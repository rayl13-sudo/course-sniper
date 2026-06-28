"""
UCI enrollment checker — uses Anteater API (successor to PeterPortal API)
and falls back to scraping WebSOC directly for real-time data.
"""

import re
import requests
from typing import Optional

ANTEATER_API = "https://anteaterapi.com/v2/rest/websoc"
WEBSOC_URL = "https://www.reg.uci.edu/perl/WebSoc"


def _parse_term(term: str) -> tuple[str, str]:
    """Parse '2026 Fall' into ('2026', 'Fall')."""
    parts = term.strip().split()
    return parts[0], parts[1]


def check_section(term: str, section_code: str) -> Optional[dict]:
    """
    Query Anteater API for a specific section code.
    Returns section info dict or None if not found / error.
    """
    year, quarter = _parse_term(term)
    params = {
        "year": year,
        "quarter": quarter,
        "sectionCodes": section_code,
    }

    try:
        resp = requests.get(ANTEATER_API, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] API request failed for section {section_code}: {e}")
        return _check_section_websoc(term, section_code)

    data = resp.json()
    if not data.get("ok"):
        print(f"[WARN] API returned error for {section_code}, trying WebSOC scrape")
        return _check_section_websoc(term, section_code)

    payload = data.get("data", {})

    for school in payload.get("schools", []):
        for dept in school.get("departments", []):
            for course in dept.get("courses", []):
                for section in course.get("sections", []):
                    if section.get("sectionCode") == section_code:
                        return {
                            "section_code": section_code,
                            "dept": course.get("deptCode", ""),
                            "course_number": course.get("courseNumber", ""),
                            "course_title": course.get("courseTitle", ""),
                            "section_type": section.get("sectionType", ""),
                            "status": section.get("status", ""),
                            "max_capacity": section.get("maxCapacity", "0"),
                            "enrolled": section.get("numCurrentlyEnrolled", {}).get("totalEnrolled", "0"),
                            "waitlist": section.get("numOnWaitlist", ""),
                            "instructors": section.get("instructors", []),
                        }

    return None


def _check_section_websoc(term: str, section_code: str) -> Optional[dict]:
    """
    Fallback: scrape UCI WebSOC directly for real-time enrollment data.
    """
    year, quarter = _parse_term(term)
    term_code = _get_term_code(year, quarter)
    if not term_code:
        return None

    form_data = {
        "YearTerm": term_code,
        "CourseCodes": section_code,
        "Submit": "Display Web Results",
        "ShowFinals": "",
        "ShowComments": "",
    }

    try:
        resp = requests.post(WEBSOC_URL, data=form_data, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] WebSOC scrape failed for {section_code}: {e}")
        return None

    return _parse_websoc_html(resp.text, section_code)


def _get_term_code(year: str, quarter: str) -> Optional[str]:
    """Convert year and quarter to UCI term code (e.g., '2025-92' for Fall 2025)."""
    quarter_map = {
        "Fall": "92",
        "Winter": "03",
        "Spring": "14",
        "Summer1": "25",
        "Summer10wk": "39",
        "Summer2": "76",
    }
    code = quarter_map.get(quarter)
    if not code:
        return None
    return f"{year}-{code}"


def _parse_websoc_html(html: str, section_code: str) -> Optional[dict]:
    """
    Parse WebSOC HTML response to extract section data.
    WebSOC returns a table with course info — we look for the row
    matching our section code.
    """
    # Extract course context (dept, number, title) from preceding rows
    dept = course_num = course_title = ""

    # Pattern for course header row: "COMPSCI   161    DES&ANALYS OF ALGOR"
    course_pattern = re.compile(
        r'<td[^>]*>([A-Z&/ ]+?)</td>\s*'
        r'<td[^>]*>(\w+)</td>\s*'
        r'<td[^>]*>(.*?)</td>',
        re.DOTALL
    )

    # Find section row by code
    # WebSOC section rows contain the 5-digit code
    code_pattern = re.compile(
        rf'>{section_code}<.*?'
        r'<td[^>]*>\s*(\w+)\s*</td>.*?'  # section type
        r'<td[^>]*>\s*(\d+)\s*</td>.*?'  # max capacity
        r'<td[^>]*>\s*(\d+)\s*</td>.*?'  # enrolled
        r'<td[^>]*>\s*(\d*)\s*</td>.*?'  # waitlist
        r'<td[^>]*>\s*(OPEN|FULL|Waitl|NewOnly)\s*</td>',
        re.DOTALL
    )

    match = code_pattern.search(html)
    if not match:
        return None

    # Try to get course context
    for m in course_pattern.finditer(html):
        dept = m.group(1).strip()
        course_num = m.group(2).strip()
        course_title = m.group(3).strip()

    return {
        "section_code": section_code,
        "dept": dept,
        "course_number": course_num,
        "course_title": course_title,
        "section_type": match.group(1),
        "status": match.group(5),
        "max_capacity": match.group(2),
        "enrolled": match.group(3),
        "waitlist": match.group(4),
        "instructors": [],
    }


def has_open_spot(section_info: dict) -> bool:
    """Check if a section has an open spot."""
    if section_info is None:
        return False

    status = section_info.get("status", "").upper()
    if status == "OPEN":
        return True

    # Also check numerically in case status is stale
    try:
        enrolled = int(section_info["enrolled"])
        capacity = int(section_info["max_capacity"])
        return enrolled < capacity
    except (ValueError, KeyError):
        return False

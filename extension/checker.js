// Course Sniper — enrollment checker (JS port of checker.py)
// Queries the Anteater API directly from the browser. host_permissions in
// manifest.json lets the service worker fetch cross-origin without CORS issues.

const ANTEATER_API = "https://anteaterapi.com/v2/rest/websoc";

// term string is like "2026 Fall" -> { year: "2026", quarter: "Fall" }
function parseTerm(term) {
  const parts = term.trim().split(/\s+/);
  return { year: parts[0], quarter: parts[1] };
}

// Query the Anteater API for one 5-digit section code.
// Returns a section-info object, or null if not found / on error.
export async function checkSection(term, sectionCode) {
  const { year, quarter } = parseTerm(term);
  const url =
    `${ANTEATER_API}?year=${encodeURIComponent(year)}` +
    `&quarter=${encodeURIComponent(quarter)}` +
    `&sectionCodes=${encodeURIComponent(sectionCode)}`;

  let data;
  try {
    const resp = await fetch(url, { method: "GET" });
    if (!resp.ok) {
      console.warn(`[checker] HTTP ${resp.status} for ${sectionCode}`);
      return null;
    }
    data = await resp.json();
  } catch (e) {
    console.error(`[checker] request failed for ${sectionCode}:`, e);
    return null;
  }

  if (!data || !data.ok) {
    console.warn(`[checker] API returned error for ${sectionCode}`);
    return null;
  }

  const payload = data.data || {};
  for (const school of payload.schools || []) {
    for (const dept of school.departments || []) {
      for (const course of dept.courses || []) {
        for (const section of course.sections || []) {
          if (section.sectionCode === sectionCode) {
            return {
              section_code: sectionCode,
              dept: course.deptCode || "",
              course_number: course.courseNumber || "",
              course_title: course.courseTitle || "",
              section_type: section.sectionType || "",
              status: section.status || "",
              max_capacity: section.maxCapacity || "0",
              enrolled:
                (section.numCurrentlyEnrolled &&
                  section.numCurrentlyEnrolled.totalEnrolled) ||
                "0",
              waitlist: section.numOnWaitlist || "",
              instructors: section.instructors || [],
            };
          }
        }
      }
    }
  }

  return null;
}

// True if the section has an open seat.
export function hasOpenSpot(info) {
  if (!info) return false;

  if ((info.status || "").toUpperCase() === "OPEN") return true;

  // Numeric fallback in case status is stale.
  const enrolled = parseInt(info.enrolled, 10);
  const capacity = parseInt(info.max_capacity, 10);
  if (Number.isFinite(enrolled) && Number.isFinite(capacity)) {
    return enrolled < capacity;
  }
  return false;
}

import client from "./client";

export async function getAttendance(courseId, date) {
  const query = date ? `?date=${encodeURIComponent(date)}` : "";
  const { data } = await client.get(`/faculty/courses/${courseId}/attendance${query}`);
  return data;
}

export async function getHealthSummary(courseId) {
  const { data } = await client.get(`/faculty/courses/${courseId}/health-summary`);
  return data;
}

export async function createAbsenceFlag(flagData) {
  const { data } = await client.post("/faculty/absence-flags", flagData);
  return data;
}

export async function getAbsenceFlags() {
  const { data } = await client.get("/faculty/absence-flags");
  return data;
}

export async function getDivisionPattern(divisionId) {
  const query = divisionId ? `?division_id=${encodeURIComponent(divisionId)}` : "";
  const { data } = await client.get(`/class-teacher/division-pattern${query}`);
  return data;
}

export async function getEscalations() {
  const { data } = await client.get("/class-teacher/escalations");
  return data;
}

export async function approveEnrollmentChange(enrollmentIdOrData, payload = {}) {
  if (typeof enrollmentIdOrData === "object" && enrollmentIdOrData !== null) {
    const { data } = await client.post("/class-teacher/enrollment-changes/approve", enrollmentIdOrData);
    return data;
  }
  const endpoint = enrollmentIdOrData ? `/class-teacher/enrollment-changes/${enrollmentIdOrData}/approve` : "/class-teacher/enrollment-changes/approve";
  const { data } = await client.post(endpoint, payload);
  return data;
}

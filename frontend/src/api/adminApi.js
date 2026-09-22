import client from "./client";

// Health Admin endpoints
export async function getCases(params = {}) {
  const { data } = await client.get("/health-admin/cases", { params });
  return data;
}

export async function confirmCase(caseId, diseaseId = null) {
  const payload = diseaseId ? { disease_id: diseaseId } : {};
  const { data } = await client.post(`/health-admin/cases/${caseId}/confirm`, payload);
  return data;
}

export async function getContactGraph(caseId, params = {}) {
  const { data } = await client.get(`/health-admin/contact-graph/${caseId}`, { params });
  return data;
}

export async function retraceContactGraph(caseId, params = {}) {
  const { data } = await client.post(`/health-admin/contact-graph/${caseId}/retrace`, params);
  return data;
}

export async function getDiseaseKB() {
  const { data } = await client.get("/health-admin/disease-kb");
  return data;
}

export async function createDiseaseKB(kbData) {
  const { data } = await client.post("/health-admin/disease-kb", kbData);
  return data;
}

export async function updateDiseaseKB(id, kbData) {
  const { data } = await client.patch(`/health-admin/disease-kb/${id}`, kbData);
  return data;
}

export async function getCapacity() {
  const { data } = await client.get("/health-admin/capacity");
  return data;
}

export async function allocateBed(capacityId, userId = null) {
  const payload = userId ? { user_id: userId } : {};
  const { data } = await client.post(`/health-admin/capacity/${capacityId}/allocate`, payload);
  return data;
}

export async function reviewFeedback(alertId, adjustWeight = false) {
  const { data } = await client.post(`/health-admin/feedback/${alertId}/review`, {
    adjust_weight: adjustWeight,
  });
  return data;
}

export async function getCaseAnalytics(caseId) {
  const { data } = await client.get(`/health-admin/analytics/case/${caseId}`);
  return data;
}

export async function getAnalyticsSummary() {
  const { data } = await client.get("/health-admin/analytics/summary");
  return data;
}

export async function getPriorityQueue() {
  const { data } = await client.get("/health-admin/priority-queue");
  return data;
}

// Institute Admin endpoints
export async function getAggregateDashboards() {
  const { data } = await client.get("/institute-admin/dashboards/aggregate");
  return data;
}

export async function createDivision(divisionData) {
  const { data } = await client.post("/institute-admin/divisions", divisionData);
  return data;
}

export async function createRoom(roomData) {
  const { data } = await client.post("/institute-admin/rooms", roomData);
  return data;
}

export async function createCourse(courseData) {
  const { data } = await client.post("/institute-admin/courses", courseData);
  return data;
}

export async function createBatch(batchData) {
  const { data } = await client.post("/institute-admin/batches", batchData);
  return data;
}

export async function assignFaculty(assignmentData) {
  const { data } = await client.post("/institute-admin/faculty-assignments", assignmentData);
  return data;
}

export async function createTimetableSlot(slotData) {
  const { data } = await client.post("/institute-admin/timetable-slots", slotData);
  return data;
}

export async function getSystemConfig() {
  const { data } = await client.get("/institute-admin/system-config");
  return data;
}

export async function updateSystemConfig(configData) {
  const { data } = await client.patch("/institute-admin/system-config", configData);
  return data;
}

export async function getAuditLog(params = {}) {
  const { data } = await client.get("/institute-admin/audit-log", { params });
  return data;
}

export async function listUsers(params = {}) {
  const { data } = await client.get("/institute-admin/users", { params });
  return data;
}

export async function updateUserStatus(userId, isActive) {
  const { data } = await client.patch(`/institute-admin/users/${userId}`, {
    is_active: isActive,
  });
  return data;
}

export async function registerRoleUser(userData) {
  const { data } = await client.post("/auth/register", userData);
  return data;
}

export async function getOutbreakTrends() {
  const { data } = await client.get("/institute-admin/dashboards/trends");
  return data;
}

export async function getDepartmentStats() {
  const { data } = await client.get("/institute-admin/dashboards/by-department");
  return data;
}

export async function getHighOverlapLocations() {
  const { data } = await client.get("/institute-admin/dashboards/high-overlap-locations");
  return data;
}

export async function getAnalytics() {
  const { data } = await client.get("/institute-admin/dashboards/analytics");
  return data;
}

export async function getEventExposures() {
  const { data } = await client.get("/institute-admin/dashboards/event-exposures");
  return data;
}

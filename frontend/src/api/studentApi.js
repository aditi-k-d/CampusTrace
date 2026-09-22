import client from "./client";

export async function registerBatches(batchSelections) {
  const { data } = await client.post("/student/register-batches", {
    batch_selections: batchSelections,
  });
  return data;
}

export async function getCourses() {
  const { data } = await client.get("/student/courses");
  return data;
}

export async function reportHealth(healthData) {
  const { data } = await client.post("/student/health-report", healthData);
  return data;
}

export async function getAlerts() {
  const { data } = await client.get("/student/alerts");
  return data;
}

export async function getHealthRecords() {
  const { data } = await client.get("/student/health-records");
  return data;
}

export async function getDiseases() {
  const { data } = await client.get("/student/diseases");
  return data;
}

export async function acknowledgeAlert(alertId) {
  const { data } = await client.post(`/student/alerts/${alertId}/acknowledge`);
  return data;
}

export async function reportFalsePositive(alertId) {
  const { data } = await client.post(`/student/alerts/${alertId}/false-positive`);
  return data;
}

export async function getAbsenceFlags() {
  const { data } = await client.get("/student/absence-flags");
  return data;
}

export async function respondAbsenceFlag(flagId, confirm) {
  const { data } = await client.post(`/student/absence-flags/${flagId}/respond`, {
    confirm,
  });
  return data;
}

export async function selfAssessment(symptoms) {
  const { data } = await client.post("/student/self-assessment", { symptoms });
  return data;
}

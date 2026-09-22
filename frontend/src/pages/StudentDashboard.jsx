import React, { useState, useEffect } from "react";
import { getCourses, getAlerts, getHealthRecords } from "../api/studentApi";
import { getUser, clearSession } from "../auth/authStorage";
import { useNavigate } from "react-router-dom";
import SelfReportForm from "../components/student/SelfReportForm";
import AlertCard from "../components/student/AlertCard";
import SelfAssessment from "../components/student/SelfAssessment";
import AbsenceFlagResponse from "../components/student/AbsenceFlagResponse";
import DashboardShell from "../components/layout/DashboardShell";
import ModuleCard from "../components/layout/ModuleCard";
import "./student.css";

export default function StudentDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [healthRecords, setHealthRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadDashboardData() {
    setLoading(true);
    setError(null);
    try {
      const [coursesData, alertsData, healthData] = await Promise.all([
        getCourses(),
        getAlerts(),
        getHealthRecords().catch(() => []),
      ]);

      const needsBatchSelection = (coursesData || []).some(
        (c) => (c.course_type === "lab" || c.course_type === "tutorial") && !c.batch_id
      );
      if (needsBatchSelection) {
        navigate("/batch-selection", { replace: true });
        return;
      }

      setCourses(coursesData || []);
      setAlerts(alertsData || []);
      setHealthRecords(healthData || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <DashboardShell
      title="Student Portal"
      subtitle="Undergraduate & Graduate Academic and Health Intranet"
      error={error}
      onLogout={handleLogout}
    >
      <div className="student-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        {/* Card-based Module Entry Points */}
        <div className="module-entry-grid">
          <ModuleCard
            title="Enrolled Courses"
            description="View registered courses, lab batches, and tutorial sections"
            badge={`${courses.length} Courses`}
            badgeType="primary"
            actionText="Go to Courses →"
            href="#courses-module"
          />
          <ModuleCard
            title="Health Self-Report"
            description="Confidential self-reporting for symptom onset and clinical assessment"
            badge="Health Action"
            badgeType="warning"
            actionText="Submit Health Report →"
            href="#self-report-module"
          />
          <ModuleCard
            title="Exposure Alerts"
            description="Confidential exposure notifications and recommended preventive actions"
            badge={alerts.length > 0 ? `${alerts.length} Active` : "Clear"}
            badgeType={alerts.length > 0 ? "warning" : "success"}
            actionText="View Exposure Alerts →"
            href="#exposure-alerts-module"
          />
          <ModuleCard
            title="Symptom Triage"
            description="Evaluate symptoms against the campus Disease Knowledge Base"
            badge="Assessment"
            badgeType="primary"
            actionText="Run Triage →"
            href="#self-assessment-module"
          />
        </div>

        <div className="dashboard-grid">
          <section className="column">
            <ModuleCard
              id="courses-module"
              title="My Enrolled Courses"
              description="Current academic term registrations and assigned practical batches"
            >
              {loading ? (
                <p>Loading courses...</p>
              ) : courses.length === 0 ? (
                <p className="text-muted">No course enrollments found.</p>
              ) : (
                <ul className="course-list">
                  {courses.map((c) => (
                    <li key={c.course_id} className="course-item">
                      <div>
                        <strong>{c.code} - {c.name}</strong>
                        <span className="course-type"> ({c.course_type})</span>
                      </div>
                      {c.batch_name && (
                        <span className="batch-pill">Batch: {c.batch_name}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </ModuleCard>

            <div id="self-report-module">
              <SelfReportForm onReportSubmitted={loadDashboardData} />
            </div>

            <ModuleCard
              id="health-history-module"
              title="My Health Status & History"
              description="Historical log of reported health events and institutional confirmation"
            >
              {loading ? (
                <p>Loading health history...</p>
              ) : healthRecords.length === 0 ? (
                <p className="text-muted">No health reports filed.</p>
              ) : (
                <ul className="health-records-list">
                  {healthRecords.map((r) => (
                    <li key={r.id} className="health-record-item">
                      <div>
                        <strong>Onset Date:</strong> {r.onset_date} | <strong>Severity:</strong> {r.severity}
                      </div>
                      <div>
                        <strong>Symptoms/Disease:</strong> {r.disease_name || r.custom_symptoms}
                      </div>
                      <div>
                        <span className={`status-badge status-${r.status}`}>{r.status}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </ModuleCard>

            <div id="absence-responses-module">
              <AbsenceFlagResponse />
            </div>
          </section>

          <section className="column">
            <ModuleCard
              id="exposure-alerts-module"
              title={`Exposure Alerts (${alerts.length})`}
              description="Private exposure notices; does not disclose identity of contact sources"
            >
              {loading ? (
                <p>Loading alerts...</p>
              ) : alerts.length === 0 ? (
                <p className="text-muted">No active exposure alerts. Stay safe!</p>
              ) : (
                <div className="alerts-container">
                  {alerts.map((a) => (
                    <AlertCard key={a.id} alert={a} onAlertUpdated={loadDashboardData} />
                  ))}
                </div>
              )}
            </ModuleCard>

            <div id="self-assessment-module">
              <SelfAssessment />
            </div>
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}

import React, { useState, useEffect } from "react";
import { getAbsenceFlags } from "../api/facultyApi";
import { getUser, clearSession } from "../auth/authStorage";
import { useNavigate } from "react-router-dom";
import AttendanceView from "../components/faculty/AttendanceView";
import AbsenceFlagForm from "../components/faculty/AbsenceFlagForm";
import DashboardShell from "../components/layout/DashboardShell";
import ModuleCard from "../components/layout/ModuleCard";
import "./faculty.css";

export default function FacultyDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadFlags() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAbsenceFlags();
      setFlags(data || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load absence flags.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFlags();
  }, []);

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <DashboardShell
      title="Course Faculty Portal"
      subtitle="Course Session Attendance Management & Health Surveillance"
      error={error}
      onLogout={handleLogout}
    >
      <div className="faculty-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        {/* Card-based Module Entry Points */}
        <div className="module-entry-grid">
          <ModuleCard
            title="Attendance & Health Summary"
            description="Track course session attendance and aggregate health statistics"
            badge="Attendance"
            badgeType="primary"
            actionText="View Attendance →"
            href="#attendance-module"
          />
          <ModuleCard
            title="Flag Student Absence"
            description="Observe and flag student absences for health surveillance follow-up"
            badge="Action"
            badgeType="warning"
            actionText="Flag Absence →"
            href="#absence-flag-module"
          />
          <ModuleCard
            title="Absence Flags Raised"
            description="Review raised flags, categorized reasons, and escalation status"
            badge={`${flags.length} Flags`}
            badgeType={flags.length > 0 ? "warning" : "success"}
            actionText="Review Flags →"
            href="#raised-flags-module"
          />
        </div>

        <div className="dashboard-grid">
          <section className="column">
            <div id="attendance-module">
              <AttendanceView />
            </div>
          </section>

          <section className="column">
            <div id="absence-flag-module">
              <AbsenceFlagForm onFlagCreated={loadFlags} />
            </div>

            <ModuleCard
              id="raised-flags-module"
              title={`Absence Flags Raised (${flags.length})`}
              description="Log of student absence flags submitted for your assigned courses"
            >
              {loading ? (
                <p>Loading flags...</p>
              ) : flags.length === 0 ? (
                <p className="text-muted">No absence flags raised yet.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Course</th>
                      <th>Flagged Date</th>
                      <th>Reason</th>
                      <th>State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flags.map((f) => (
                      <tr key={f.id}>
                        <td>{f.student_name || `#${f.student_id}`}</td>
                        <td>{f.course_code || `#${f.course_id}`}</td>
                        <td>{f.flagged_date}</td>
                        <td>{f.reason_category}</td>
                        <td>
                          <span className={`status-badge status-${f.state}`}>{f.state}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </ModuleCard>
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}

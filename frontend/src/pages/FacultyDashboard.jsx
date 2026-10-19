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
  const [activeModule, setActiveModule] = useState("attendance");

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

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [activeModule]);

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <DashboardShell
      title="Course Faculty Portal"
      subtitle="Course Session Attendance Management & Health Surveillance"
      activeNav={activeModule}
      onNavClick={setActiveModule}
      error={error}
      onLogout={handleLogout}
    >
      <div className="faculty-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        <div className="dashboard-grid single-module-view">
          <section className="column">
            <div id="attendance-module" hidden={activeModule !== "attendance"}>
              <AttendanceView />
            </div>
          </section>

          <section className="column">
            <div id="absence-flag-module" hidden={activeModule !== "flag-absence"}>
              <AbsenceFlagForm onFlagCreated={loadFlags} />
            </div>

            <ModuleCard
              id="raised-flags-module"
              hidden={activeModule !== "raised-flags"}
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

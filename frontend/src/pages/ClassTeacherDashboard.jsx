import React, { useState, useEffect } from "react";
import {
  getDivisionPattern,
  getEscalations,
  approveEnrollmentChange,
} from "../api/facultyApi";
import { getUser, clearSession } from "../auth/authStorage";
import { useNavigate } from "react-router-dom";
import DashboardShell from "../components/layout/DashboardShell";
import ModuleCard from "../components/layout/ModuleCard";
import "./faculty.css";

export default function ClassTeacherDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [divisionData, setDivisionData] = useState(null);
  const [escalations, setEscalations] = useState([]);
  const [rollingWindowDays, setRollingWindowDays] = useState(14);
  const [enrollmentInputId, setEnrollmentInputId] = useState("");
  const [approveMessage, setApproveMessage] = useState(null);
  const [approveError, setApproveError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadDashboardData() {
    setLoading(true);
    setError(null);
    try {
      const [divData, escData] = await Promise.all([
        getDivisionPattern(),
        getEscalations(),
      ]);
      setDivisionData(divData);
      setEscalations(escData.escalations || []);
      setRollingWindowDays(escData.rolling_window_days || 14);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load Class Teacher dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function handleApprove(e) {
    e.preventDefault();
    setApproveMessage(null);
    setApproveError(null);

    if (!enrollmentInputId) {
      setApproveError("Please enter an Enrollment ID.");
      return;
    }

    try {
      const res = await approveEnrollmentChange(enrollmentInputId);
      setApproveMessage(`Enrollment #${res.enrollment_id} approved successfully.`);
      setEnrollmentInputId("");
    } catch (err) {
      setApproveError(err.response?.data?.error || "Failed to approve enrollment change.");
    }
  }

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <DashboardShell
      title="Class Teacher Portal"
      subtitle="Division-Wide Attendance Monitoring & Enrollment Adjustments"
      error={error}
      onLogout={handleLogout}
    >
      <div className="faculty-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        {/* Card-based Module Entry Points */}
        <div className="module-entry-grid">
          <ModuleCard
            title="Division Overview"
            description="Course attendance and presence pattern summary across your division"
            badge={divisionData ? `${divisionData.total_students} Students` : "Division"}
            badgeType="primary"
            actionText="View Overview →"
            href="#division-module"
          />
          <ModuleCard
            title="Absence Escalations"
            description={`Multi-course absence detection over a rolling ${rollingWindowDays}-day surveillance window`}
            badge={`${escalations.length} Detected`}
            badgeType={escalations.length > 0 ? "warning" : "success"}
            actionText="Review Escalations →"
            href="#escalations-module"
          />
          <ModuleCard
            title="Enrollment Approvals"
            description="Approve cross-division elective enrollments and laboratory batch transfers"
            badge="Administration"
            badgeType="primary"
            actionText="Approve Transfers →"
            href="#approvals-module"
          />
        </div>

        <div className="dashboard-grid">
          <section className="column">
            <ModuleCard
              id="division-module"
              title="Division Overview"
              description="Division-wide attendance and course flag summary"
            >
              {loading ? (
                <p>Loading division pattern...</p>
              ) : divisionData ? (
                <div>
                  <p><strong>Division:</strong> {divisionData.division_name} ({divisionData.branch} Year {divisionData.year})</p>
                  <p><strong>Total Students:</strong> {divisionData.total_students}</p>
                  <p><strong>Active Health Cases:</strong> <span className="text-warning">{divisionData.active_health_cases}</span></p>

                  <h3>Course Attendance & Flag Summary</h3>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Course Code</th>
                        <th>Course Name</th>
                        <th>Absence Flags</th>
                        <th>Presence Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {divisionData.courses?.map((c) => (
                        <tr key={c.course_id}>
                          <td>{c.code}</td>
                          <td>{c.name}</td>
                          <td>{c.absence_flags_count}</td>
                          <td>{c.presence_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted">No division pattern data available.</p>
              )}
            </ModuleCard>
          </section>

          <section className="column">
            <ModuleCard
              id="escalations-module"
              title={`Absence Escalations (${escalations.length})`}
              subtitle={`Students showing cross-course absence patterns in the last ${rollingWindowDays} days.`}
            >
              {loading ? (
                <p>Loading escalations...</p>
              ) : escalations.length === 0 ? (
                <p className="text-muted">No cross-course absence escalations detected in the last {rollingWindowDays} days.</p>
              ) : (
                <div className="escalations-list">
                  {escalations.map((esc) => (
                    <div key={esc.student_id} className="escalation-item card">
                      <p><strong>Student:</strong> {esc.student_name} ({esc.student_email})</p>
                      <p><strong>Total Flags:</strong> {esc.flag_count}</p>
                      <p><strong>Distinct Courses:</strong> {esc.distinct_courses_count}</p>
                      <p><strong>Reasons:</strong> {esc.reason_categories?.join(", ")}</p>
                    </div>
                  ))}
                </div>
              )}
            </ModuleCard>

            <ModuleCard
              id="approvals-module"
              title="Approve Enrollment Change"
              description="Authorize elective changes and student transfers"
            >
              <form onSubmit={handleApprove}>
                <div className="form-group">
                  <label htmlFor="enrollment-id">Enrollment ID</label>
                  <input
                    id="enrollment-id"
                    type="number"
                    placeholder="Enter Enrollment ID"
                    value={enrollmentInputId}
                    onChange={(e) => setEnrollmentInputId(e.target.value)}
                  />
                </div>

                {approveError && <p className="error-text" role="alert">{approveError}</p>}
                {approveMessage && <p className="success-text">{approveMessage}</p>}

                <button type="submit">Approve Change</button>
              </form>
            </ModuleCard>
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}

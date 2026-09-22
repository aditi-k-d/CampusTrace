import React, { useState, useEffect } from "react";
import { getAttendance, getHealthSummary } from "../../api/facultyApi";

export default function AttendanceView({ courseId }) {
  const [selectedCourseId, setSelectedCourseId] = useState(courseId || "");
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [attendanceData, setAttendanceData] = useState(null);
  const [healthSummary, setHealthSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function loadData() {
    if (!selectedCourseId) return;
    setLoading(true);
    setError(null);
    try {
      const [att, hs] = await Promise.all([
        getAttendance(selectedCourseId, selectedDate),
        getHealthSummary(selectedCourseId),
      ]);
      setAttendanceData(att);
      setHealthSummary(hs);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load course attendance data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedCourseId) {
      loadData();
    }
  }, [selectedCourseId, selectedDate]);

  return (
    <div className="card">
      <h2>Course Attendance & Health Summary</h2>

      <div className="filter-bar">
        <div className="form-group inline">
          <label htmlFor="select-course">Course ID</label>
          <input
            id="select-course"
            type="number"
            placeholder="Course ID"
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
          />
        </div>

        <div className="form-group inline">
          <label htmlFor="select-date">Date</label>
          <input
            id="select-date"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        </div>
      </div>

      {error && <p className="error-text" role="alert">{error}</p>}

      {loading ? (
        <p>Loading attendance data...</p>
      ) : (
        <>
          {healthSummary && (
            <div className="health-summary-box">
              <h3>Aggregate Health Status</h3>
              <div className="stats-row">
                <div className="stat-card">
                  <span className="stat-num">{healthSummary.total_students}</span>
                  <span className="stat-label">Total Enrolled</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num text-warning">{healthSummary.under_observation}</span>
                  <span className="stat-label">Under Observation</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num text-danger">{healthSummary.confirmed_cases}</span>
                  <span className="stat-label">Confirmed Cases</span>
                </div>
              </div>
              <small className="text-muted">
                * Note: Displays aggregate counts only, never individual health diagnoses.
              </small>
            </div>
          )}

          {attendanceData && (
            <div className="attendance-list-box">
              <h3>
                Session Presence ({attendanceData.total_present} Present) - {attendanceData.date}
              </h3>
              {attendanceData.present_users?.length === 0 ? (
                <p className="text-muted">No student presence records for this date/session.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>User ID</th>
                      <th>Student Name</th>
                      <th>Room</th>
                      <th>Time Slot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendanceData.present_users?.map((p, idx) => (
                      <tr key={idx}>
                        <td>{p.user_id}</td>
                        <td>{p.user_name || "Student"}</td>
                        <td>{p.room_name || "N/A"}</td>
                        <td>{p.start_time} - {p.end_time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

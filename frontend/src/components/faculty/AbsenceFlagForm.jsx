import React, { useState } from "react";
import { createAbsenceFlag } from "../../api/facultyApi";

export default function AbsenceFlagForm({ defaultCourseId, onFlagCreated }) {
  const [studentId, setStudentId] = useState("");
  const [courseId, setCourseId] = useState(defaultCourseId || "");
  const [flaggedDate, setFlaggedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [reasonCategory, setReasonCategory] = useState("health_observed");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!studentId || !courseId) {
      setError("Student ID and Course ID are required.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createAbsenceFlag({
        student_id: Number(studentId),
        course_id: Number(courseId),
        flagged_date: flaggedDate,
        reason_category: reasonCategory,
      });
      setMessage(`Absence flag created successfully for Student #${studentId}.`);
      setStudentId("");
      if (onFlagCreated) {
        onFlagCreated(result);
      }
    } catch (err) {
      setError(
        err.response?.data?.error || "Failed to create absence flag."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Flag Student Absence</h2>
      <p className="subtitle">
        Flag a student absent for health reasons in your assigned course.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="student-id">Student ID</label>
          <input
            id="student-id"
            type="number"
            placeholder="Enter Student User ID"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="course-id">Course ID</label>
          <input
            id="course-id"
            type="number"
            placeholder="Enter Course ID"
            value={courseId}
            onChange={(e) => setCourseId(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="flagged-date">Flagged Date</label>
          <input
            id="flagged-date"
            type="date"
            value={flaggedDate}
            onChange={(e) => setFlaggedDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="reason-category">Reason Category</label>
          <select
            id="reason-category"
            value={reasonCategory}
            onChange={(e) => setReasonCategory(e.target.value)}
            required
          >
            <option value="health_observed">Health Observed / Reported</option>
            <option value="unexcused_absence">Unexcused Medical Absence</option>
            <option value="symptom_observation">Symptom Observation</option>
          </select>
        </div>

        {error && <p className="error-text" role="alert">{error}</p>}
        {message && <p className="success-text">{message}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Submitting..." : "Flag Student"}
        </button>
      </form>
    </div>
  );
}

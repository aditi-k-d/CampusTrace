import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getCourses, registerBatches } from "../api/studentApi";
import { getUser } from "../auth/authStorage";
import "./student.css";

export default function BatchSelection() {
  const user = getUser();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [selections, setSelections] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadCourses() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCourses();
        const labAndTutorialCourses = (data || []).filter(
          (c) => c.course_type === "lab" || c.course_type === "tutorial"
        );
        setCourses(labAndTutorialCourses);

        // Initialize selections with existing batch_id or default to first batch
        const initialSelections = {};
        labAndTutorialCourses.forEach((c) => {
          if (c.batch_id) {
            initialSelections[c.course_id] = c.batch_id;
          } else if (c.batches && c.batches.length > 0) {
            initialSelections[c.course_id] = c.batches[0].id;
          }
        });
        setSelections(initialSelections);
      } catch (err) {
        setError(err.response?.data?.error || "Failed to load courses for batch selection.");
      } finally {
        setLoading(false);
      }
    }

    loadCourses();
  }, []);

  function handleBatchChange(courseId, batchId) {
    setSelections((prev) => ({
      ...prev,
      [courseId]: Number(batchId),
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    const batchSelections = Object.entries(selections).map(([courseId, batchId]) => ({
      course_id: Number(courseId),
      batch_id: Number(batchId),
    }));

    if (courses.length > 0 && batchSelections.length < courses.length) {
      setError("Please select a batch for every required lab and tutorial course.");
      return;
    }

    setSubmitting(true);
    try {
      if (batchSelections.length > 0) {
        await registerBatches(batchSelections);
      }
      navigate("/student");
    } catch (err) {
      setError(err.response?.data?.error || "Failed to register batch selections.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="batch-selection-page student-dashboard-page">
      <header className="dashboard-header">
        <div>
          <h1>Practical & Tutorial Batch Selection</h1>
          <p className="welcome-text">
            Welcome, {user?.name || "Student"}. Please select your practical/tutorial batches to complete registration.
          </p>
        </div>
      </header>

      <main className="batch-selection-container" style={{ maxWidth: "700px", margin: "2rem auto" }}>
        <div className="card">
          <h2>Select Your Batches</h2>
          <p className="subtitle">
            Theory courses are assigned institution-wide and need no batch selection. Only laboratory and tutorial courses require batch assignment.
          </p>

          {error && <p className="error-text" role="alert">{error}</p>}

          {loading ? (
            <p>Loading course requirements...</p>
          ) : courses.length === 0 ? (
            <div>
              <p className="text-muted">No lab or tutorial courses requiring batch selection found.</p>
              <button className="btn-primary" onClick={() => navigate("/student")} style={{ marginTop: "1rem" }}>
                Proceed to Dashboard
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="course-batches-list" style={{ display: "flex", flexDirection: "column", gap: "1.25rem", margin: "1.5rem 0" }}>
                {courses.map((course) => (
                  <div key={course.course_id} className="course-batch-item" style={{ border: "1px solid #e2e8f0", padding: "1rem", borderRadius: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                      <strong>{course.code} — {course.name}</strong>
                      <span className="badge" style={{ textTransform: "capitalize", background: "#edf2f7", padding: "0.2rem 0.6rem", borderRadius: "4px" }}>
                        {course.course_type}
                      </span>
                    </div>

                    <label htmlFor={`select-batch-${course.course_id}`} style={{ display: "block", marginBottom: "0.4rem", fontSize: "0.9rem", color: "#4a5568" }}>
                      Select Assigned Batch:
                    </label>

                    {course.batches && course.batches.length > 0 ? (
                      <select
                        id={`select-batch-${course.course_id}`}
                        value={selections[course.course_id] || ""}
                        onChange={(e) => handleBatchChange(course.course_id, e.target.value)}
                        required
                        style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e0" }}
                      >
                        {course.batches.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-muted" style={{ fontSize: "0.85rem", fontStyle: "italic" }}>
                        No batches configured yet for this course.
                      </p>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "1rem" }}>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting || courses.length === 0}
                >
                  {submitting ? "Saving..." : "Confirm Batches & Continue to Dashboard"}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}

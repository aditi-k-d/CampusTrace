import React, { useState, useEffect } from "react";
import { getAbsenceFlags, respondAbsenceFlag } from "../../api/studentApi";

export default function AbsenceFlagResponse() {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);

  async function loadFlags() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAbsenceFlags();
      setFlags(data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load absence flags.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFlags();
  }, []);

  async function handleRespond(flagId, confirm) {
    setActionLoading(flagId);
    setError(null);
    try {
      await respondAbsenceFlag(flagId, confirm);
      setFlags((prev) =>
        prev.map((f) =>
          f.id === flagId ? { ...f, state: confirm ? "confirmed" : "dismissed" } : f
        )
      );
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update absence flag status.");
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="card">
      <h2>Absence Flags</h2>
      {error && <p className="error-text" role="alert">{error}</p>}
      {loading ? (
        <p>Loading absence flags...</p>
      ) : flags.length === 0 ? (
        <p className="text-muted">No absence flags raised against you.</p>
      ) : (
        <div className="flags-list">
          {flags.map((flag) => (
            <div key={flag.id} className="flag-item">
              <div className="flag-info">
                <p><strong>Course:</strong> {flag.course_name || `Course #${flag.course_id}`}</p>
                <p><strong>Flagged Date:</strong> {flag.flagged_date}</p>
                <p><strong>Reason:</strong> {flag.reason_category}</p>
                <p>
                  <strong>Status:</strong>{" "}
                  <span className={`status-badge status-${flag.state}`}>{flag.state}</span>
                </p>
              </div>

              {flag.state === "pending" && (
                <div className="flag-actions">
                  <button
                    className="btn-confirm"
                    disabled={actionLoading === flag.id}
                    onClick={() => handleRespond(flag.id, true)}
                  >
                    Confirm Absence
                  </button>
                  <button
                    className="btn-deny"
                    disabled={actionLoading === flag.id}
                    onClick={() => handleRespond(flag.id, false)}
                  >
                    Deny
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import React, { useState, useEffect } from "react";
import { getCaseAnalytics } from "../../api/adminApi";

export default function RiskBreakdownView({ caseId }) {
  const [breakdown, setBreakdown] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!caseId) {
      setBreakdown(null);
      return;
    }

    async function loadAnalytics() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCaseAnalytics(caseId);
        setBreakdown(data);
      } catch (err) {
        setError(
          err.response?.data?.error || `Failed to load risk analytics for Case #${caseId}.`
        );
      } finally {
        setLoading(false);
      }
    }

    loadAnalytics();
  }, [caseId]);

  function getRiskBadgeStyle(level) {
    const l = (level || "").toLowerCase();
    if (l === "high") {
      return {
        backgroundColor: "#fee2e2",
        color: "#991b1b",
        border: "1px solid #f87171",
      };
    }
    if (l === "medium") {
      return {
        backgroundColor: "#ffedd5",
        color: "#9a3412",
        border: "1px solid #fb923c",
      };
    }
    return {
      backgroundColor: "#dcfce7",
      color: "#166534",
      border: "1px solid #86efac",
    };
  }

  const contacts = breakdown?.contacts || (Array.isArray(breakdown) ? breakdown : []);

  return (
    <div className="card risk-breakdown-card" data-testid="risk-breakdown-view">
      <h2>Contact Risk Calculation Breakdown</h2>
      <p className="subtitle">
        Surfacing transparent spatial, temporal, and hop-decay scoring dimensions per contact.
      </p>

      {!caseId && (
        <p className="text-muted" style={{ fontStyle: "italic" }}>
          Select a health case to view its detailed contact risk calculation breakdown.
        </p>
      )}

      {error && <p className="error-text" role="alert">{error}</p>}

      {loading && <p>Loading contact risk calculations for Case #{caseId}...</p>}

      {!loading && caseId && (
        <>
          <div
            style={{
              marginBottom: "1rem",
              padding: "0.5rem 0.75rem",
              background: "#f1f5f9",
              borderRadius: "6px",
              display: "flex",
              gap: "1.5rem",
              fontSize: "0.85rem",
              color: "#334155",
            }}
          >
            <span>
              <strong>Case ID:</strong> #{caseId}
            </span>
            {breakdown?.onset_date && (
              <span>
                <strong>Onset Date:</strong> {breakdown.onset_date}
              </span>
            )}
            <span>
              <strong>Total Traced Contacts:</strong> {contacts.length}
            </span>
          </div>

          {contacts.length === 0 ? (
            <p className="text-muted">No traced contacts recorded for Case #{caseId}.</p>
          ) : (
            <table className="data-table risk-breakdown-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Contact Type</th>
                  <th>Duration Overlap</th>
                  <th>Location / Room</th>
                  <th>Days Since Contact</th>
                  <th>Hop Decay Factor</th>
                  <th>Base Score</th>
                  <th>Final Risk Category</th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c, idx) => {
                  const depth = c.depth != null ? Number(c.depth) : 1;
                  const isDirect =
                    depth === 1 ||
                    (c.contact_type && c.contact_type.toLowerCase() === "direct");
                  const contactType = isDirect ? "Direct" : "Indirect";
                  const riskLevel = (c.risk_level || c.risk_category || "low").toLowerCase();
                  const userName =
                    c.user_name ||
                    c.name ||
                    (c.user_id ? `User #${c.user_id}` : `Contact #${idx + 1}`);
                  const duration =
                    c.duration_minutes != null ? `${c.duration_minutes} mins` : "N/A";
                  const room =
                    c.room_name ||
                    (c.room_id
                      ? `Room #${c.room_id}`
                      : c.room_type_weight != null
                      ? `Weight: ${c.room_type_weight}`
                      : "Shared Space");
                  const daysSince =
                    c.days_since_contact != null ? `${c.days_since_contact} days` : "0 days";
                  const hopDecay = c.hop_decay != null ? c.hop_decay : depth === 1 ? 1.0 : 0.5;
                  const baseScore =
                    c.base_score != null
                      ? Number(c.base_score).toFixed(1)
                      : c.risk_score != null
                      ? Number(c.risk_score).toFixed(1)
                      : "0.0";

                  return (
                    <tr key={c.user_id || idx} data-testid={`risk-row-${idx}`}>
                      <td>
                        <strong>{userName}</strong>
                      </td>
                      <td>
                        <span
                          className={`badge-contact-type ${
                            isDirect ? "type-direct" : "type-indirect"
                          }`}
                          style={{
                            padding: "0.2rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            fontWeight: "600",
                            backgroundColor: isDirect ? "#e0f2fe" : "#f1f5f9",
                            color: isDirect ? "#0369a1" : "#475569",
                          }}
                        >
                          {contactType}
                        </span>
                      </td>
                      <td>{duration}</td>
                      <td>{room}</td>
                      <td>{daysSince}</td>
                      <td>{hopDecay}</td>
                      <td>{baseScore}</td>
                      <td>
                        <span
                          className={`status-badge risk-badge risk-${riskLevel}`}
                          style={{
                            ...getRiskBadgeStyle(riskLevel),
                            padding: "0.25rem 0.6rem",
                            borderRadius: "4px",
                            fontWeight: "700",
                            textTransform: "uppercase",
                            fontSize: "0.75rem",
                          }}
                        >
                          {riskLevel}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}

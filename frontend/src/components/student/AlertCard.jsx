import React, { useState } from "react";
import { acknowledgeAlert, reportFalsePositive } from "../../api/studentApi";

export default function AlertCard({ alert, onAlertUpdated }) {
  const [acknowledged, setAcknowledged] = useState(Boolean(alert.acknowledged_at));
  const [falsePositiveSubmitted, setFalsePositiveSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAcknowledge() {
    setError(null);
    setLoading(true);
    try {
      await acknowledgeAlert(alert.id);
      setAcknowledged(true);
      if (onAlertUpdated) onAlertUpdated();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to acknowledge alert.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFalsePositive() {
    setError(null);
    setLoading(true);
    try {
      await reportFalsePositive(alert.id);
      setFalsePositiveSubmitted(true);
      if (onAlertUpdated) onAlertUpdated();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to report false positive.");
    } finally {
      setLoading(false);
    }
  }

  const riskClass = `risk-badge risk-${(alert.risk_level || "low").toLowerCase()}`;

  return (
    <div className="alert-card card">
      <div className="alert-header">
        <span className={riskClass}>Risk Level: {alert.risk_level?.toUpperCase()}</span>
        <span className="risk-score">Score: {alert.risk_score}</span>
      </div>

      <div className="alert-body">
        <p><strong>Symptoms:</strong> {alert.symptoms}</p>
        <p><strong>Preventive Measures:</strong> {alert.preventive_measures || alert.precautions}</p>
        <p><strong>Recommended Action:</strong> {alert.recommended_action || alert.precautions}</p>
        <p className="alert-date">
          <small>Reported on: {new Date(alert.created_at).toLocaleDateString()}</small>
        </p>
      </div>

      {error && <p className="error-text" role="alert">{error}</p>}

      <div className="alert-actions">
        {!acknowledged ? (
          <button
            className="btn-acknowledge"
            onClick={handleAcknowledge}
            disabled={loading}
          >
            {loading ? "Processing..." : "Acknowledge Alert"}
          </button>
        ) : (
          <span className="text-muted">Acknowledged</span>
        )}

        {!falsePositiveSubmitted ? (
          <button
            className="btn-false-positive"
            onClick={handleFalsePositive}
            disabled={loading}
          >
            Report False Positive
          </button>
        ) : (
          <span className="text-muted">Flagged as False Positive</span>
        )}
      </div>
    </div>
  );
}

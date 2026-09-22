import React, { useState, useEffect } from "react";
import { getAnalyticsSummary } from "../../api/adminApi";

export default function AnalyticsSummaryPanel() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadSummary() {
      setLoading(true);
      setError(null);
      try {
        const data = await getAnalyticsSummary();
        setSummary(data);
      } catch (err) {
        setError(err.response?.data?.error || "Failed to load analytics summary.");
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
  }, []);

  return (
    <div className="card analytics-summary-panel" data-testid="analytics-summary-panel">
      <h2>Campus Outbreak Analytics</h2>
      <p className="subtitle">
        Institution-wide metrics across contact networks, secondary exposures, and case statuses.
      </p>

      {error && <p className="error-text" role="alert">{error}</p>}

      {loading ? (
        <p className="text-muted" style={{ marginTop: "1rem" }}>Loading analytics summary…</p>
      ) : (
        <div className="kpi-grid">
          {/* Metric 1: Total Cases */}
          <div className="kpi-card" data-testid="kpi-total-cases">
            <div className="kpi-number">
              {summary?.total_cases != null ? summary.total_cases : 0}
            </div>
            <div className="kpi-label">Total Cases</div>
          </div>

          {/* Metric 2: Average Contacts per Case */}
          <div className="kpi-card" data-testid="kpi-avg-contacts">
            <div className="kpi-number kpi-primary">
              {summary?.avg_contacts_per_case != null ? summary.avg_contacts_per_case : 0}
            </div>
            <div className="kpi-label">Average Contacts per Case</div>
          </div>

          {/* Metric 3: Secondary Contacts (Depth 2+) */}
          <div className="kpi-card" data-testid="kpi-secondary-contacts">
            <div className="kpi-number kpi-warning">
              {summary?.secondary_contacts != null
                ? summary.secondary_contacts
                : summary?.secondary_contacts_count != null
                ? summary.secondary_contacts_count
                : 0}
            </div>
            <div className="kpi-label">Secondary (Depth 2+) Contacts</div>
          </div>

          {/* Metric 4: Active vs. Pending Cases */}
          <div className="kpi-card" data-testid="kpi-active-pending">
            <div className="kpi-number kpi-split">
              <span className="text-danger" title="Active (Confirmed)">
                {summary?.confirmed_cases != null
                  ? summary.confirmed_cases
                  : summary?.active_cases != null
                  ? summary.active_cases
                  : 0}
              </span>
              <span style={{ color: "#94a3b8", fontSize: "1.25rem" }}>/</span>
              <span className="text-warning" title="Pending (Reported)">
                {summary?.pending_cases != null ? summary.pending_cases : 0}
              </span>
            </div>
            <div className="kpi-label">Active vs. Pending Cases</div>
          </div>
        </div>
      )}

      {!loading && !error && (
        <div className="analytics-chart" aria-label="Contact exposure chart">
          <h3>Exposure Profile</h3>
          <p className="text-muted">A visual comparison of direct and secondary contacts in the traced network.</p>
          {[
            ["Direct contacts", summary?.direct_contacts ?? 0, "#2563eb"],
            ["Secondary contacts", summary?.secondary_contacts ?? summary?.secondary_contacts_count ?? 0, "#f59e0b"],
            ["Confirmed cases", summary?.confirmed_cases ?? summary?.active_cases ?? 0, "#ef4444"],
            ["Pending cases", summary?.pending_cases ?? 0, "#8b5cf6"],
          ].map(([label, value, colour]) => {
            const maxValue = Math.max(
              summary?.direct_contacts ?? 0,
              summary?.secondary_contacts ?? summary?.secondary_contacts_count ?? 0,
              summary?.confirmed_cases ?? summary?.active_cases ?? 0,
              summary?.pending_cases ?? 0,
              1
            );
            return (
              <div className="analytics-chart-row" key={label}>
                <span>{label}</span>
                <div className="analytics-chart-track">
                  <div
                    className="analytics-chart-bar"
                    style={{ width: `${(Number(value) / maxValue) * 100}%`, background: colour }}
                  />
                </div>
                <strong>{value}</strong>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

import React, { useState, useEffect } from "react";
import { getCases, confirmCase } from "../api/adminApi";
import { getUser, clearSession } from "../auth/authStorage";
import { useNavigate } from "react-router-dom";
import NetworkGraphView from "../components/admin/NetworkGraphView";
import DiseaseKBEditor from "../components/admin/DiseaseKBEditor";
import CapacityView from "../components/admin/CapacityView";
import PriorityQueueView from "../components/admin/PriorityQueueView";
import AnalyticsSummaryPanel from "../components/admin/AnalyticsSummaryPanel";
import RiskBreakdownView from "../components/admin/RiskBreakdownView";
import DashboardShell from "../components/layout/DashboardShell";
import ModuleCard from "../components/layout/ModuleCard";
import "./admin.css";

export default function HealthAdminDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);
  const [selectedBreakdownCaseId, setSelectedBreakdownCaseId] = useState(null);

  async function loadCases() {
    setLoading(true);
    setError(null);
    try {
      const data = await getCases();
      setCases(data.items || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load health cases.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  async function handleConfirmCase(caseId) {
    setActionLoading(caseId);
    setError(null);
    try {
      await confirmCase(caseId);
      loadCases();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to confirm case.");
    } finally {
      setActionLoading(null);
    }
  }

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  return (
    <DashboardShell
      title="Health Admin Portal"
      subtitle="Epidemiological Surveillance, Contact Network Tracing & Facility Management"
      error={error}
      onLogout={handleLogout}
    >
      <div className="admin-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        {/* Card-based Module Entry Points */}
        <div className="module-entry-grid">
          <ModuleCard
            title="Health Cases Tracker"
            description="Real-time case confirmation, disease matching, and severity surveillance"
            badge={`${cases.length} Cases`}
            badgeType={cases.length > 0 ? "warning" : "success"}
            actionText="Track Cases →"
            href="#cases-module"
          />
          <ModuleCard
            title="Contact Graph Tracing"
            description="Temporal and spatial BFS contact traversal forward and backward from onset"
            badge="Graph Engine"
            badgeType="primary"
            actionText="Trace Contacts →"
            href="#contact-graph-module"
          />
          <ModuleCard
            title="Isolation Facility"
            description="Beds inventory management and priority-queue isolation allocation"
            badge="Beds Allocation"
            badgeType="primary"
            actionText="Manage Beds →"
            href="#capacity-module"
          />
          <ModuleCard
            title="Disease Knowledge Base"
            description="Central disease definitions, symptoms, incubation periods, and precautions"
            badge="KB Records"
            badgeType="primary"
            actionText="Manage KB →"
            href="#disease-kb-module"
          />
        </div>

        {/* Analytics Summary Section */}
        <div id="analytics-summary-module" style={{ marginBottom: "1.5rem" }}>
          <AnalyticsSummaryPanel />
        </div>

        <div className="dashboard-grid">
          <section className="column">
            <ModuleCard
              id="cases-module"
              title="Health Cases Tracker"
              description="Reported student incidents requiring clinical assessment or confirmation"
            >
              {loading ? (
                <p>Loading reported cases...</p>
              ) : cases.length === 0 ? (
                <p className="text-muted">No health cases reported.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>User ID</th>
                      <th>Onset Date</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((c) => (
                      <tr key={c.id}>
                        <td>#{c.id}</td>
                        <td>User #{c.user_id}</td>
                        <td>{c.onset_date}</td>
                        <td>{c.severity}</td>
                        <td>
                          <span className={`status-badge status-${c.status}`}>{c.status}</span>
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                            {c.status === "reported" && (
                              <button
                                className="btn-confirm"
                                disabled={actionLoading === c.id}
                                onClick={() => handleConfirmCase(c.id)}
                              >
                                Confirm Case
                              </button>
                            )}
                            <button
                              type="button"
                              style={{
                                fontSize: "0.78rem",
                                padding: "0.3rem 0.6rem",
                                background: selectedBreakdownCaseId === c.id ? "#1e3a5f" : "#f1f5f9",
                                color: selectedBreakdownCaseId === c.id ? "#fff" : "#334155",
                                border: "1px solid #cbd5e1",
                                borderRadius: "4px",
                                cursor: "pointer",
                                fontWeight: "600",
                              }}
                              onClick={() =>
                                setSelectedBreakdownCaseId(
                                  selectedBreakdownCaseId === c.id ? null : c.id
                                )
                              }
                            >
                              {selectedBreakdownCaseId === c.id ? "Hide Breakdown" : "View Breakdown"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </ModuleCard>

            {selectedBreakdownCaseId && (
              <div id="risk-breakdown-module">
                <RiskBreakdownView caseId={selectedBreakdownCaseId} />
              </div>
            )}

            <div id="contact-graph-module">
              <NetworkGraphView cases={cases} />
            </div>
          </section>

          <section className="column">
            <div id="capacity-module">
              <CapacityView />
            </div>
            <div id="priority-queue-module">
              <PriorityQueueView />
            </div>
            <div id="disease-kb-module">
              <DiseaseKBEditor />
            </div>
          </section>
        </div>
      </div>
    </DashboardShell>
  );
}

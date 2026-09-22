import React, { useState } from "react";
import { getContactGraph, retraceContactGraph } from "../../api/adminApi";

export default function ContactGraphView() {
  const [caseId, setCaseId] = useState("");
  const [direction, setDirection] = useState("both");
  const [maxDepth, setMaxDepth] = useState(2);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleTrace(e) {
    e.preventDefault();
    if (!caseId) {
      setError("Please enter a Case Health Record ID.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await getContactGraph(caseId, {
        direction,
        max_depth: maxDepth,
      });
      setGraphData(data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to fetch contact graph.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRetrace() {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await retraceContactGraph(caseId, {
        direction,
        max_depth: Number(maxDepth),
      });
      setGraphData(data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to retrace contact graph.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>Contact Graph Tracing</h2>
      <p className="subtitle">
        Trace exposure network forward and backward for reported or confirmed health cases.
      </p>

      <form onSubmit={handleTrace} className="filter-bar">
        <div className="form-group inline">
          <label htmlFor="case-id">Health Record (Case) ID</label>
          <input
            id="case-id"
            type="number"
            placeholder="Case ID"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            required
          />
        </div>

        <div className="form-group inline">
          <label htmlFor="direction-select">Direction</label>
          <select
            id="direction-select"
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
          >
            <option value="both">Both (Forward + Backward)</option>
            <option value="forward">Forward (Exposures caused)</option>
            <option value="backward">Backward (Potential sources)</option>
          </select>
        </div>

        <div className="form-group inline">
          <label htmlFor="depth-select">Max Depth</label>
          <input
            id="depth-select"
            type="number"
            min="1"
            max="5"
            value={maxDepth}
            onChange={(e) => setMaxDepth(e.target.value)}
          />
        </div>

        <button type="submit" disabled={loading} style={{ alignSelf: "flex-end" }}>
          {loading ? "Tracing..." : "Trace Case"}
        </button>
      </form>

      {error && <p className="error-text" role="alert">{error}</p>}

      {graphData && (
        <div className="graph-results-box">
          <div className="graph-header-actions">
            <h3>Contact Graph for Case #{graphData.case_id}</h3>
            <button className="btn-secondary" onClick={handleRetrace} disabled={loading}>
              Re-trigger Tracing Algorithm
            </button>
          </div>

          {Object.entries(graphData.contacts || {}).map(([dirName, contacts]) => (
            <div key={dirName} className="direction-section">
              <h4>{dirName.toUpperCase()} Trace Contacts ({Object.keys(contacts).length})</h4>
              {Object.keys(contacts).length === 0 ? (
                <p className="text-muted">No contacts discovered in {dirName} trace.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Contact User ID</th>
                      <th>Hop Depth</th>
                      <th>Risk Score</th>
                      <th>Risk Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(contacts).map(([uid, info]) => (
                      <tr key={uid}>
                        <td>User #{uid}</td>
                        <td>{info.depth} hop(s)</td>
                        <td>{info.risk_score}</td>
                        <td>
                          <span className={`risk-badge risk-${(info.risk_level || "low").toLowerCase()}`}>
                            {info.risk_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

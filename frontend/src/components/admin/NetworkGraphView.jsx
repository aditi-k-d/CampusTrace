import React, { useEffect, useRef, useState } from "react";
import { getContactGraph, retraceContactGraph } from "../../api/adminApi";

// ---------------------------------------------------------------------------
// Headless / jsdom environment check
// vis-network requires a real DOM canvas context. In vitest / jsdom it is
// unavailable; we detect this once at module load so the component can
// choose a safe fallback branch.
// ---------------------------------------------------------------------------
function canRenderCanvas() {
  try {
    if (typeof document === "undefined") return false;
    // jsdom logs a noisy "not implemented" error before returning null.
    if (typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent)) return false;
    const c = document.createElement("canvas");
    // HTMLCanvasElement.getContext returns null in jsdom without canvas mocks
    return typeof c.getContext === "function" && c.getContext("2d") !== null;
  } catch {
    return false;
  }
}

const IS_CANVAS_ENV = canRenderCanvas();

// ---------------------------------------------------------------------------
// Colour / size map keyed by risk_level
// ---------------------------------------------------------------------------
const RISK_STYLE = {
  high:   { color: "#ef4444", size: 30 },
  medium: { color: "#f59e0b", size: 24 },
  low:    { color: "#10b981", size: 18 },
  source: { color: "#f59e0b", size: 38 }, // gold; overridden below to border gold
};

function buildVisNodes(apiNodes) {
  return apiNodes.map((n) => {
    if (n.is_source) {
      return {
        id: n.id,
        label: `User #${n.id}\n(SOURCE)`,
        color: { background: "#f5c518", border: "#b8860b", highlight: { background: "#ffd700" } },
        size: 38,
        font: { bold: true, size: 14 },
        title: `Source case — User #${n.id}`,
      };
    }
    const level = (n.risk_level || "low").toLowerCase();
    const style = RISK_STYLE[level] || RISK_STYLE.low;
    return {
      id: n.id,
      label: `User #${n.id}`,
      color: { background: style.color, border: "#1e293b", highlight: { background: style.color } },
      size: style.size,
      font: { color: "#fff", size: 12 },
      title: `User #${n.id} | Risk: ${n.risk_level} (${n.risk_score ?? "—"}) | Depth: ${n.depth}`,
    };
  });
}

function buildVisEdges(apiEdges) {
  return apiEdges
    .filter((e) => e.source !== null && e.target !== null)
    .map((e, i) => ({
      id: i,
      from: e.source,
      to: e.target,
      label: e.duration_minutes != null ? `${e.duration_minutes}m` : "",
      title: `Room weight: ${e.weight ?? "—"} | Date: ${e.contact_date ?? "—"} | Duration: ${e.duration_minutes ?? "—"} min`,
      color: { color: "#64748b", highlight: "#334155" },
      font: { size: 11, strokeWidth: 2, strokeColor: "#fff" },
      arrows: "to",
    }));
}

// ---------------------------------------------------------------------------
// Fallback table — rendered when canvas is unavailable (test / headless env)
// ---------------------------------------------------------------------------
function FallbackTable({ graphData }) {
  if (!graphData) {
    return (
      <div data-testid="network-graph-fallback">
        <p className="text-muted">Enter a Case ID and click Trace Case to see the contact network.</p>
      </div>
    );
  }

  const nodes = graphData.graph?.nodes || [];
  const edges = graphData.graph?.edges || [];

  return (
    <div data-testid="network-graph-fallback">
      <h3>Contact Graph for Case #{graphData.case_id} (List View)</h3>
      <p className="text-muted" style={{ marginBottom: "0.75rem" }}>
        Canvas rendering is unavailable in this environment — showing tabular data.
      </p>

      <h4>Nodes ({nodes.length})</h4>
      {nodes.length === 0 ? (
        <p className="text-muted">No nodes.</p>
      ) : (
        <table className="data-table" data-testid="fallback-nodes-table">
          <thead>
            <tr>
              <th>User ID</th>
              <th>Role</th>
              <th>Depth</th>
              <th>Risk Level</th>
              <th>Risk Score</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.id} data-testid={`fallback-node-${n.id}`}>
                <td>User #{n.id}</td>
                <td>{n.is_source ? "Source" : "Contact"}</td>
                <td>{n.depth}</td>
                <td>{n.risk_level ?? "—"}</td>
                <td>{n.risk_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4 style={{ marginTop: "1rem" }}>Edges ({edges.length})</h4>
      {edges.length === 0 ? (
        <p className="text-muted">No edges.</p>
      ) : (
        <table className="data-table" data-testid="fallback-edges-table">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Duration</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {edges.map((e, i) => (
              <tr key={i}>
                <td>{e.source != null ? `User #${e.source}` : "—"}</td>
                <td>{e.target != null ? `User #${e.target}` : "—"}</td>
                <td>{e.duration_minutes != null ? `${e.duration_minutes} min` : "—"}</td>
                <td>{e.contact_date ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// vis-network canvas renderer — only mounted when IS_CANVAS_ENV is true
// ---------------------------------------------------------------------------
function VisNetworkCanvas({ graphData }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    const nodes = buildVisNodes(graphData.graph?.nodes || []);
    const edges = buildVisEdges(graphData.graph?.edges || []);

    // The default vis-network entry point is the peer build and does not
    // export DataSet.  The standalone build bundles it, which is required
    // to construct the node and edge collections used by Network.
    import("vis-network/standalone").then(({ Network, DataSet }) => {
      const visNodes = new DataSet(nodes);
      const visEdges = new DataSet(edges);

      const options = {
        physics: {
          enabled: true,
          solver: "forceAtlas2Based",
          stabilization: { iterations: 150 },
        },
        interaction: {
          hover: true,
          tooltipDelay: 100,
        },
        layout: {
          randomSeed: 42,
        },
        nodes: {
          shape: "dot",
          borderWidth: 2,
          shadow: true,
        },
        edges: {
          smooth: { type: "continuous" },
          shadow: false,
        },
      };

      if (networkRef.current) {
        networkRef.current.destroy();
      }
      networkRef.current = new Network(
        containerRef.current,
        { nodes: visNodes, edges: visEdges },
        options
      );
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [graphData]);

  return (
    <div
      ref={containerRef}
      data-testid="vis-network-canvas"
      style={{
        width: "100%",
        height: "500px",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        background: "#f8fafc",
      }}
    />
  );
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------
function Legend() {
  const items = [
    { color: "#f5c518", label: "Source (Case Patient)" },
    { color: "#ef4444", label: "High Risk" },
    { color: "#f59e0b", label: "Medium Risk" },
    { color: "#10b981", label: "Low Risk" },
  ];
  return (
    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
      {items.map(({ color, label }) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem" }}>
          <span style={{
            width: 14, height: 14, borderRadius: "50%", background: color,
            border: "1px solid #1e293b", display: "inline-block",
          }} />
          {label}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function NetworkGraphView({ cases = [] }) {
  const [caseId, setCaseId] = useState("");
  const [direction, setDirection] = useState("both");
  const [maxDepth, setMaxDepth] = useState(2);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // A seeded demo should be immediately demonstrable.  Keep the manual Case
  // ID entry, but preselect and trace the latest available health record.
  useEffect(() => {
    if (!caseId && cases.length > 0) {
      setCaseId(String(cases[0].id));
    }
  }, [cases, caseId]);

  useEffect(() => {
    const isSelectedDemoCase = cases.some((healthCase) => String(healthCase.id) === String(caseId));
    if (!isSelectedDemoCase || graphData?.case_id === Number(caseId)) return;

    let cancelled = false;
    async function loadSelectedCase() {
      setLoading(true);
      setError(null);
      try {
        const data = await getContactGraph(caseId, { direction, max_depth: maxDepth });
        if (!cancelled) setGraphData(data);
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.error || "Failed to fetch contact graph.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadSelectedCase();
    return () => { cancelled = true; };
  }, [caseId, cases]);

  async function handleTrace(e) {
    e.preventDefault();
    if (!caseId) {
      setError("Please enter a Case Health Record ID.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getContactGraph(caseId, { direction, max_depth: maxDepth });
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
      <h2>Contact Network Graph</h2>
      <p className="subtitle">
        Visualise the exposure network for a reported or confirmed health case.
        Nodes are sized and coloured by risk level; edge labels show contact duration.
      </p>

      <form onSubmit={handleTrace} className="filter-bar">
        <div className="form-group inline">
          <label htmlFor="ng-case-id">Health Record (Case) ID</label>
          <input
            id="ng-case-id"
            type="number"
            placeholder="Case ID"
            value={caseId}
            onChange={(e) => {
              setCaseId(e.target.value);
              setGraphData(null);
            }}
            required
          />
        </div>

        {cases.length > 0 && (
          <div className="form-group inline">
            <label htmlFor="ng-case-picker">Demo case</label>
            <select
              id="ng-case-picker"
              value={caseId}
              onChange={(e) => {
                setCaseId(e.target.value);
                setGraphData(null);
              }}
            >
              {cases.map((healthCase) => (
                <option key={healthCase.id} value={healthCase.id}>
                  Case #{healthCase.id} — {healthCase.status}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="form-group inline">
          <label htmlFor="ng-direction">Direction</label>
          <select id="ng-direction" value={direction} onChange={(e) => setDirection(e.target.value)}>
            <option value="both">Both (Forward + Backward)</option>
            <option value="forward">Forward (Exposures caused)</option>
            <option value="backward">Backward (Potential sources)</option>
          </select>
        </div>

        <div className="form-group inline">
          <label htmlFor="ng-depth">Max Depth</label>
          <input
            id="ng-depth"
            type="number"
            min="1"
            max="5"
            value={maxDepth}
            onChange={(e) => setMaxDepth(e.target.value)}
          />
        </div>

        <button type="submit" disabled={loading} style={{ alignSelf: "flex-end" }}>
          {loading ? "Tracing…" : "Trace Case"}
        </button>
      </form>

      {error && <p className="error-text" role="alert">{error}</p>}

      {graphData && (
        <div style={{ marginTop: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>
              Case #{graphData.case_id} — {(graphData.graph?.nodes?.length ?? 0)} node(s),{" "}
              {(graphData.graph?.edges?.length ?? 0)} edge(s)
            </h3>
            <button className="btn-secondary" onClick={handleRetrace} disabled={loading}>
              Re-trigger Tracing
            </button>
          </div>
          <Legend />
          {IS_CANVAS_ENV ? (
            <VisNetworkCanvas graphData={graphData} />
          ) : (
            <FallbackTable graphData={graphData} />
          )}
        </div>
      )}

      {!graphData && !loading && (
        IS_CANVAS_ENV ? null : <FallbackTable graphData={null} />
      )}
    </div>
  );
}

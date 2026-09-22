import React, { useState, useEffect } from "react";
import { getAuditLog } from "../../api/adminApi";

export default function AuditLogViewer() {
  const [logs, setLogs] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [filterUser, setFilterUser] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadLogs(cursor = null, append = false) {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (filterUser) params.user_id = filterUser;
      if (filterAction) params.action = filterAction;
      if (cursor) params.cursor = cursor;

      const data = await getAuditLog(params);
      setLogs((prev) => (append ? [...prev, ...data.items] : data.items));
      setNextCursor(data.next_cursor);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  function handleFilterSubmit(e) {
    e.preventDefault();
    loadLogs(null, false);
  }

  function handleLoadMore() {
    if (nextCursor) {
      loadLogs(nextCursor, true);
    }
  }

  return (
    <div className="card">
      <h2>Institute Audit Log Viewer</h2>
      <p className="subtitle">
        Audited log of administrative actions across the CampusTrace system.
      </p>

      <form onSubmit={handleFilterSubmit} className="filter-bar">
        <div className="form-group inline">
          <label htmlFor="filter-user">User ID</label>
          <input
            id="filter-user"
            type="number"
            placeholder="User ID"
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
          />
        </div>

        <div className="form-group inline">
          <label htmlFor="filter-action">Action</label>
          <input
            id="filter-action"
            type="text"
            placeholder="e.g. create_division"
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
          />
        </div>

        <button type="submit" disabled={loading} style={{ alignSelf: "flex-end" }}>
          Filter Logs
        </button>
      </form>

      {error && <p className="error-text" role="alert">{error}</p>}

      {loading && logs.length === 0 ? (
        <p>Loading audit logs...</p>
      ) : logs.length === 0 ? (
        <p className="text-muted">No audit log entries found matching filters.</p>
      ) : (
        <div className="audit-log-box">
          <table className="data-table">
            <thead>
              <tr>
                <th>Log ID</th>
                <th>User ID</th>
                <th>Action</th>
                <th>Target Type</th>
                <th>Target ID</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.id}</td>
                  <td>User #{log.user_id}</td>
                  <td><strong>{log.action}</strong></td>
                  <td>{log.target_type || "N/A"}</td>
                  <td>{log.target_id || "N/A"}</td>
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {nextCursor && (
            <div className="load-more-box">
              <button className="btn-secondary" onClick={handleLoadMore} disabled={loading}>
                {loading ? "Loading..." : "Load More Logs"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

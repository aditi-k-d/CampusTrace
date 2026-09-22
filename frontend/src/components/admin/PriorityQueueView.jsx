import React, { useState, useEffect } from "react";
import { getPriorityQueue } from "../../api/adminApi";

export default function PriorityQueueView() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadQueue() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPriorityQueue();
        const items = Array.isArray(data) ? data : (data?.queue || []);
        // Strictly use API order — do NOT re-sort
        setQueue(items);
      } catch (err) {
        setError(err.response?.data?.error || "Failed to load priority queue.");
      } finally {
        setLoading(false);
      }
    }

    loadQueue();
  }, []);

  return (
    <div className="card priority-queue-card" data-testid="priority-queue-view">
      <h2>High-Risk Contact Priority Queue</h2>
      <p className="subtitle">
        Ranked waiting list by risk score for bed triage and immediate isolation allocation.
      </p>

      {error && <p className="error-text" role="alert">{error}</p>}

      {loading ? (
        <p className="text-muted" style={{ marginTop: "0.75rem" }}>Loading priority queue…</p>
      ) : queue.length === 0 ? (
        <p className="text-muted" style={{ marginTop: "0.75rem" }}>No contacts currently waiting in priority queue.</p>
      ) : (
        <table className="data-table priority-queue-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>User</th>
              <th>Priority Score</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((item, index) => {
              const rankNum = item.rank != null ? item.rank : index + 1;
              const isRankOne = rankNum === 1;
              const displayName =
                item.user_name ||
                item.name ||
                (item.user_id ? `User #${item.user_id}` : `Contact #${rankNum}`);
              const score =
                item.priority_score != null
                  ? Number(item.priority_score).toFixed(1)
                  : "0.0";

              return (
                <tr
                  key={item.user_id || index}
                  className={`priority-queue-row ${isRankOne ? "rank-first top-priority highlight-rank-1" : ""}`}
                  data-testid={isRankOne ? "rank-1-row" : `rank-${rankNum}-row`}
                >
                  <td>
                    <span
                      className={`rank-badge ${isRankOne ? "rank-badge-first" : ""}`}
                    >
                      #{rankNum}
                    </span>
                  </td>
                  <td>
                    <strong>{displayName}</strong>
                    {isRankOne && (
                      <span
                        className="top-priority-pill"
                        data-testid="rank-1-badge"
                      >
                        Top Priority
                      </span>
                    )}
                  </td>
                  <td>
                    <span className={isRankOne ? "text-danger" : ""} style={{ fontWeight: 600 }}>
                      {score}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn-allocate-placeholder btn-secondary"
                      style={{ fontSize: "0.78rem", padding: "0.3rem 0.65rem" }}
                      onClick={() =>
                        console.log(
                          `Allocate bed for user ${item.user_id || displayName} (Score: ${score})`
                        )
                      }
                    >
                      Allocate Bed
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

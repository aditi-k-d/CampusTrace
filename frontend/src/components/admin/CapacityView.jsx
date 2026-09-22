import React, { useState, useEffect } from "react";
import { getCapacity, allocateBed } from "../../api/adminApi";

export default function CapacityView() {
  const [facilities, setFacilities] = useState([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState("");
  const [targetUserId, setTargetUserId] = useState("");
  const [loading, setLoading] = useState(true);
  const [allocating, setAllocating] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  async function loadCapacity() {
    setLoading(true);
    setError(null);
    try {
      const data = await getCapacity();
      // The health-admin API wraps facilities in `{ items: [...] }`, while
      // tests and older API versions may return the array directly.
      const items = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
      setFacilities(items);
      if (items.length > 0 && !selectedFacilityId) {
        setSelectedFacilityId(items[0].id);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load facility capacity.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCapacity();
  }, []);

  async function handleAllocate(e) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!selectedFacilityId) {
      setError("Please select a facility.");
      return;
    }

    setAllocating(true);
    try {
      const res = await allocateBed(
        selectedFacilityId,
        targetUserId ? Number(targetUserId) : null
      );
      setMessage(
        `Bed allocated successfully (Bed #${res.allocated_bed_number} for User #${res.allocated_user_id}).`
      );
      setTargetUserId("");
      loadCapacity();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to allocate bed.");
    } finally {
      setAllocating(false);
    }
  }

  return (
    <div className="card">
      <h2>Isolation Facility Capacity & Bed Allocation</h2>

      {loading ? (
        <p>Loading capacity data...</p>
      ) : facilities.length === 0 ? (
        <p className="text-muted">No facility capacity records found.</p>
      ) : (
        <div className="facilities-grid">
          {facilities.map((fac) => (
            <div key={fac.id} className="facility-card card">
              <h3>{fac.facility_name}</h3>
              <p><strong>Building / Location:</strong> {fac.building || "Main Campus"}</p>
              <div className="capacity-stats">
                <span className="stat-pill">Total Beds: {fac.total_beds}</span>
                <span className="stat-pill">Occupied: {fac.occupied_beds}</span>
                <span className="stat-pill pill-available">Available: {fac.available_beds}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="allocation-form-box">
        <h3>Allocate Bed (Priority-Queue Driven)</h3>
        <p className="subtitle">
          Leave User ID blank to automatically allocate to the highest-risk exposure contact.
        </p>

        <form onSubmit={handleAllocate}>
          <div className="form-group">
            <label htmlFor="facility-select">Select Facility</label>
            <select
              id="facility-select"
              value={selectedFacilityId}
              onChange={(e) => setSelectedFacilityId(e.target.value)}
              required
            >
              <option value="">-- Select Facility --</option>
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.facility_name} ({f.available_beds} beds available)
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="user-id-input">User ID (Optional - Auto-selects highest risk if blank)</label>
            <input
              id="user-id-input"
              type="number"
              placeholder="Enter User ID or leave blank"
              value={targetUserId}
              onChange={(e) => setTargetUserId(e.target.value)}
            />
          </div>

          {error && <p className="error-text" role="alert">{error}</p>}
          {message && <p className="success-text">{message}</p>}

          <button type="submit" disabled={allocating}>
            {allocating ? "Allocating..." : "Allocate Bed"}
          </button>
        </form>
      </div>
    </div>
  );
}

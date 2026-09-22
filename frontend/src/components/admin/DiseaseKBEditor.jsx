import React, { useState, useEffect } from "react";
import { getDiseaseKB, createDiseaseKB, updateDiseaseKB } from "../../api/adminApi";

export default function DiseaseKBEditor() {
  const [entries, setEntries] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [name, setName] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [preventiveMeasures, setPreventiveMeasures] = useState("");
  const [incubationDays, setIncubationDays] = useState(5);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  async function loadEntries() {
    setLoading(true);
    setError(null);
    try {
      const data = await getDiseaseKB();
      // The API response is `{ items: [...] }`.  Keeping the state as an
      // array prevents this dashboard module from crashing if the API ever
      // returns an empty or unexpected payload.
      setEntries(Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load Disease KB entries.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEntries();
  }, []);

  function handleEditClick(entry) {
    setEditingId(entry.id);
    setName(entry.name);
    setSymptoms(entry.symptoms);
    setPreventiveMeasures(entry.preventive_measures);
    setIncubationDays(entry.incubation_period_days || 5);
    setMessage(null);
    setError(null);
  }

  function resetForm() {
    setEditingId(null);
    setName("");
    setSymptoms("");
    setPreventiveMeasures("");
    setIncubationDays(5);
  }

  function handleCancelEdit() {
    resetForm();
    setMessage(null);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    const payload = {
      name,
      symptoms,
      preventive_measures: preventiveMeasures,
      incubation_period_days: Number(incubationDays),
    };

    setSubmitting(true);
    try {
      if (editingId) {
        await updateDiseaseKB(editingId, payload);
        setMessage(`Disease KB entry #${editingId} updated successfully.`);
      } else {
        await createDiseaseKB(payload);
        setMessage(`New Disease KB entry '${name}' created successfully.`);
      }
      resetForm();
      loadEntries();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to save Disease KB entry.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Disease Knowledge Base Editor</h2>

      <form onSubmit={handleSubmit} className="kb-form">
        <h3>{editingId ? `Edit Entry #${editingId}` : "Add New Knowledge Base Entry"}</h3>

        <div className="form-group">
          <label htmlFor="kb-name">Disease Name</label>
          <input
            id="kb-name"
            type="text"
            placeholder="e.g. Chickenpox, Influenza"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="kb-symptoms">Symptoms</label>
          <textarea
            id="kb-symptoms"
            rows="2"
            placeholder="e.g. fever, rash, fatigue"
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="kb-preventive">Preventive Measures</label>
          <textarea
            id="kb-preventive"
            rows="2"
            placeholder="e.g. Isolate for 7 days, sanitize surfaces"
            value={preventiveMeasures}
            onChange={(e) => setPreventiveMeasures(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="kb-incubation">Incubation Period (Days)</label>
          <input
            id="kb-incubation"
            type="number"
            value={incubationDays}
            onChange={(e) => setIncubationDays(e.target.value)}
            required
          />
        </div>

        {error && <p className="error-text" role="alert">{error}</p>}
        {message && <p className="success-text">{message}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : editingId ? "Update Entry" : "Add Entry"}
          </button>
          {editingId && (
            <button type="button" className="btn-secondary" onClick={handleCancelEdit}>
              Cancel Edit
            </button>
          )}
        </div>
      </form>

      <div className="kb-list-box">
        <h3>Knowledge Base Entries</h3>
        {loading ? (
          <p>Loading entries...</p>
        ) : entries.length === 0 ? (
          <p className="text-muted">No disease knowledge base entries found.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Disease Name</th>
                <th>Symptoms</th>
                <th>Incubation</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.id}</td>
                  <td><strong>{entry.name}</strong></td>
                  <td>{entry.symptoms}</td>
                  <td>{entry.incubation_period_days} days</td>
                  <td>
                    <button
                      className="btn-edit"
                      onClick={() => handleEditClick(entry)}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

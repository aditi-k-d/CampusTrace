import React, { useState, useEffect } from "react";
import { selfAssessment, getDiseases } from "../../api/studentApi";

export default function SelfAssessment() {
  const [symptomsInput, setSymptomsInput] = useState("");
  const [diseases, setDiseases] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDiseases() {
      try {
        const data = await getDiseases();
        setDiseases(data || []);
      } catch {
        setDiseases([]);
      }
    }
    loadDiseases();
  }, []);

  async function handleCheck(e) {
    e.preventDefault();
    setError(null);
    if (!symptomsInput.trim()) {
      setError("Please enter your symptoms to run assessment.");
      return;
    }

    setLoading(true);
    try {
      const res = await selfAssessment(symptomsInput);
      setResult(res);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to run self assessment.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>Symptom Self-Assessment Triage</h2>
      <p className="subtitle">
        Rule-based triage tool to evaluate symptoms against the campus Disease Knowledge Base.
      </p>

      <form onSubmit={handleCheck}>
        <div className="form-group">
          <label htmlFor="assessment-symptoms">Enter Symptoms</label>
          <input
            id="assessment-symptoms"
            type="text"
            list="disease-symptom-suggestions"
            placeholder="e.g. fever, cough, headache"
            value={symptomsInput}
            onChange={(e) => setSymptomsInput(e.target.value)}
          />
          <datalist id="disease-symptom-suggestions">
            {diseases.map((d) => (
              <option key={d.id} value={d.symptoms}>
                {d.name} symptoms ({d.symptoms})
              </option>
            ))}
          </datalist>
        </div>

        {diseases.length > 0 && (
          <div className="disease-pills" style={{ marginBottom: "1rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
            <span style={{ fontSize: "0.85rem", color: "#64748b" }}>Common Conditions:</span>
            {diseases.map((d) => (
              <button
                key={d.id}
                type="button"
                className="btn-badge"
                style={{
                  fontSize: "0.75rem",
                  padding: "0.2rem 0.5rem",
                  background: "#e2e8f0",
                  border: "none",
                  borderRadius: "12px",
                  cursor: "pointer",
                }}
                onClick={() => setSymptomsInput(d.symptoms)}
              >
                {d.name}
              </button>
            ))}
          </div>
        )}

        {error && <p className="error-text" role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Evaluating..." : "Check Symptoms"}
        </button>
      </form>

      {result && (
        <div className="assessment-result">
          <h3>Assessment Result</h3>
          {result.matched_disease ? (
            <p className="match-tag">Matched Disease: <strong>{result.matched_disease}</strong></p>
          ) : (
            <p className="text-muted">No specific disease match found.</p>
          )}
          <p><strong>Guidance:</strong> {result.guidance}</p>
          <p><strong>Recommended Action:</strong> {result.recommended_action}</p>
        </div>
      )}
    </div>
  );
}

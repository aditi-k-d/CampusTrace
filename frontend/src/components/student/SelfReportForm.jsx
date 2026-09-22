import React, { useState, useEffect } from "react";
import { reportHealth, getDiseases } from "../../api/studentApi";

export default function SelfReportForm({ onReportSubmitted }) {
  const [onsetDate, setOnsetDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [severity, setSeverity] = useState("mild");
  const [diseaseId, setDiseaseId] = useState("");
  const [customSymptoms, setCustomSymptoms] = useState("");
  const [diseases, setDiseases] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchDiseases() {
      try {
        const data = await getDiseases();
        setDiseases(data || []);
      } catch (err) {
        // Soft fallback
        setDiseases([]);
      }
    }
    fetchDiseases();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!diseaseId && !customSymptoms.trim()) {
      setError("Please select a disease or describe your custom symptoms.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        onset_date: onsetDate,
        severity: severity,
      };

      if (diseaseId) {
        payload.disease_id = Number(diseaseId);
      }
      if (customSymptoms.trim()) {
        payload.custom_symptoms = customSymptoms.trim();
      }

      const result = await reportHealth(payload);
      setMessage("Health report submitted successfully.");
      setCustomSymptoms("");
      setDiseaseId("");
      if (onReportSubmitted) {
        onReportSubmitted(result);
      }
    } catch (err) {
      setError(
        err.response?.data?.error || "Failed to submit health report."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h2>Report Health Issue</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="onset-date">Onset Date</label>
          <input
            id="onset-date"
            type="date"
            value={onsetDate}
            onChange={(e) => setOnsetDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="severity">Severity</label>
          <select
            id="severity"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            required
          >
            <option value="mild">Mild</option>
            <option value="moderate">Moderate</option>
            <option value="severe">Severe</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="disease-lookup">Known Disease (Lookup)</label>
          <select
            id="disease-lookup"
            value={diseaseId}
            onChange={(e) => {
              setDiseaseId(e.target.value);
              if (e.target.value) {
                const selected = diseases.find((d) => d.id === Number(e.target.value));
                if (selected && !customSymptoms) {
                  setCustomSymptoms(selected.symptoms);
                }
              }
            }}
          >
            <option value="">-- Select Disease (Optional) --</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} {d.icd_code ? `(${d.icd_code})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="custom-symptoms">Symptoms</label>
          <textarea
            id="custom-symptoms"
            rows="3"
            placeholder="Describe your symptoms (e.g., fever, cough, headache)"
            value={customSymptoms}
            onChange={(e) => setCustomSymptoms(e.target.value)}
          />
        </div>

        {error && <p className="error-text" role="alert">{error}</p>}
        {message && <p className="success-text">{message}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "Submitting..." : "Submit Health Report"}
        </button>
      </form>
    </div>
  );
}

import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import client from "../api/client";
import "./auth.css";

// Registration policy (see docs/api_contract.md): only 'student' can
// self-register through a public form. Other roles are created by an
// authenticated institute_admin elsewhere (Person 4's admin panel),
// so this page deliberately doesn't offer a role picker.
export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // TODO(Person 2/4): replace with a <select> populated from a
  // GET /divisions endpoint once one exists — not in api_contract.md yet.
  const [divisionId, setDivisionId] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await client.post("/auth/register", {
        name,
        email,
        password,
        role: "student",
        division_id: Number(divisionId),
      });
      navigate("/login", { replace: true, state: { justRegistered: true } });
    } catch (err) {
      setError(err.response?.data?.error || "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      {/* Left brand panel */}
      <div className="auth-brand-panel">
        <div className="auth-brand-emblem">🏛️</div>
        <h1 className="auth-brand-name">Join CampusTrace</h1>
        <p className="auth-brand-tagline">
          Create your student account to access health services, course tracking, and exposure alerts.
        </p>
        <div className="auth-brand-features">
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">📚</span>
            Course enrollment & batch management
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🩺</span>
            Confidential health self-reporting
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🔔</span>
            Private exposure alert notifications
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🩹</span>
            Symptom triage & assessment tools
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-form-panel">
        <form className="auth-card" onSubmit={handleSubmit}>
          <div className="auth-card-header">
            <div className="auth-card-logo">🏛️</div>
            <h1>Create your account</h1>
            <p className="auth-card-subtitle">Student self-registration — institutional credentials only.</p>
          </div>

          <div className="auth-field">
            <label htmlFor="name">Full name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Your full name"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@institution.edu"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Min. 8 characters"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="division">Division ID</label>
            <input
              id="division"
              type="number"
              value={divisionId}
              onChange={(e) => setDivisionId(e.target.value)}
              required
              placeholder="Your division number"
            />
          </div>

          {error && (
            <p className="auth-error" role="alert">
              ⚠ {error}
            </p>
          )}

          <button type="submit" className="auth-submit-btn" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

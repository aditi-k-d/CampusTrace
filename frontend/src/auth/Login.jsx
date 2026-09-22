import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import client from "../api/client";
import { saveSession } from "./authStorage";
import "./auth.css";

// Where each role lands after login. Person 2-4 should update the path
// here once their dashboard route exists (see App.jsx).
const ROLE_HOME = {
  student: "/student",
  course_faculty: "/faculty",
  class_teacher: "/class-teacher",
  health_admin: "/health-admin",
  institute_admin: "/institute-admin",
};

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await client.post("/auth/login", { email, password });
      saveSession(data.access_token, data.user);

      if (data.user.role === "student") {
        try {
          const coursesRes = await client.get("/student/courses");
          const unbatched = (coursesRes.data || []).some(
            (c) => (c.course_type === "lab" || c.course_type === "tutorial") && !c.batch_id
          );
          if (unbatched) {
            navigate("/batch-selection", { replace: true });
            return;
          }
        } catch {
          // proceed to standard role home if check fails
        }
      }

      navigate(ROLE_HOME[data.user.role] || "/", { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      {/* Left brand panel */}
      <div className="auth-brand-panel">
        <div className="auth-brand-emblem">🏛️</div>
        <h1 className="auth-brand-name">CampusTrace</h1>
        <p className="auth-brand-tagline">
          Integrated health surveillance and contact-tracing for modern campuses.
        </p>
        <div className="auth-brand-features">
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🔒</span>
            Role-based secure access
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🕸️</span>
            Real-time contact graph tracing
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">📊</span>
            Outbreak analytics & KPIs
          </div>
          <div className="auth-brand-feature">
            <span className="auth-brand-feature-icon">🏥</span>
            Isolation capacity management
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-form-panel">
        <form className="auth-card" onSubmit={handleSubmit}>
          <div className="auth-card-header">
            <div className="auth-card-logo">🏛️</div>
            <h1>Sign in to CampusTrace</h1>
            <p className="auth-card-subtitle">Enter your institutional credentials to continue.</p>
          </div>

          <div className="auth-field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoFocus
              placeholder="you@institution.edu"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="auth-error" role="alert">
              ⚠ {error}
            </p>
          )}

          <button type="submit" className="auth-submit-btn" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>

          <p className="auth-switch">
            New student? <Link to="/register">Create an account</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

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
      navigate(ROLE_HOME[data.user.role] || "/", { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Sign in to CampusTrace</h1>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          autoFocus
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>

        <p className="auth-switch">
          New student? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </div>
  );
}

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
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create your CampusTrace account</h1>

        <label htmlFor="name">Full name</label>
        <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />

        <label htmlFor="division">Division ID</label>
        <input
          id="division"
          type="number"
          value={divisionId}
          onChange={(e) => setDivisionId(e.target.value)}
          required
        />

        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account..." : "Create account"}
        </button>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}

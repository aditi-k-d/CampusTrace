import React from "react";
import { getUser } from "../../auth/authStorage";

const ROLE_NAV_CONFIG = {
  student: [
    { id: "courses", label: "Enrolled Courses", icon: "📚", href: "#courses-module" },
    { id: "self-report", label: "Health Self-Report", icon: "🩺", href: "#self-report-module" },
    { id: "health-history", label: "Health Status & History", icon: "📋", href: "#health-history-module" },
    { id: "exposure-alerts", label: "Exposure Alerts", icon: "🔔", href: "#exposure-alerts-module" },
    { id: "self-assessment", label: "Symptom Self-Assessment", icon: "🩹", href: "#self-assessment-module" },
    { id: "absence-responses", label: "Absence Observations", icon: "⚠️", href: "#absence-responses-module" },
  ],
  course_faculty: [
    { id: "attendance", label: "Attendance & Health", icon: "👥", href: "#attendance-module" },
    { id: "flag-absence", label: "Flag Student Absence", icon: "🚩", href: "#absence-flag-module" },
    { id: "raised-flags", label: "Absence Flags Raised", icon: "📑", href: "#raised-flags-module" },
  ],
  class_teacher: [
    { id: "division", label: "Division Overview", icon: "🏫", href: "#division-module" },
    { id: "escalations", label: "Absence Escalations", icon: "📈", href: "#escalations-module" },
    { id: "approvals", label: "Enrollment Approvals", icon: "✅", href: "#approvals-module" },
  ],
  health_admin: [
    { id: "cases", label: "Cases Tracker", icon: "📊", href: "#cases-module" },
    { id: "analytics", label: "Analytics Summary", icon: "📉", href: "#analytics-summary-module" },
    { id: "contact-graph", label: "Contact Graph Tracing", icon: "🕸️", href: "#contact-graph-module" },
    { id: "risk-breakdown", label: "Risk Breakdown", icon: "⚖️", href: "#risk-breakdown-module" },
    { id: "capacity", label: "Isolation Capacity", icon: "🏥", href: "#capacity-module" },
    { id: "priority-queue", label: "Priority Queue", icon: "📌", href: "#priority-queue-module" },
    { id: "disease-kb", label: "Disease Knowledge Base", icon: "📖", href: "#disease-kb-module" },
  ],
  institute_admin: [
    { id: "analytics", label: "Aggregated Analytics", icon: "📊", href: "#analytics" },
    { id: "structure", label: "Structure & Timetables", icon: "🏛️", href: "#structure" },
    { id: "users", label: "User Role Management", icon: "👤", href: "#users" },
    { id: "config", label: "System Configuration", icon: "⚙️", href: "#config" },
    { id: "audit", label: "Audit Log Viewer", icon: "📜", href: "#audit" },
  ],
};

const ROLE_DISPLAY = {
  student: "Student",
  course_faculty: "Course Faculty",
  class_teacher: "Class Teacher",
  health_admin: "Health Admin",
  institute_admin: "Institute Admin",
};

const ROLE_COLOUR = {
  student:        "#0ea5e9",
  course_faculty: "#8b5cf6",
  class_teacher:  "#f59e0b",
  health_admin:   "#ef4444",
  institute_admin:"#10b981",
};

export default function Sidebar({
  customNavItems,
  activeNav,
  onNavClick,
  user: propUser,
}) {
  const user = propUser || getUser();
  const userRole = user?.role || "student";
  const navItems = customNavItems || ROLE_NAV_CONFIG[userRole] || [];
  const accentColour = ROLE_COLOUR[userRole] || "#2563eb";

  function handleItemClick(e, item) {
    if (onNavClick) onNavClick(item.id);
    if (item.onClick) item.onClick(e);
    if (item.href && item.href.startsWith("#")) {
      const targetEl = document.querySelector(item.href);
      if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <aside className="portal-sidebar" aria-label="Portal Navigation">
      {/* Brand */}
      <div className="portal-sidebar-brand">
        <div className="portal-brand-emblem" aria-hidden="true">🏛️</div>
        <div>
          <h2 className="portal-brand-title">CampusTrace</h2>
          <p className="portal-brand-subtitle">University Intranet</p>
        </div>
      </div>

      {/* Role pill */}
      <div style={{
        padding: "0.5rem 1.25rem 0",
      }}>
        <span style={{
          display: "inline-block",
          fontSize: "0.68rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          background: accentColour + "22",
          color: accentColour,
          border: `1px solid ${accentColour}44`,
          padding: "0.2rem 0.6rem",
          borderRadius: "9999px",
        }}>
          {ROLE_DISPLAY[userRole] || "Portal"}
        </span>
      </div>

      {/* Nav */}
      <nav className="portal-sidebar-nav">
        <div className="portal-nav-section-title">Navigation</div>
        {navItems.map((item) => {
          const isActive = activeNav ? activeNav === item.id : false;
          return (
            <button
              key={item.id}
              type="button"
              className={`portal-nav-item ${isActive ? "active" : ""}`}
              onClick={(e) => handleItemClick(e, item)}
              title={item.label}
            >
              <span className="portal-nav-icon" aria-hidden="true">{item.icon || "•"}</span>
              <span className="portal-nav-label">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="portal-sidebar-footer">
        <span>
          <span className="portal-status-dot" aria-hidden="true" />
          Intranet Secure
        </span>
        <span>AY 2025–26</span>
      </div>
    </aside>
  );
}

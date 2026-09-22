import React from "react";
import { useNavigate } from "react-router-dom";
import { getUser, clearSession } from "../../auth/authStorage";

const ROLE_FORMAT_MAP = {
  student: "Student",
  course_faculty: "Course Faculty",
  class_teacher: "Class Teacher",
  health_admin: "Health Administrator",
  institute_admin: "Institute Administrator",
};

const ROLE_COLOUR = {
  student:        "#0ea5e9",
  course_faculty: "#8b5cf6",
  class_teacher:  "#f59e0b",
  health_admin:   "#ef4444",
  institute_admin:"#10b981",
};

export default function TopBar({ onLogout, user: propUser, portalTitle }) {
  const navigate = useNavigate();
  const user = propUser || getUser();
  const userName = user?.name || "Campus User";
  const userRole = user?.role || "user";
  const roleDisplay = ROLE_FORMAT_MAP[userRole] || userRole;
  const accentColour = ROLE_COLOUR[userRole] || "#2563eb";

  const initials = userName
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() || "U";

  function handleLogoutClick() {
    if (onLogout) {
      onLogout();
    } else {
      clearSession();
      navigate("/login");
    }
  }

  return (
    <header className="portal-topbar" aria-label="Top Navigation Bar">
      {/* Left: breadcrumb */}
      <div className="portal-topbar-left">
        <div className="portal-institution-badge">
          <span aria-hidden="true">🏛️</span>
          <span>CampusTrace</span>
          {portalTitle && (
            <>
              <span style={{ color: "#94a3b8", margin: "0 0.1rem" }}>/</span>
              <span style={{ color: "#334155", fontWeight: 700 }}>{portalTitle}</span>
            </>
          )}
        </div>
      </div>

      {/* Right: notifications + user */}
      <div className="portal-topbar-right">
        {/* Notification bell — placeholder, no wiring */}
        <button
          type="button"
          className="portal-notification-btn"
          title="Notifications"
          aria-label="Notifications"
          onClick={() => {/* placeholder */}}
        >
          🔔
        </button>

        {/* User profile block */}
        <div className="portal-user-profile">
          <div
            className="portal-user-avatar"
            aria-hidden="true"
            style={{ background: `linear-gradient(135deg, ${accentColour}cc, ${accentColour})` }}
          >
            {initials}
          </div>
          <div className="portal-user-info">
            <span className="portal-user-name">{userName}</span>
            <span className="portal-user-role">{roleDisplay}</span>
          </div>
        </div>

        {/* Sign out */}
        <button
          type="button"
          className="btn-logout"
          onClick={handleLogoutClick}
          title="Sign out of your session"
        >
          ↪ Sign Out
        </button>
      </div>
    </header>
  );
}

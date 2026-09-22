import React from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { getUser } from "../../auth/authStorage";
import "./layout.css";

export default function DashboardShell({
  title,
  subtitle,
  activeNav,
  onNavClick,
  customNavItems,
  onLogout,
  error,
  bannerMsg,
  headerActions,
  children,
}) {
  const user = getUser();

  return (
    <div className="portal-shell">
      <Sidebar
        customNavItems={customNavItems}
        activeNav={activeNav}
        onNavClick={onNavClick}
        user={user}
      />

      <div className="portal-main">
        <TopBar
          onLogout={onLogout}
          user={user}
          portalTitle={title}
        />

        <main className="portal-content">
          {/* Page header */}
          {(title || subtitle) && (
            <header className="portal-page-header">
              <div>
                {title && (
                  <h1>
                    {title}
                  </h1>
                )}
                <p className="welcome-text">
                  Welcome back, <strong>{user?.name || "User"}</strong>
                </p>
                {subtitle && (
                  <p className="subtitle">{subtitle}</p>
                )}
              </div>
              {headerActions && (
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  {headerActions}
                </div>
              )}
            </header>
          )}

          {/* Banners */}
          {error && (
            <div className="banner-error" role="alert">
              ⚠ {error}
            </div>
          )}
          {bannerMsg && (
            <div className="banner-success" role="status">
              ✓ {bannerMsg}
            </div>
          )}

          {children}
        </main>
      </div>
    </div>
  );
}

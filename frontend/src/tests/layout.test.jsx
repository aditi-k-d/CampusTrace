import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import Sidebar from "../components/layout/Sidebar";
import TopBar from "../components/layout/TopBar";
import ModuleCard from "../components/layout/ModuleCard";
import DashboardShell from "../components/layout/DashboardShell";
import * as authStorage from "../auth/authStorage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../auth/authStorage", () => ({
  getUser: vi.fn(),
  clearSession: vi.fn(),
  saveSession: vi.fn(),
  isAuthenticated: vi.fn(),
}));

describe("Layout Components", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("Sidebar", () => {
    it("renders app branding and role-aware navigation for student", () => {
      authStorage.getUser.mockReturnValue({
        name: "Alice Student",
        role: "student",
      });

      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      // App branding
      expect(screen.getByText("CampusTrace")).toBeInTheDocument();
      expect(screen.getByText("University Intranet")).toBeInTheDocument();

      // Student modules should be present
      expect(screen.getByText("Enrolled Courses")).toBeInTheDocument();
      expect(screen.getByText("Health Self-Report")).toBeInTheDocument();
      expect(screen.getByText("Exposure Alerts")).toBeInTheDocument();

      // Institute Admin or Faculty modules must NOT be present
      expect(screen.queryByText("Audit Log Viewer")).not.toBeInTheDocument();
      expect(screen.queryByText("Flag Student Absence")).not.toBeInTheDocument();
    });

    it("renders role-aware navigation for institute_admin", () => {
      authStorage.getUser.mockReturnValue({
        name: "Admin User",
        role: "institute_admin",
      });

      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );

      // Admin modules should be present
      expect(screen.getByText("Aggregated Analytics")).toBeInTheDocument();
      expect(screen.getByText("Structure & Timetables")).toBeInTheDocument();
      expect(screen.getByText("Audit Log Viewer")).toBeInTheDocument();

      // Student modules must NOT be present
      expect(screen.queryByText("Health Self-Report")).not.toBeInTheDocument();
    });

    it("triggers onNavClick callback when nav item is clicked", () => {
      authStorage.getUser.mockReturnValue({
        name: "Dr. Smith",
        role: "course_faculty",
      });
      const onNavClickMock = vi.fn();

      render(
        <MemoryRouter>
          <Sidebar onNavClick={onNavClickMock} />
        </MemoryRouter>
      );

      const item = screen.getByText("Attendance & Health");
      fireEvent.click(item);
      expect(onNavClickMock).toHaveBeenCalledWith("attendance");
    });
  });

  describe("TopBar", () => {
    it("displays user name, formatted role, and handles sign out", () => {
      authStorage.getUser.mockReturnValue({
        name: "Charles Xavier",
        role: "institute_admin",
      });

      render(
        <MemoryRouter>
          <TopBar portalTitle="Institute Admin Portal" />
        </MemoryRouter>
      );

      expect(screen.getByText("Charles Xavier")).toBeInTheDocument();
      expect(screen.getByText("Institute Administrator")).toBeInTheDocument();
      expect(screen.getByText("CX")).toBeInTheDocument(); // Initials avatar

      const logoutBtn = screen.getByRole("button", { name: /sign out/i });
      fireEvent.click(logoutBtn);

      expect(authStorage.clearSession).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });
  });

  describe("ModuleCard", () => {
    it("renders title, description, badge, action button, and children", () => {
      const onActionMock = vi.fn();

      render(
        <ModuleCard
          id="test-module"
          title="Clinical Surveillance"
          description="Real-time case monitoring across campus divisions"
          badge="Live"
          badgeType="success"
          actionText="Inspect Cases →"
          onAction={onActionMock}
        >
          <div data-testid="module-content">Embedded Content Table</div>
        </ModuleCard>
      );

      expect(screen.getByText("Clinical Surveillance")).toBeInTheDocument();
      expect(screen.getByText("Real-time case monitoring across campus divisions")).toBeInTheDocument();
      expect(screen.getByText("Live")).toBeInTheDocument();
      expect(screen.getByTestId("module-content")).toHaveTextContent("Embedded Content Table");

      const actionBtn = screen.getByRole("button", { name: /inspect cases/i });
      fireEvent.click(actionBtn);
      expect(onActionMock).toHaveBeenCalled();
    });

    it("handles interactive card clicks and keyboard interaction", () => {
      const onClickMock = vi.fn();

      render(
        <ModuleCard
          title="Overview Module"
          description="Interactive entry card"
          onClick={onClickMock}
          interactive
        />
      );

      const card = screen.getByRole("button");
      fireEvent.click(card);
      expect(onClickMock).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(card, { key: "Enter" });
      expect(onClickMock).toHaveBeenCalledTimes(2);
    });
  });

  describe("DashboardShell", () => {
    it("wraps layout with Sidebar, TopBar, and main content area", () => {
      authStorage.getUser.mockReturnValue({
        name: "Jane Student",
        role: "student",
      });

      render(
        <MemoryRouter>
          <DashboardShell
            title="Student Portal"
            subtitle="Academic and Health Services Intranet"
            error="Notice of scheduled maintenance"
          >
            <div data-testid="dashboard-children">Portal Content Inside Shell</div>
          </DashboardShell>
        </MemoryRouter>
      );

      // TopBar + Sidebar
      expect(screen.getByText("CampusTrace")).toBeInTheDocument();
      expect(screen.getByText("Jane Student")).toBeInTheDocument();

      // Page Header inside shell
      expect(screen.getByRole("heading", { level: 1, name: "Student Portal" })).toBeInTheDocument();
      expect(screen.getByText("Academic and Health Services Intranet")).toBeInTheDocument();
      expect(screen.getByText("Welcome back, Jane Student")).toBeInTheDocument();

      // Error banner
      expect(screen.getByText("Notice of scheduled maintenance")).toBeInTheDocument();

      // Main content
      expect(screen.getByTestId("dashboard-children")).toHaveTextContent("Portal Content Inside Shell");
    });
  });
});

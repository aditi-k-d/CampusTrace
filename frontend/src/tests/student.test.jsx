import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import SelfReportForm from "../components/student/SelfReportForm";
import AlertCard from "../components/student/AlertCard";
import BatchSelection from "../pages/BatchSelection";
import * as studentApi from "../api/studentApi";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../api/studentApi");
vi.mock("../auth/authStorage", () => ({
  getUser: () => ({ name: "Test Student", role: "student" }),
  clearSession: vi.fn(),
  saveSession: vi.fn(),
}));

describe("Student Components", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("SelfReportForm", () => {
    it("renders form fields correctly", () => {
      render(<SelfReportForm />);

      expect(screen.getByLabelText(/onset date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/severity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/symptoms/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /submit health report/i })).toBeInTheDocument();
    });

    it("submits health report when form is filled", async () => {
      const mockCallback = vi.fn();
      studentApi.reportHealth.mockResolvedValueOnce({ id: 10, status: "reported" });

      render(<SelfReportForm onReportSubmitted={mockCallback} />);

      const symptomsInput = screen.getByLabelText(/symptoms/i);
      fireEvent.change(symptomsInput, { target: { value: "Fever and cough" } });

      const submitButton = screen.getByRole("button", { name: /submit health report/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(studentApi.reportHealth).toHaveBeenCalledWith(
          expect.objectContaining({
            custom_symptoms: "Fever and cough",
            severity: "mild",
          })
        );
        expect(screen.getByText(/health report submitted successfully/i)).toBeInTheDocument();
        expect(mockCallback).toHaveBeenCalled();
      });
    });

    it("shows error message on submission failure", async () => {
      studentApi.reportHealth.mockRejectedValueOnce({
        response: { data: { error: "Failed to report health issue." } },
      });

      render(<SelfReportForm />);

      const symptomsInput = screen.getByLabelText(/symptoms/i);
      fireEvent.change(symptomsInput, { target: { value: "High fever" } });

      fireEvent.click(screen.getByRole("button", { name: /submit health report/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("Failed to report health issue.");
      });
    });
  });

  describe("AlertCard", () => {
    const dummyAlert = {
      id: 5,
      risk_level: "high",
      risk_score: 85.5,
      symptoms: "Fever, Fatigue",
      precautions: "Isolate for 5 days and monitor temperature.",
      created_at: "2026-09-14T10:00:00Z",
      acknowledged_at: null,
    };

    it("renders alert details correctly", () => {
      render(<AlertCard alert={dummyAlert} />);

      expect(screen.getByText(/risk level: high/i)).toBeInTheDocument();
      expect(screen.getByText(/score: 85.5/i)).toBeInTheDocument();
      expect(screen.getByText(/fever, fatigue/i)).toBeInTheDocument();
      expect(screen.getAllByText(/isolate for 5 days/i).length).toBeGreaterThanOrEqual(1);
    });

    it("handles acknowledge action", async () => {
      const mockCallback = vi.fn();
      studentApi.acknowledgeAlert.mockResolvedValueOnce({ id: 5, acknowledged_at: "2026-09-14T11:00:00Z" });

      render(<AlertCard alert={dummyAlert} onAlertUpdated={mockCallback} />);

      const ackBtn = screen.getByRole("button", { name: /acknowledge alert/i });
      fireEvent.click(ackBtn);

      await waitFor(() => {
        expect(studentApi.acknowledgeAlert).toHaveBeenCalledWith(5);
        expect(screen.getByText(/acknowledged/i)).toBeInTheDocument();
        expect(mockCallback).toHaveBeenCalled();
      });
    });

    it("handles false positive report action", async () => {
      const mockCallback = vi.fn();
      studentApi.reportFalsePositive.mockResolvedValueOnce({ id: 1, alert_id: 5, is_false_positive: true });

      render(<AlertCard alert={dummyAlert} onAlertUpdated={mockCallback} />);

      const fpBtn = screen.getByRole("button", { name: /report false positive/i });
      fireEvent.click(fpBtn);

      await waitFor(() => {
        expect(studentApi.reportFalsePositive).toHaveBeenCalledWith(5);
        expect(screen.getByText(/flagged as false positive/i)).toBeInTheDocument();
        expect(mockCallback).toHaveBeenCalled();
      });
    });

    it("renders symptoms, preventive measures, and recommended action without exposure source", () => {
      const detailedAlert = {
        id: 6,
        risk_level: "medium",
        risk_score: 45.0,
        symptoms: "Mild fever, cough",
        preventive_measures: "Wear mask, sanitize hands",
        recommended_action: "Self-monitor for 3 days",
        created_at: "2026-09-14T10:00:00Z",
      };

      const { container } = render(<AlertCard alert={detailedAlert} />);
      expect(screen.getByText(/risk level: medium/i)).toBeInTheDocument();
      expect(screen.getByText(/mild fever, cough/i)).toBeInTheDocument();
      expect(screen.getByText(/wear mask, sanitize hands/i)).toBeInTheDocument();
      expect(screen.getByText(/self-monitor for 3 days/i)).toBeInTheDocument();
      // Ensure exposure source is never rendered
      expect(container.textContent).not.toContain("exposed_by");
      expect(container.textContent).not.toContain("Exposed by");
    });
  });

  describe("BatchSelection", () => {
    it("renders lab/tutorial courses and submits selected batches", async () => {
      mockNavigate.mockClear();

      const mockCourses = [
        {
          course_id: 1,
          code: "CE201",
          name: "Theory Course",
          course_type: "theory",
          batches: [],
        },
        {
          course_id: 2,
          code: "CE202L",
          name: "Data Structures Lab",
          course_type: "lab",
          batch_id: null,
          batches: [
            { id: 101, name: "CE202L-B1" },
            { id: 102, name: "CE202L-B2" },
          ],
        },
        {
          course_id: 3,
          code: "CE203T",
          name: "Maths Tutorial",
          course_type: "tutorial",
          batch_id: null,
          batches: [
            { id: 201, name: "CE203T-B1" },
            { id: 202, name: "CE203T-B2" },
          ],
        },
      ];

      studentApi.getCourses.mockResolvedValueOnce(mockCourses);
      studentApi.registerBatches.mockResolvedValueOnce([{ id: 1, course_id: 2, batch_id: 101 }]);

      render(
        <MemoryRouter>
          <BatchSelection />
        </MemoryRouter>
      );

      // Wait for lab/tutorial course names to appear
      // Use exact:false because course name is a partial text node inside <strong>CE202L — Data Structures Lab</strong>
      await waitFor(() => {
        expect(screen.getByText(/Data Structures Lab/, { exact: false })).toBeInTheDocument();
        expect(screen.getByText(/Maths Tutorial/, { exact: false })).toBeInTheDocument();
      });

      // Theory course should not be rendered for batch selection
      expect(screen.queryByText(/Theory Course/, { exact: false })).not.toBeInTheDocument();

      const submitBtn = screen.getByRole("button", { name: /confirm batches & continue to dashboard/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(studentApi.registerBatches).toHaveBeenCalledWith([
          { course_id: 2, batch_id: 101 },
          { course_id: 3, batch_id: 201 },
        ]);
        expect(mockNavigate).toHaveBeenCalledWith("/student");
      });
    });
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import AbsenceFlagForm from "../components/faculty/AbsenceFlagForm";
import AttendanceView from "../components/faculty/AttendanceView";
import * as facultyApi from "../api/facultyApi";

vi.mock("../api/facultyApi");

describe("Faculty Components", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("AbsenceFlagForm", () => {
    it("renders form fields correctly", () => {
      render(<AbsenceFlagForm defaultCourseId="1" />);

      expect(screen.getByLabelText(/student id/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/course id/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/flagged date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/reason category/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /flag student/i })).toBeInTheDocument();
    });

    it("submits absence flag form successfully", async () => {
      const mockCallback = vi.fn();
      facultyApi.createAbsenceFlag.mockResolvedValueOnce({
        id: 1,
        student_id: 10,
        course_id: 1,
        flagged_date: "2026-09-14",
        reason_category: "health_observed",
        state: "pending",
      });

      render(<AbsenceFlagForm defaultCourseId="1" onFlagCreated={mockCallback} />);

      const studentIdInput = screen.getByLabelText(/student id/i);
      fireEvent.change(studentIdInput, { target: { value: "10" } });

      const submitButton = screen.getByRole("button", { name: /flag student/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(facultyApi.createAbsenceFlag).toHaveBeenCalledWith({
          student_id: 10,
          course_id: 1,
          flagged_date: expect.any(String),
          reason_category: "health_observed",
        });
        expect(screen.getByText(/absence flag created successfully/i)).toBeInTheDocument();
        expect(mockCallback).toHaveBeenCalled();
      });
    });

    it("displays error message on submission error", async () => {
      facultyApi.createAbsenceFlag.mockRejectedValueOnce({
        response: { data: { error: "Forbidden: You are not assigned to this course" } },
      });

      render(<AbsenceFlagForm defaultCourseId="2" />);

      fireEvent.change(screen.getByLabelText(/student id/i), { target: { value: "15" } });
      fireEvent.click(screen.getByRole("button", { name: /flag student/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("Forbidden: You are not assigned to this course");
      });
    });
  });

  describe("AttendanceView", () => {
    it("renders attendance and aggregate health summary without disclosing individual diagnoses", async () => {
      facultyApi.getAttendance.mockResolvedValueOnce({
        course_id: 1,
        date: "2026-09-14",
        total_present: 1,
        present_users: [
          { user_id: 10, user_name: "Alice Smith", room_name: "Lab 101", start_time: "09:00", end_time: "10:00" },
        ],
      });

      facultyApi.getHealthSummary.mockResolvedValueOnce({
        course_id: 1,
        total_students: 20,
        under_observation: 3,
        confirmed_cases: 1,
      });

      render(<AttendanceView courseId="1" />);

      await waitFor(() => {
        expect(screen.getByText(/total enrolled/i)).toBeInTheDocument();
        expect(screen.getByText("20")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
        expect(screen.getByText(/alice smith/i)).toBeInTheDocument();
        expect(screen.getByText(/aggregate health status/i)).toBeInTheDocument();
      });
    });
  });
});

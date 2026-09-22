import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import DiseaseKBEditor from "../components/admin/DiseaseKBEditor";
import CapacityView from "../components/admin/CapacityView";
import PriorityQueueView from "../components/admin/PriorityQueueView";
import AnalyticsSummaryPanel from "../components/admin/AnalyticsSummaryPanel";
import RiskBreakdownView from "../components/admin/RiskBreakdownView";
import NetworkGraphView from "../components/admin/NetworkGraphView";
import * as adminApi from "../api/adminApi";

vi.mock("../api/adminApi");

describe("Admin Components", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe("DiseaseKBEditor", () => {
    const mockKBList = [
      {
        id: 1,
        name: "Chickenpox",
        symptoms: "fever, rash, blisters",
        preventive_measures: "Isolate for 7 days",
        incubation_period_days: 14,
      },
    ];

    it("renders existing KB entries and form fields", async () => {
      adminApi.getDiseaseKB.mockResolvedValueOnce(mockKBList);

      render(<DiseaseKBEditor />);

      await waitFor(() => {
        expect(screen.getByText("Chickenpox")).toBeInTheDocument();
        expect(screen.getByText("fever, rash, blisters")).toBeInTheDocument();
      });

      expect(screen.getByLabelText(/disease name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/symptoms/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /add entry/i })).toBeInTheDocument();
    });

    it("submits a new Disease KB entry", async () => {
      adminApi.getDiseaseKB.mockResolvedValue(mockKBList);
      adminApi.createDiseaseKB.mockResolvedValueOnce({
        id: 2,
        name: "COVID-19",
        symptoms: "fever, loss of taste",
        preventive_measures: "Isolate",
        incubation_period_days: 5,
      });

      render(<DiseaseKBEditor />);

      await waitFor(() => {
        expect(screen.getByText("Chickenpox")).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText(/disease name/i), { target: { value: "COVID-19" } });
      fireEvent.change(screen.getByLabelText(/symptoms/i), { target: { value: "fever, loss of taste" } });
      fireEvent.change(screen.getByLabelText(/preventive measures/i), { target: { value: "Isolate" } });

      fireEvent.click(screen.getByRole("button", { name: /add entry/i }));

      await waitFor(() => {
        expect(adminApi.createDiseaseKB).toHaveBeenCalled();
        expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
      });
    });

    it("populates form when Edit button is clicked", async () => {
      adminApi.getDiseaseKB.mockResolvedValueOnce(mockKBList);

      render(<DiseaseKBEditor />);

      await waitFor(() => {
        expect(screen.getByText("Chickenpox")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /edit/i }));

      expect(screen.getByLabelText(/disease name/i)).toHaveValue("Chickenpox");
      expect(screen.getByRole("button", { name: /update entry/i })).toBeInTheDocument();
    });
  });

  describe("CapacityView", () => {
    const mockCapacity = [
      {
        id: 1,
        facility_name: "Isolation Ward A",
        building: "Health Block",
        total_beds: 20,
        occupied_beds: 5,
        available_beds: 15,
      },
    ];

    it("renders facility capacity stats", async () => {
      adminApi.getCapacity.mockResolvedValueOnce(mockCapacity);

      render(<CapacityView />);

      await waitFor(() => {
        expect(screen.getByText("Isolation Ward A")).toBeInTheDocument();
        expect(screen.getByText("Total Beds: 20")).toBeInTheDocument();
        expect(screen.getByText("Available: 15")).toBeInTheDocument();
      });
    });

    it("allocates bed successfully via priority queue", async () => {
      adminApi.getCapacity.mockResolvedValue(mockCapacity);
      adminApi.allocateBed.mockResolvedValueOnce({
        id: 1,
        capacity_id: 1,
        allocated_user_id: 102,
        allocated_bed_number: 6,
      });

      render(<CapacityView />);

      await waitFor(() => {
        expect(screen.getByText("Isolation Ward A")).toBeInTheDocument();
      });

      const allocateBtn = screen.getByRole("button", { name: /allocate bed/i });
      fireEvent.click(allocateBtn);

      await waitFor(() => {
        expect(adminApi.allocateBed).toHaveBeenCalledWith(1, null);
        expect(screen.getByText(/bed allocated successfully/i)).toBeInTheDocument();
      });
    });
  });

  describe("PriorityQueueView", () => {
    it("renders rows in the order returned and visually distinguishes rank #1", async () => {
      const mockQueue = [
        { rank: 1, user_id: 101, user_name: "Alice Student", priority_score: 95.5 },
        { rank: 2, user_id: 102, user_name: "Bob Contact", priority_score: 72.0 },
        { rank: 3, user_id: 103, user_name: "Charlie Case", priority_score: 41.2 },
      ];

      adminApi.getPriorityQueue.mockResolvedValueOnce({
        queue: mockQueue,
        total: 3,
      });

      render(<PriorityQueueView />);

      await waitFor(() => {
        expect(screen.getByText("Alice Student")).toBeInTheDocument();
        expect(screen.getByText("Bob Contact")).toBeInTheDocument();
        expect(screen.getByText("Charlie Case")).toBeInTheDocument();
      });

      // Confirm rows render in descending order as returned
      const rows = screen.getAllByRole("row").slice(1); // omit header row
      expect(rows).toHaveLength(3);
      expect(rows[0]).toHaveTextContent("Alice Student");
      expect(rows[0]).toHaveTextContent("95.5");
      expect(rows[1]).toHaveTextContent("Bob Contact");
      expect(rows[1]).toHaveTextContent("72.0");
      expect(rows[2]).toHaveTextContent("Charlie Case");
      expect(rows[2]).toHaveTextContent("41.2");

      // Confirm rank #1 is visually distinguished (by class name and test-id)
      expect(rows[0]).toHaveClass("rank-first");
      expect(rows[0]).toHaveAttribute("data-testid", "rank-1-row");
      expect(screen.getByTestId("rank-1-badge")).toHaveTextContent(/top priority/i);

      // Other rows should not have rank-first class
      expect(rows[1]).not.toHaveClass("rank-first");
      expect(rows[2]).not.toHaveClass("rank-first");

      // Placeholder button exists
      const allocateButtons = screen.getAllByRole("button", { name: /allocate bed/i });
      expect(allocateButtons).toHaveLength(3);
    });
  });

  describe("AnalyticsSummaryPanel", () => {
    it("renders all 4 metrics with their mocked values", async () => {
      const mockSummary = {
        total_cases: 42,
        avg_contacts_per_case: 8.5,
        secondary_contacts: 120,
        confirmed_cases: 15,
        pending_cases: 27,
      };

      adminApi.getAnalyticsSummary.mockResolvedValueOnce(mockSummary);

      render(<AnalyticsSummaryPanel />);

      await waitFor(() => {
        expect(screen.getByTestId("kpi-total-cases")).toHaveTextContent("42");
        expect(screen.getByTestId("kpi-avg-contacts")).toHaveTextContent("8.5");
        expect(screen.getByTestId("kpi-secondary-contacts")).toHaveTextContent("120");
        expect(screen.getByTestId("kpi-active-pending")).toHaveTextContent("15");
        expect(screen.getByTestId("kpi-active-pending")).toHaveTextContent("27");
      });

      expect(screen.getByText("Total Cases")).toBeInTheDocument();
      expect(screen.getByText("Average Contacts per Case")).toBeInTheDocument();
      expect(screen.getByText("Secondary (Depth 2+) Contacts")).toBeInTheDocument();
      expect(screen.getByText("Active vs. Pending Cases")).toBeInTheDocument();
    });
  });

  describe("RiskBreakdownView", () => {
    const mockBreakdown = {
      case_id: 7,
      source_user_id: 101,
      onset_date: "2025-09-01",
      total_contacts: 2,
      contacts: [
        {
          user_id: 201,
          depth: 1,
          contact_type: "direct",
          duration_minutes: 60,
          contact_date: "2025-08-30",
          days_since_contact: 2,
          hop_decay: 1.0,
          base_score: 72,
          risk_score: 72,
          risk_level: "high",
          room_type_weight: 1.2,
        },
        {
          user_id: 202,
          depth: 2,
          contact_type: "indirect",
          duration_minutes: 20,
          contact_date: "2025-08-29",
          days_since_contact: 3,
          hop_decay: 0.5,
          base_score: 30,
          risk_score: 15,
          risk_level: "low",
          room_type_weight: 0.8,
        },
      ],
    };

    it("renders one row per contact and labels depth-1 as Direct and depth-2 as Indirect", async () => {
      adminApi.getCaseAnalytics.mockResolvedValueOnce(mockBreakdown);
      render(<RiskBreakdownView caseId={7} />);

      await waitFor(() => {
        // Two data rows rendered
        const directCells = screen.getAllByText("Direct");
        const indirectCells = screen.getAllByText("Indirect");
        expect(directCells).toHaveLength(1);
        expect(indirectCells).toHaveLength(1);
      });
    });
  });

  describe("NetworkGraphView", () => {
    // In jsdom, HTMLCanvasElement.getContext("2d") returns null, so
    // NetworkGraphView's canRenderCanvas() returns false and the component
    // renders the FallbackTable instead of vis-network. We exercise that path.
    const mockGraphResponse = {
      case_id: 3,
      contacts: {
        forward: {
          202: { depth: 1, risk_score: 80, risk_level: "high" },
          303: { depth: 2, risk_score: 30, risk_level: "low" },
        },
      },
      graph: {
        nodes: [
          { id: 100, is_source: true,  depth: 0, risk_score: null, risk_level: "source" },
          { id: 202, is_source: false, depth: 1, risk_score: 80,   risk_level: "high"   },
          { id: 303, is_source: false, depth: 2, risk_score: 30,   risk_level: "low"    },
        ],
        edges: [
          { source: 100, target: 202, duration_minutes: 45, contact_date: "2025-08-30", weight: 1.2 },
          { source: 202, target: 303, duration_minutes: 20, contact_date: "2025-08-31", weight: 0.8 },
        ],
      },
    };

    it("renders the headless fallback without throwing and shows mocked nodes and edges", async () => {
      adminApi.getContactGraph.mockResolvedValueOnce(mockGraphResponse);

      render(<NetworkGraphView />);

      // Fill in case ID and submit the form to trigger the API call
      const input = screen.getByPlaceholderText("Case ID");
      fireEvent.change(input, { target: { value: "3" } });
      fireEvent.submit(input.closest("form"));

      // Wait for the fallback container to appear (canvas unavailable in jsdom)
      await waitFor(() => {
        expect(screen.getByTestId("network-graph-fallback")).toBeInTheDocument();
      });

      // All 3 mocked nodes should appear in the fallback table
      expect(screen.getByTestId("fallback-node-100")).toBeInTheDocument();
      expect(screen.getByTestId("fallback-node-202")).toBeInTheDocument();
      expect(screen.getByTestId("fallback-node-303")).toBeInTheDocument();

      // Both edges should be present (2 rows in the edges table body)
      const edgesTable = screen.getByTestId("fallback-edges-table");
      const edgeRows = edgesTable.querySelectorAll("tbody tr");
      expect(edgeRows).toHaveLength(2);
    });
  });
});

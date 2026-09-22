import React, { useState, useEffect } from "react";
import {
  getAggregateDashboards,
  getSystemConfig,
  updateSystemConfig,
  createDivision,
  createRoom,
  createCourse,
  createBatch,
  assignFaculty,
  createTimetableSlot,
  listUsers,
  updateUserStatus,
  registerRoleUser,
  getOutbreakTrends,
  getDepartmentStats,
  getHighOverlapLocations,
  getAnalytics,
  getEventExposures,
} from "../api/adminApi";
import { getUser, clearSession } from "../auth/authStorage";
import { useNavigate } from "react-router-dom";
import AuditLogViewer from "../components/admin/AuditLogViewer";
import DashboardShell from "../components/layout/DashboardShell";
import ModuleCard from "../components/layout/ModuleCard";
import "./admin.css";

export default function InstituteAdminDashboard() {
  const user = getUser();
  const navigate = useNavigate();

  // Active Tab: "analytics" | "structure" | "users" | "config" | "audit"
  const [activeTab, setActiveTab] = useState("analytics");

  // General Loading & Banner States
  const [loading, setLoading] = useState(true);
  const [formMsg, setFormMsg] = useState(null);
  const [error, setError] = useState(null);

  // Dashboards & Analytics States
  const [aggregates, setAggregates] = useState(null);
  const [outbreakTrends, setOutbreakTrends] = useState([]);
  const [departmentStats, setDepartmentStats] = useState([]);
  const [highOverlapLocations, setHighOverlapLocations] = useState([]);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [eventExposures, setEventExposures] = useState([]);

  // System Config State
  const [config, setConfig] = useState(null);
  const [kAnonInput, setKAnonInput] = useState(5);
  const [depthInput, setDepthInput] = useState(2);
  const [directionInput, setDirectionInput] = useState("both");

  // User Management State
  const [usersList, setUsersList] = useState([]);
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [newUser, setNewUser] = useState({
    name: "",
    email: "",
    password: "",
    role: "course_faculty",
    division_id: "",
  });

  // Structure Form States
  const [divForm, setDivForm] = useState({ name: "", branch: "CS", year: 1 });
  const [roomForm, setRoomForm] = useState({ name: "", building: "Main Block", capacity: 60 });
  const [courseForm, setCourseForm] = useState({ division_id: "", code: "", name: "", course_type: "theory" });
  const [batchForm, setBatchForm] = useState({ course_id: "", name: "" });
  const [facAssignForm, setFacAssignForm] = useState({ faculty_id: "", course_id: "" });
  const [slotForm, setSlotForm] = useState({
    course_id: "",
    room_id: "",
    batch_id: "",
    day_of_week: 0,
    start_time: "09:00",
    end_time: "10:00",
  });

  async function loadAllData() {
    setLoading(true);
    setError(null);
    try {
      const [agg, cfg, trends, depts, overlaps, analytics, events, users] = await Promise.all([
        getAggregateDashboards().catch(() => null),
        getSystemConfig().catch(() => null),
        getOutbreakTrends().catch(() => ({ trends: [] })),
        getDepartmentStats().catch(() => ({ departments: [] })),
        getHighOverlapLocations().catch(() => ({ locations: [] })),
        getAnalytics().catch(() => null),
        getEventExposures().catch(() => ({ events: [] })),
        listUsers({ role: userRoleFilter || undefined }).catch(() => ({ items: [] })),
      ]);

      if (agg) setAggregates(agg);
      if (cfg) {
        setConfig(cfg);
        setKAnonInput(cfg.k_anonymity_threshold);
        setDepthInput(cfg.default_tracing_depth);
        setDirectionInput(cfg.default_tracing_direction);
      }
      setOutbreakTrends(trends.trends || []);
      setDepartmentStats(depts.departments || []);
      setHighOverlapLocations(overlaps.locations || []);
      setAnalyticsData(analytics);
      setEventExposures(events.events || []);
      setUsersList(users.items || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load Institute Admin data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAllData();
  }, [userRoleFilter]);

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  // --- Handlers for System Config ---
  async function handleUpdateConfig(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      const updated = await updateSystemConfig({
        k_anonymity_threshold: Number(kAnonInput),
        default_tracing_depth: Number(depthInput),
        default_tracing_direction: directionInput,
      });
      setConfig(updated);
      setFormMsg("System configuration updated successfully.");
      loadAllData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update system config.");
    }
  }

  // --- Handlers for Structure Setup ---
  async function handleCreateDivision(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await createDivision({
        name: divForm.name,
        branch: divForm.branch,
        year: Number(divForm.year),
      });
      setFormMsg(`Division '${divForm.name}' created successfully.`);
      setDivForm({ name: "", branch: "CS", year: 1 });
      loadAllData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create division.");
    }
  }

  async function handleCreateRoom(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await createRoom({
        name: roomForm.name,
        building: roomForm.building,
        capacity: Number(roomForm.capacity),
      });
      setFormMsg(`Room '${roomForm.name}' (Capacity: ${roomForm.capacity}) created successfully.`);
      setRoomForm({ name: "", building: "Main Block", capacity: 60 });
      loadAllData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create room.");
    }
  }

  async function handleCreateCourse(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await createCourse({
        division_id: Number(courseForm.division_id),
        code: courseForm.code,
        name: courseForm.name,
        course_type: courseForm.course_type,
      });
      setFormMsg(`Course '${courseForm.code} - ${courseForm.name}' created successfully.`);
      setCourseForm({ division_id: "", code: "", name: "", course_type: "theory" });
      loadAllData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create course.");
    }
  }

  async function handleCreateBatch(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await createBatch({
        course_id: Number(batchForm.course_id),
        name: batchForm.name,
      });
      setFormMsg(`Batch '${batchForm.name}' created successfully.`);
      setBatchForm({ course_id: "", name: "" });
      loadAllData();
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create batch.");
    }
  }

  async function handleAssignFaculty(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await assignFaculty({
        faculty_id: Number(facAssignForm.faculty_id),
        course_id: Number(facAssignForm.course_id),
      });
      setFormMsg("Faculty assigned to course successfully.");
      setFacAssignForm({ faculty_id: "", course_id: "" });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to assign faculty.");
    }
  }

  async function handleCreateTimetableSlot(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      await createTimetableSlot({
        course_id: Number(slotForm.course_id),
        room_id: Number(slotForm.room_id),
        batch_id: slotForm.batch_id ? Number(slotForm.batch_id) : null,
        day_of_week: Number(slotForm.day_of_week),
        start_time: slotForm.start_time,
        end_time: slotForm.end_time,
      });
      setFormMsg("Timetable slot created successfully.");
      setSlotForm({
        course_id: "",
        room_id: "",
        batch_id: "",
        day_of_week: 0,
        start_time: "09:00",
        end_time: "10:00",
      });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create timetable slot.");
    }
  }

  // --- Handlers for User Management ---
  async function handleRegisterUser(e) {
    e.preventDefault();
    setFormMsg(null);
    setError(null);
    try {
      const payload = {
        name: newUser.name,
        email: newUser.email,
        password: newUser.password,
        role: newUser.role,
        ...(newUser.division_id ? { division_id: Number(newUser.division_id) } : {}),
      };
      await registerRoleUser(payload);
      setFormMsg(`User '${newUser.name}' (${newUser.role}) registered successfully.`);
      setNewUser({ name: "", email: "", password: "", role: "course_faculty", division_id: "" });
      const updatedUsers = await listUsers({ role: userRoleFilter || undefined });
      setUsersList(updatedUsers.items || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to register user.");
    }
  }

  async function handleToggleUserStatus(userId, currentActive) {
    setFormMsg(null);
    setError(null);
    try {
      await updateUserStatus(userId, !currentActive);
      setFormMsg(`User ID ${userId} status updated to ${!currentActive ? "Active" : "Inactive"}.`);
      const updatedUsers = await listUsers({ role: userRoleFilter || undefined });
      setUsersList(updatedUsers.items || []);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update user status.");
    }
  }

  const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  const sidebarNavItems = [
    { id: "analytics", label: "Aggregated Analytics", icon: "📊", onClick: () => setActiveTab("analytics") },
    { id: "structure", label: "Structure & Timetables", icon: "🏛️", onClick: () => setActiveTab("structure") },
    { id: "users", label: "User Role Management", icon: "👤", onClick: () => setActiveTab("users") },
    { id: "config", label: "System Configuration", icon: "⚙️", onClick: () => setActiveTab("config") },
    { id: "audit", label: "Audit Log Viewer", icon: "📜", onClick: () => setActiveTab("audit") },
  ];

  const tabModules = [
    {
      id: "analytics",
      title: "Aggregated Analytics & Trends",
      description: "K-anonymized division and course counts, outbreak trends, and high-overlap locations",
      badge: "K-Anonymized",
    },
    {
      id: "structure",
      title: "Structure & Timetable Setup",
      description: "Divisions, rooms with capacities, courses, batches, and timetable slots",
      badge: "Architecture",
    },
    {
      id: "users",
      title: "User Role Management",
      description: "Register faculty & health staff; manage user account active status",
      badge: "RBAC",
    },
    {
      id: "config",
      title: "System Configuration",
      description: "Adjust k-anonymity threshold, default tracing depth and direction",
      badge: "Config",
    },
    {
      id: "audit",
      title: "Audit Log Viewer",
      description: "Immutable institutional activity log with action filtering and cursor pagination",
      badge: "Audit Trail",
    },
  ];

  return (
    <DashboardShell
      title="Institute Admin Portal"
      subtitle="Central Academic Architecture, User Roles & Institutional Configuration"
      error={error}
      bannerMsg={formMsg}
      customNavItems={sidebarNavItems}
      activeNav={activeTab}
      onNavClick={(tabId) => setActiveTab(tabId)}
      onLogout={handleLogout}
    >
      <div className="admin-dashboard-page" style={{ padding: 0, minHeight: "auto", background: "transparent" }}>
        {/* Card-based Module Entry Points */}
        <div className="module-entry-grid">
          {tabModules.map((m) => (
            <ModuleCard
              key={m.id}
              title={m.title}
              description={m.description}
              badge={m.badge}
              badgeType={activeTab === m.id ? "primary" : "secondary"}
              interactive
              actionText={activeTab === m.id ? "Active Module ✓" : "Open Module →"}
              onClick={() => setActiveTab(m.id)}
              style={activeTab === m.id ? { borderColor: "#2563eb", background: "#f8fafc" } : {}}
            />
          ))}
        </div>

        <div className="tab-navigation" style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", borderBottom: "2px solid #e5e7eb", paddingBottom: "0.5rem" }}>
          <button
            style={{ padding: "0.5rem 1rem", border: "none", borderRadius: "4px", cursor: "pointer", background: activeTab === "analytics" ? "#2563eb" : "#f3f4f6", color: activeTab === "analytics" ? "#fff" : "#374151", fontWeight: "bold" }}
            onClick={() => setActiveTab("analytics")}
          >
            Aggregated Analytics & Trends
          </button>
          <button
            style={{ padding: "0.5rem 1rem", border: "none", borderRadius: "4px", cursor: "pointer", background: activeTab === "structure" ? "#2563eb" : "#f3f4f6", color: activeTab === "structure" ? "#fff" : "#374151", fontWeight: "bold" }}
            onClick={() => setActiveTab("structure")}
          >
            Structure & Timetable Setup
          </button>
          <button
            style={{ padding: "0.5rem 1rem", border: "none", borderRadius: "4px", cursor: "pointer", background: activeTab === "users" ? "#2563eb" : "#f3f4f6", color: activeTab === "users" ? "#fff" : "#374151", fontWeight: "bold" }}
            onClick={() => setActiveTab("users")}
          >
            User Role Management
          </button>
          <button
            style={{ padding: "0.5rem 1rem", border: "none", borderRadius: "4px", cursor: "pointer", background: activeTab === "config" ? "#2563eb" : "#f3f4f6", color: activeTab === "config" ? "#fff" : "#374151", fontWeight: "bold" }}
            onClick={() => setActiveTab("config")}
          >
            System Config
          </button>
          <button
            style={{ padding: "0.5rem 1rem", border: "none", borderRadius: "4px", cursor: "pointer", background: activeTab === "audit" ? "#2563eb" : "#f3f4f6", color: activeTab === "audit" ? "#fff" : "#374151", fontWeight: "bold" }}
            onClick={() => setActiveTab("audit")}
          >
            Audit Log
          </button>
        </div>

      <main>
        {/* --- TAB 1: ANALYTICS & TRENDS --- */}
        {activeTab === "analytics" && (
          <div className="tab-pane">
            <div className="card" style={{ marginBottom: "1.5rem" }}>
              <h2>K-Anonymized Aggregated Overview</h2>
              <p className="subtitle">
                Counts below the K-Anonymity threshold (K = {config?.k_anonymity_threshold || 5}) are suppressed.
              </p>
              {loading ? (
                <p>Loading metrics...</p>
              ) : aggregates ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                  <div>
                    <h3>Divisions Breakdown</h3>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Division</th>
                          <th>Branch</th>
                          <th>Students</th>
                          <th>Active Cases</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aggregates.divisions?.map((d) => (
                          <tr key={d.division_id}>
                            <td><strong>{d.name}</strong></td>
                            <td>{d.branch}</td>
                            <td>{d.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold} (Suppressed)</em> : d.student_count}</td>
                            <td>{d.active_cases_suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold} (Suppressed)</em> : d.active_cases}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div>
                    <h3>Courses Breakdown</h3>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Code</th>
                          <th>Name</th>
                          <th>Enrollments</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aggregates.courses?.map((c) => (
                          <tr key={c.course_id}>
                            <td><strong>{c.code}</strong></td>
                            <td>{c.name}</td>
                            <td>{c.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold} (Suppressed)</em> : c.enrollment_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
              <div className="card">
                <h3>Institution-wide Outbreak Trends</h3>
                {outbreakTrends.length === 0 ? (
                  <p className="text-muted">No trend data logged yet.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Cases Reported</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outbreakTrends.map((t, idx) => (
                        <tr key={idx}>
                          <td>{t.date}</td>
                          <td>{t.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold} (Suppressed)</em> : t.case_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="card">
                <h3>Department-wise Statistics</h3>
                {departmentStats.length === 0 ? (
                  <p className="text-muted">No department data available.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Branch</th>
                        <th>Cases</th>
                        <th>Alerts</th>
                      </tr>
                    </thead>
                    <tbody>
                      {departmentStats.map((d, idx) => (
                        <tr key={idx}>
                          <td><strong>{d.branch}</strong></td>
                          <td>{d.case_suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold}</em> : d.case_count}</td>
                          <td>{d.alert_suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold}</em> : d.alert_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>
              <div className="card">
                <h3>High-Overlap Locations</h3>
                {highOverlapLocations.length === 0 ? (
                  <p className="text-muted">No location data available.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Room</th>
                        <th>Building</th>
                        <th>Distinct Users</th>
                        <th>Distinct Courses</th>
                      </tr>
                    </thead>
                    <tbody>
                      {highOverlapLocations.map((loc) => (
                        <tr key={loc.room_id}>
                          <td><strong>{loc.room_name}</strong></td>
                          <td>{loc.building}</td>
                          <td>{loc.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold}</em> : loc.distinct_users}</td>
                          <td>{loc.distinct_courses ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="card">
                <h3>Exposure Analytics by Location</h3>
                {analyticsData?.exposure_by_location?.length === 0 ? (
                  <p className="text-muted">No exposure location data.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Location / Room</th>
                        <th>Exposures Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analyticsData?.exposure_by_location?.map((e, idx) => (
                        <tr key={idx}>
                          <td><strong>{e.room_name}</strong></td>
                          <td>{e.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold}</em> : e.exposure_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="card">
              <h3>Event-Wise Exposure Counts</h3>
              {eventExposures.length === 0 ? (
                <p className="text-muted">No event exposure sessions recorded.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Course</th>
                      <th>Room</th>
                      <th>Date</th>
                      <th>Attendee / Exposure Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eventExposures.map((ev, idx) => (
                      <tr key={idx}>
                        <td><strong>{ev.course}</strong></td>
                        <td>{ev.room}</td>
                        <td>{ev.date}</td>
                        <td>{ev.suppressed ? <em className="text-muted">&lt; {config?.k_anonymity_threshold}</em> : ev.exposure_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* --- TAB 2: STRUCTURE & TIMETABLE SETUP --- */}
        {activeTab === "structure" && (
          <div className="tab-pane" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div className="card">
              <h2>Division & Room Setup</h2>
              <form onSubmit={handleCreateDivision} className="sub-form" style={{ marginBottom: "1.5rem" }}>
                <h3>Create Division</h3>
                <div className="form-group">
                  <label>Division Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Second Year CS-C"
                    value={divForm.name}
                    onChange={(e) => setDivForm({ ...divForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Branch</label>
                  <input
                    type="text"
                    placeholder="e.g. Computer Science"
                    value={divForm.branch}
                    onChange={(e) => setDivForm({ ...divForm, branch: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Year</label>
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={divForm.year}
                    onChange={(e) => setDivForm({ ...divForm, year: e.target.value })}
                    required
                  />
                </div>
                <button type="submit">Add Division</button>
              </form>

              <form onSubmit={handleCreateRoom} className="sub-form">
                <h3>Create Room (with Capacity)</h3>
                <div className="form-group">
                  <label>Room Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Lab 204"
                    value={roomForm.name}
                    onChange={(e) => setRoomForm({ ...roomForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Building</label>
                  <input
                    type="text"
                    placeholder="e.g. Main Academic Block"
                    value={roomForm.building}
                    onChange={(e) => setRoomForm({ ...roomForm, building: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Seating Capacity</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="e.g. 60"
                    value={roomForm.capacity}
                    onChange={(e) => setRoomForm({ ...roomForm, capacity: e.target.value })}
                    required
                  />
                </div>
                <button type="submit">Add Room</button>
              </form>
            </div>

            <div className="card">
              <h2>Courses, Batches & Faculty Setup</h2>
              <form onSubmit={handleCreateCourse} className="sub-form" style={{ marginBottom: "1.5rem" }}>
                <h3>Create Course</h3>
                <div className="form-group">
                  <label>Division ID</label>
                  <select
                    value={courseForm.division_id}
                    onChange={(e) => setCourseForm({ ...courseForm, division_id: e.target.value })}
                    required
                  >
                    <option value="">Select Division...</option>
                    {aggregates?.divisions?.map((d) => (
                      <option key={d.division_id} value={d.division_id}>
                        {d.name} ({d.branch})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Course Code</label>
                  <input
                    type="text"
                    placeholder="e.g. CS201"
                    value={courseForm.code}
                    onChange={(e) => setCourseForm({ ...courseForm, code: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Course Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Data Structures"
                    value={courseForm.name}
                    onChange={(e) => setCourseForm({ ...courseForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Course Type</label>
                  <select
                    value={courseForm.course_type}
                    onChange={(e) => setCourseForm({ ...courseForm, course_type: e.target.value })}
                  >
                    <option value="theory">Theory</option>
                    <option value="lab">Lab</option>
                    <option value="tutorial">Tutorial</option>
                  </select>
                </div>
                <button type="submit">Add Course</button>
              </form>

              <form onSubmit={handleCreateBatch} className="sub-form" style={{ marginBottom: "1.5rem" }}>
                <h3>Create Batch (for Lab/Tutorial)</h3>
                <div className="form-group">
                  <label>Course</label>
                  <select
                    value={batchForm.course_id}
                    onChange={(e) => setBatchForm({ ...batchForm, course_id: e.target.value })}
                    required
                  >
                    <option value="">Select Course...</option>
                    {aggregates?.courses?.map((c) => (
                      <option key={c.course_id} value={c.course_id}>
                        {c.code} - {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Batch Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Batch B1"
                    value={batchForm.name}
                    onChange={(e) => setBatchForm({ ...batchForm, name: e.target.value })}
                    required
                  />
                </div>
                <button type="submit">Add Batch</button>
              </form>

              <form onSubmit={handleAssignFaculty} className="sub-form">
                <h3>Assign Faculty to Course</h3>
                <div className="form-group">
                  <label>Faculty User ID</label>
                  <input
                    type="number"
                    placeholder="e.g. 5"
                    value={facAssignForm.faculty_id}
                    onChange={(e) => setFacAssignForm({ ...facAssignForm, faculty_id: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Course</label>
                  <select
                    value={facAssignForm.course_id}
                    onChange={(e) => setFacAssignForm({ ...facAssignForm, course_id: e.target.value })}
                    required
                  >
                    <option value="">Select Course...</option>
                    {aggregates?.courses?.map((c) => (
                      <option key={c.course_id} value={c.course_id}>
                        {c.code} - {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button type="submit">Assign Faculty</button>
              </form>

              <form onSubmit={handleCreateTimetableSlot} className="sub-form" style={{ marginTop: "1.5rem" }}>
                <h3>Create Timetable Slot</h3>
                <div className="form-group">
                  <label>Course ID</label>
                  <select
                    value={slotForm.course_id}
                    onChange={(e) => setSlotForm({ ...slotForm, course_id: e.target.value })}
                    required
                  >
                    <option value="">Select Course...</option>
                    {aggregates?.courses?.map((c) => (
                      <option key={c.course_id} value={c.course_id}>
                        {c.code} - {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Room ID</label>
                  <input
                    type="number"
                    placeholder="e.g. Room ID"
                    value={slotForm.room_id}
                    onChange={(e) => setSlotForm({ ...slotForm, room_id: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Batch ID (Optional)</label>
                  <input
                    type="number"
                    placeholder="e.g. Batch ID for lab"
                    value={slotForm.batch_id}
                    onChange={(e) => setSlotForm({ ...slotForm, batch_id: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Day of Week</label>
                  <select
                    value={slotForm.day_of_week}
                    onChange={(e) => setSlotForm({ ...slotForm, day_of_week: e.target.value })}
                  >
                    {DAY_NAMES.map((name, idx) => (
                      <option key={idx} value={idx}>{name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                  <div>
                    <label>Start Time</label>
                    <input
                      type="time"
                      value={slotForm.start_time}
                      onChange={(e) => setSlotForm({ ...slotForm, start_time: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label>End Time</label>
                    <input
                      type="time"
                      value={slotForm.end_time}
                      onChange={(e) => setSlotForm({ ...slotForm, end_time: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <button type="submit">Create Slot</button>
              </form>
            </div>
          </div>
        )}

        {/* --- TAB 3: USER MANAGEMENT --- */}
        {activeTab === "users" && (
          <div className="tab-pane" style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1.5rem" }}>
            <div className="card">
              <h2>User Accounts List</h2>
              <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", alignItems: "center" }}>
                <label>Filter by Role:</label>
                <select
                  value={userRoleFilter}
                  onChange={(e) => setUserRoleFilter(e.target.value)}
                >
                  <option value="">All Roles</option>
                  <option value="student">Student</option>
                  <option value="course_faculty">Course Faculty</option>
                  <option value="class_teacher">Class Teacher</option>
                  <option value="health_admin">Health Admin</option>
                  <option value="institute_admin">Institute Admin</option>
                </select>
              </div>

              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Division</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {usersList.map((u) => (
                    <tr key={u.id}>
                      <td>{u.id}</td>
                      <td><strong>{u.name}</strong></td>
                      <td>{u.email}</td>
                      <td><span className="badge">{u.role}</span></td>
                      <td>{u.division_id || "N/A"}</td>
                      <td>{u.is_active ? <span style={{ color: "#166534", fontWeight: "bold" }}>Active</span> : <span style={{ color: "#991b1b", fontWeight: "bold" }}>Inactive</span>}</td>
                      <td>
                        <button
                          style={{
                            padding: "0.25rem 0.5rem",
                            fontSize: "0.85rem",
                            background: u.is_active ? "#ef4444" : "#22c55e",
                            color: "#fff",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                          }}
                          onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card">
              <h2>Register Staff / Admin User</h2>
              <form onSubmit={handleRegisterUser}>
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={newUser.name}
                    onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>System Role</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  >
                    <option value="course_faculty">Course Faculty</option>
                    <option value="class_teacher">Class Teacher</option>
                    <option value="health_admin">Health Admin</option>
                    <option value="institute_admin">Institute Admin</option>
                  </select>
                </div>
                {newUser.role === "class_teacher" && (
                  <div className="form-group">
                    <label>Division ID</label>
                    <input
                      type="number"
                      value={newUser.division_id}
                      onChange={(e) => setNewUser({ ...newUser, division_id: e.target.value })}
                    />
                  </div>
                )}
                <button type="submit">Register Role User</button>
              </form>
            </div>
          </div>
        )}

        {/* --- TAB 4: SYSTEM CONFIG --- */}
        {activeTab === "config" && (
          <div className="tab-pane card" style={{ maxWidth: "600px" }}>
            <h2>System-Wide Configuration</h2>
            <form onSubmit={handleUpdateConfig}>
              <div className="form-group">
                <label htmlFor="k-anon-thresh">K-Anonymity Threshold</label>
                <input
                  id="k-anon-thresh"
                  type="number"
                  min="1"
                  value={kAnonInput}
                  onChange={(e) => setKAnonInput(e.target.value)}
                  required
                />
                <small className="text-muted">Minimum number of cases/users before aggregate counts are displayed.</small>
              </div>

              <div className="form-group" style={{ marginTop: "1rem" }}>
                <label htmlFor="def-depth">Default Tracing Depth</label>
                <input
                  id="def-depth"
                  type="number"
                  min="1"
                  value={depthInput}
                  onChange={(e) => setDepthInput(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ marginTop: "1rem" }}>
                <label htmlFor="def-dir">Default Tracing Direction</label>
                <select
                  id="def-dir"
                  value={directionInput}
                  onChange={(e) => setDirectionInput(e.target.value)}
                >
                  <option value="both">Both (Forward + Backward)</option>
                  <option value="forward">Forward</option>
                  <option value="backward">Backward</option>
                </select>
              </div>

              <button type="submit" style={{ marginTop: "1.5rem" }}>Update Config</button>
            </form>
          </div>
        )}

        {/* --- TAB 5: AUDIT LOG --- */}
        {activeTab === "audit" && (
          <div className="tab-pane card">
            <h2>Audit Log History</h2>
            <AuditLogViewer />
          </div>
        )}
      </main>
    </div>
  </DashboardShell>
  );
}

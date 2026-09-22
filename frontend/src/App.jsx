import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Login from "./auth/Login";
import Register from "./auth/Register";
import ProtectedRoute from "./auth/ProtectedRoute";

// --- Person 2/3/4: import your dashboard pages here as they're built.
// Additive-only, per Tasks.md merge strategy — add your own import
// line, never restructure this file. ---
import StudentDashboard from "./pages/StudentDashboard";
import BatchSelection from "./pages/BatchSelection";
import FacultyDashboard from "./pages/FacultyDashboard";
import ClassTeacherDashboard from "./pages/ClassTeacherDashboard";
import HealthAdminDashboard from "./pages/HealthAdminDashboard";
import InstituteAdminDashboard from "./pages/InstituteAdminDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* --- Person 2: student routes --- */}
        <Route element={<ProtectedRoute allowedRoles={["student"]} />}>
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/batch-selection" element={<BatchSelection />} />
        </Route>

        {/* --- Person 3: course faculty + class teacher routes --- */}
        <Route element={<ProtectedRoute allowedRoles={["course_faculty"]} />}>
          <Route path="/faculty" element={<FacultyDashboard />} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={["class_teacher"]} />}>
          <Route path="/class-teacher" element={<ClassTeacherDashboard />} />
        </Route>

        {/* --- Person 4: health admin + institute admin routes --- */}
        <Route element={<ProtectedRoute allowedRoles={["health_admin"]} />}>
          <Route path="/health-admin" element={<HealthAdminDashboard />} />
        </Route>
        <Route element={<ProtectedRoute allowedRoles={["institute_admin"]} />}>
          <Route path="/institute-admin" element={<InstituteAdminDashboard />} />
        </Route>

        <Route
          path="/unauthorized"
          element={
            <div className="auth-page">
              <p>You don&apos;t have access to this page.</p>
            </div>
          }
        />

        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { isAuthenticated, getUser } from "./authStorage";

/**
 * Usage in App.jsx:
 *   <Route element={<ProtectedRoute allowedRoles={["student"]} />}>
 *     <Route path="/student" element={<StudentDashboard />} />
 *   </Route>
 *
 * Omit allowedRoles to just require "logged in, any role".
 */
export default function ProtectedRoute({ allowedRoles }) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const user = getUser();
    if (!user || !allowedRoles.includes(user.role)) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <Outlet />;
}

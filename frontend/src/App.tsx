import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Navigation from "./components/Navigation";
import Leaderboard from "./pages/Leaderboard";
import Profile from "./pages/Profile";
import Visits from "./pages/Visits";
import VisitDetail from "./pages/VisitDetail";
import AdminVisits from "./pages/admin/AdminVisits";
import AdminBaths from "./pages/admin/AdminBaths";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminSettings from "./pages/admin/AdminSettings";

export default function App() {
  const { user, loading, error } = useAuth();

  if (loading) {
    return <div className="loading">⏳ Загрузка...</div>;
  }

  if (error) {
    return <div className="error">❌ {error}</div>;
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/leaderboard" replace />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/profile" element={<Profile user={user!} />} />
        <Route path="/visits" element={<Visits />} />
        <Route path="/visits/:id" element={<VisitDetail />} />

        {user?.is_admin && (
          <>
            <Route path="/admin/visits" element={<AdminVisits />} />
            <Route path="/admin/baths" element={<AdminBaths />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/settings" element={<AdminSettings />} />
          </>
        )}

        <Route path="*" element={<Navigate to="/leaderboard" replace />} />
      </Routes>
      <Navigation isAdmin={user?.is_admin ?? false} />
    </>
  );
}

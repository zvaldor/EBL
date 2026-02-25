import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import type { Visit, User } from "../types";
import VisitCard from "../components/VisitCard";

const AVATAR_COLORS = [
  "#e53935", "#8e24aa", "#1e88e5", "#00897b",
  "#43a047", "#fb8c00", "#6d4c41", "#546e7a",
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [profile, setProfile] = useState<User | null>(null);
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<User>(`/users/${id}`),
      api.get<Visit[]>(`/visits?user_id=${id}&limit=50`),
    ]).then(([u, v]) => {
      setProfile(u.data);
      setVisits(v.data);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">⏳ Загрузка...</div>;
  if (!profile) return <div className="error">Пользователь не найден</div>;

  const color = getAvatarColor(profile.full_name);

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", gap: 12 }}>
        <button onClick={() => navigate(-1)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}>
          ←
        </button>
        <div className="page-header" style={{ padding: 0 }}>Профиль</div>
      </div>

      {/* Profile card */}
      <div className="card" style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div
          style={{
            width: 60, height: 60, borderRadius: "50%",
            background: color, display: "flex", alignItems: "center",
            justifyContent: "center", color: "#fff", fontSize: 22, fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {initials(profile.full_name)}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{profile.full_name}</div>
          {profile.username && (
            <div style={{ fontSize: 13, color: "var(--tg-theme-hint-color)" }}>
              @{profile.username}
            </div>
          )}
          <div style={{ marginTop: 8, display: "flex", gap: 16 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--tg-theme-button-color)" }}>
                {profile.points.toFixed(0)}
              </div>
              <div style={{ fontSize: 11, color: "var(--tg-theme-hint-color)" }}>очков</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{profile.visit_count}</div>
              <div style={{ fontSize: 11, color: "var(--tg-theme-hint-color)" }}>визитов</div>
            </div>
          </div>
        </div>
      </div>

      {/* Visits */}
      <div style={{ padding: "12px 16px 4px", fontWeight: 600, fontSize: 15 }}>
        🏊 Визиты
      </div>
      {visits.length === 0 ? (
        <div className="loading">Нет визитов</div>
      ) : (
        visits.map((v) => <VisitCard key={v.id} visit={v} />)
      )}
    </div>
  );
}

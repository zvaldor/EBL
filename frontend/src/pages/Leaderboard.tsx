import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import type { LeaderboardEntry, Period } from "../types";

const PERIODS: { value: Period; label: string }[] = [
  { value: "year", label: "Год" },
  { value: "month", label: "Месяц" },
  { value: "week", label: "Неделя" },
  { value: "all", label: "Всё время" },
];

const MEDALS = ["🥇", "🥈", "🥉"];

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

export default function Leaderboard() {
  const [period, setPeriod] = useState<Period>("year");
  const [rows, setRows] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api
      .get<LeaderboardEntry[]>(`/leaderboard?period=${period}`)
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      <div className="page-header">🏆 Лидерборд</div>

      <div className="tabs" style={{ marginBottom: 12 }}>
        {PERIODS.map((p) => (
          <button
            key={p.value}
            className={`tab ${period === p.value ? "active" : ""}`}
            onClick={() => setPeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : rows.length === 0 ? (
        <div className="loading">Пока нет данных</div>
      ) : (
        rows.map((row) => (
          <div
            key={row.user_id}
            className="lb-row"
            style={{ cursor: "pointer" }}
            onClick={() => navigate(`/users/${row.user_id}`)}
          >
            <div className="lb-rank">
              {row.rank <= 3 ? MEDALS[row.rank - 1] : row.rank}
            </div>
            <div
              className="lb-avatar"
              style={{ background: getAvatarColor(row.full_name) }}
            >
              {initials(row.full_name)}
            </div>
            <div style={{ flex: 1 }}>
              <div className="lb-name">{row.full_name}</div>
              {row.username && (
                <div className="lb-username">@{row.username}</div>
              )}
              <div className="lb-meta">
                🏊 {row.visit_count} визитов · 🏠 {row.bath_count} бань
              </div>
            </div>
            <div>
              <div className="lb-points">{row.points.toFixed(0)}</div>
              <div className="lb-meta" style={{ textAlign: "right" }}>очков</div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

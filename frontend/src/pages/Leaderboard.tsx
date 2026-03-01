import { useState, useEffect } from "react";
import api from "../api/client";

interface LeaderboardRow {
  rank: number;
  name: string;
  points: number;
  visit_count: number;
}

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
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<LeaderboardRow[]>("/leaderboard")
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">🏆 Рейтинг</div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : rows.length === 0 ? (
        <div className="loading">Пока нет данных</div>
      ) : (
        rows.map((row) => (
          <div key={row.name} className="lb-row">
            <div className="lb-rank">
              {row.rank <= 3 ? MEDALS[row.rank - 1] : row.rank}
            </div>
            <div
              className="lb-avatar"
              style={{ background: getAvatarColor(row.name) }}
            >
              {initials(row.name)}
            </div>
            <div style={{ flex: 1 }}>
              <div className="lb-name">{row.name}</div>
              <div className="lb-meta">
                🛁 {row.visit_count} визитов
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

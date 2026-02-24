import { useState, useEffect } from "react";
import api from "../api/client";
import type { LeaderboardEntry, Period } from "../types";

const PERIODS: { value: Period; label: string }[] = [
  { value: "year", label: "Год" },
  { value: "month", label: "Месяц" },
  { value: "week", label: "Неделя" },
  { value: "all", label: "Всё время" },
];

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Leaderboard() {
  const [period, setPeriod] = useState<Period>("year");
  const [rows, setRows] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

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
          <div key={row.user_id} className="lb-row">
            <div className="lb-rank">
              {row.rank <= 3 ? MEDALS[row.rank - 1] : row.rank}
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

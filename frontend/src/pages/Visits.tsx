import { useState, useEffect } from "react";
import api from "../api/client";

interface WeeklyRow {
  rank: number;
  name: string;
  visit_count: number;
  total_visits: number;
}

interface WeeklyResponse {
  week: number;
  date_range: string;
  rows: WeeklyRow[];
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

function currentWeekNum(): number {
  const now = new Date();
  const jan1 = new Date(now.getFullYear(), 0, 1);
  const days = Math.floor((now.getTime() - jan1.getTime()) / 86400000);
  return Math.ceil((days + jan1.getDay() + 1) / 7);
}

function bathWord(n: number): string {
  if (n === 1) return "баня";
  if (n >= 2 && n <= 4) return "бани";
  return "бань";
}

export default function Visits() {
  const [week, setWeek] = useState(currentWeekNum);
  const [data, setData] = useState<WeeklyResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<WeeklyResponse>(`/visits/weekly?week=${week}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [week]);

  const totalVisits = data?.rows.reduce((s, r) => s + r.visit_count, 0) ?? 0;

  return (
    <div>
      <div className="page-header">🏊 Визиты</div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 12 }}>
        <button className="tab" onClick={() => setWeek((w) => Math.max(1, w - 1))}>
          ←
        </button>
        <span style={{ fontWeight: 600 }}>
          Неделя {data?.week ?? week}
          {data?.date_range && (
            <span style={{ fontWeight: 400, opacity: 0.7, marginLeft: 8 }}>
              {data.date_range}
            </span>
          )}
        </span>
        <button className="tab" onClick={() => setWeek((w) => Math.min(53, w + 1))}>
          →
        </button>
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : !data || data.rows.length === 0 ? (
        <div className="loading">Нет визитов на этой неделе</div>
      ) : (
        <>
          {data.rows.map((row) => (
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
                  всего: {row.total_visits} {bathWord(row.total_visits)}
                </div>
              </div>
              <div>
                <div className="lb-points">{row.visit_count}</div>
                <div className="lb-meta" style={{ textAlign: "right" }}>
                  {bathWord(row.visit_count)}
                </div>
              </div>
            </div>
          ))}

          <div style={{ textAlign: "center", marginTop: 12, opacity: 0.7, fontSize: 14 }}>
            📊 Итого: {totalVisits} визитов, {data.rows.length} участников
          </div>
        </>
      )}
    </div>
  );
}

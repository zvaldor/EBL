import { useState, useEffect } from "react";
import api from "../api/client";

interface Visitor {
  user_id: number;
  full_name: string;
  username: string | null;
  visit_count: number;
}

interface BathMapEntry {
  bath_id: number;
  bath_name: string;
  city: string | null;
  lat: number | null;
  lng: number | null;
  total_visits: number;
  visitors: Visitor[];
}

type MapPeriod = "week" | "year" | "all";

const PERIODS: { value: MapPeriod; label: string }[] = [
  { value: "week", label: "Неделя" },
  { value: "year", label: "Год" },
  { value: "all", label: "Всё время" },
];

const AVATAR_COLORS = [
  "#e53935", "#8e24aa", "#1e88e5", "#00897b",
  "#43a047", "#fb8c00", "#6d4c41", "#546e7a",
];

function avatarColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

export default function BathMap() {
  const [period, setPeriod] = useState<MapPeriod>("year");
  const [entries, setEntries] = useState<BathMapEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .get<BathMapEntry[]>(`/baths/map?period=${period}`)
      .then((r) => setEntries(r.data))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      <div className="page-header">🗺️ Карта бань</div>

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
      ) : entries.length === 0 ? (
        <div className="loading">Нет данных</div>
      ) : (
        entries.map((entry) => {
          const isOpen = expanded === entry.bath_id;
          return (
            <div
              key={entry.bath_id}
              className="card"
              style={{ cursor: "pointer" }}
              onClick={() => setExpanded(isOpen ? null : entry.bath_id)}
            >
              {/* Bath header row */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 24 }}>🏠</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{entry.bath_name}</div>
                  {entry.city && (
                    <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>
                      {entry.city}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 700, color: "var(--tg-theme-button-color)", fontSize: 16 }}>
                    {entry.total_visits}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--tg-theme-hint-color)" }}>визит(а)</div>
                </div>
              </div>

              {/* Visitor avatars (always visible, compact) */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
                {entry.visitors.map((v) => (
                  <div
                    key={v.user_id}
                    title={`${v.full_name}: ${v.visit_count} визит(а)`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 5,
                      background: "var(--tg-theme-bg-color)",
                      borderRadius: 20,
                      padding: "3px 8px 3px 3px",
                      fontSize: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: "50%",
                        background: avatarColor(v.full_name),
                        color: "#fff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 9,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {initials(v.full_name)}
                    </div>
                    <span style={{ color: "var(--tg-theme-text-color)" }}>
                      {v.full_name.split(" ")[0]}
                    </span>
                    {v.visit_count > 1 && (
                      <span
                        style={{
                          background: "var(--tg-theme-button-color)",
                          color: "var(--tg-theme-button-text-color)",
                          borderRadius: 10,
                          padding: "0 5px",
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        ×{v.visit_count}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              {/* Expanded detail: full names + counts */}
              {isOpen && (
                <div style={{ marginTop: 10, borderTop: "1px solid var(--tg-theme-secondary-bg-color)", paddingTop: 10 }}>
                  {entry.visitors.map((v) => (
                    <div
                      key={v.user_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        fontSize: 13,
                      }}
                    >
                      <span>{v.full_name}{v.username ? ` @${v.username}` : ""}</span>
                      <span style={{ color: "var(--tg-theme-hint-color)" }}>
                        {v.visit_count} визит{v.visit_count === 1 ? "" : v.visit_count < 5 ? "а" : "ов"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

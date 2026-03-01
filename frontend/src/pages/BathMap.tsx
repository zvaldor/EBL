import { useState, useEffect } from "react";
import api from "../api/client";

interface Visitor {
  name: string;
  visit_count: number;
}

interface BathMapEntry {
  bath_name: string;
  city: string;
  country: string;
  total_visits: number;
  visitors: Visitor[];
}

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
  const [entries, setEntries] = useState<BathMapEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .get<BathMapEntry[]>("/baths/map")
      .then((r) => setEntries(r.data))
      .catch((e) => setError(e?.response?.data?.detail ?? "Ошибка загрузки"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = search.trim()
    ? entries.filter(
        (e) =>
          e.bath_name.toLowerCase().includes(search.toLowerCase()) ||
          e.city.toLowerCase().includes(search.toLowerCase()) ||
          e.visitors.some((v) =>
            v.name.toLowerCase().includes(search.toLowerCase())
          )
      )
    : entries;

  return (
    <div>
      <div className="page-header">🗺️ Карта бань</div>

      <div className="form-group" style={{ marginBottom: 8 }}>
        <input
          className="form-control"
          placeholder="Поиск по бане, городу, участнику..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : error ? (
        <div className="error">❌ {error}</div>
      ) : filtered.length === 0 ? (
        <div className="loading">Ничего не найдено</div>
      ) : (
        filtered.map((entry) => {
          const key = entry.bath_name + entry.city;
          const isOpen = expanded === key;
          return (
            <div
              key={key}
              className="card"
              style={{ cursor: "pointer" }}
              onClick={() => setExpanded(isOpen ? null : key)}
            >
              {/* Bath header */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 24 }}>🏠</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>
                    {entry.bath_name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>
                    {[entry.city, entry.country].filter(Boolean).join(", ")}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontWeight: 700,
                      color: "var(--tg-theme-button-color)",
                      fontSize: 18,
                    }}
                  >
                    {entry.total_visits}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--tg-theme-hint-color)" }}>
                    визитов
                  </div>
                </div>
              </div>

              {/* Visitor chips */}
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}
              >
                {entry.visitors.map((v) => (
                  <div
                    key={v.name}
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
                        background: avatarColor(v.name),
                        color: "#fff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 9,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {initials(v.name)}
                    </div>
                    <span>{v.name}</span>
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

              {/* Expanded: full list sorted by visit count */}
              {isOpen && (
                <div
                  style={{
                    marginTop: 10,
                    borderTop: "1px solid var(--tg-theme-secondary-bg-color)",
                    paddingTop: 10,
                  }}
                >
                  {entry.visitors.map((v) => (
                    <div
                      key={v.name}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        fontSize: 13,
                      }}
                    >
                      <span>{v.name}</span>
                      <span style={{ color: "var(--tg-theme-hint-color)" }}>
                        {v.visit_count}{" "}
                        {v.visit_count === 1
                          ? "визит"
                          : v.visit_count < 5
                          ? "визита"
                          : "визитов"}
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

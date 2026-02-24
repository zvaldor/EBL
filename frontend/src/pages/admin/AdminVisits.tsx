import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/client";
import type { Visit } from "../../types";

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending: "На рассмотрении",
  confirmed: "Подтверждено",
  disputed: "Спорное",
  cancelled: "Отменено",
};

export default function AdminVisits() {
  const navigate = useNavigate();
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");

  const load = () => {
    setLoading(true);
    const params = status ? `?status=${status}` : "";
    api
      .get<Visit[]>(`/visits${params}`)
      .then((r) => setVisits(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [status]);

  const action = async (id: number, endpoint: string) => {
    await api.post(`/visits/${id}/${endpoint}`);
    load();
  };

  return (
    <div>
      <div className="page-header">⚙️ Визиты (Админ)</div>

      <div className="tabs" style={{ marginBottom: 12 }}>
        {["", "draft", "confirmed", "disputed", "cancelled"].map((s) => (
          <button
            key={s}
            className={`tab ${status === s ? "active" : ""}`}
            onClick={() => setStatus(s)}
          >
            {s ? STATUS_LABELS[s] : "Все"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : (
        visits.map((v) => (
          <div key={v.id} className="card" style={{ cursor: "pointer" }}>
            <div
              style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}
              onClick={() => navigate(`/visits/${v.id}`)}
            >
              <div style={{ fontWeight: 600 }}>
                #{v.id} · {v.bath?.name ?? "—"}
              </div>
              <span className={`badge badge-${v.status === "confirmed" ? "green" : v.status === "cancelled" ? "red" : "blue"}`}>
                {STATUS_LABELS[v.status]}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)", marginBottom: 8 }}>
              {new Date(v.visited_at).toLocaleDateString("ru-RU")} ·{" "}
              {v.participants.map((p) => p.full_name).join(", ")} ·{" "}
              ⭐ {v.total_points.toFixed(0)}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {v.status !== "confirmed" && (
                <button className="btn btn-success btn-sm" onClick={() => action(v.id, "approve")}>
                  ✅ Подтвердить
                </button>
              )}
              {v.status !== "cancelled" && (
                <button className="btn btn-danger btn-sm" onClick={() => action(v.id, "cancel")}>
                  ❌ Отменить
                </button>
              )}
              {v.status !== "disputed" && (
                <button className="btn btn-sm" style={{ background: "#ff9800", color: "#fff" }}
                  onClick={() => action(v.id, "dispute")}>
                  ⚠️ Спор
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

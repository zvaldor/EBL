import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import type { Visit } from "../types";

const STATUS_LABELS: Record<string, string> = {
  draft: "📝 Черновик",
  pending: "⏳ На рассмотрении",
  confirmed: "✅ Подтверждено",
  disputed: "⚠️ Спорное",
  cancelled: "❌ Отменено",
};

const REASON_LABELS: Record<string, string> = {
  base: "Базовые очки",
  long: "Долго 150+",
  ultraunique: "Ультрауникальная баня",
  new_region: "Новый регион",
  new_country: "Новая страна",
};

export default function VisitDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [visit, setVisit] = useState<Visit | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Visit>(`/visits/${id}`)
      .then((r) => setVisit(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">⏳ Загрузка...</div>;
  if (!visit) return <div className="error">Визит не найден</div>;

  const date = new Date(visit.visited_at).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  // Group point logs by user
  const byUser: Record<number, { total: number; reasons: string[] }> = {};
  for (const log of visit.point_logs) {
    if (!byUser[log.user_id]) byUser[log.user_id] = { total: 0, reasons: [] };
    byUser[log.user_id].total += log.points;
    byUser[log.user_id].reasons.push(`+${log.points} ${REASON_LABELS[log.reason] ?? log.reason}`);
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", gap: 12 }}>
        <button onClick={() => navigate(-1)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}>
          ←
        </button>
        <div className="page-header" style={{ padding: 0 }}>
          Визит #{visit.id}
        </div>
      </div>

      <div className="card">
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
          🏠 {visit.bath?.name ?? "Баня не указана"}
        </div>
        {visit.bath?.city && (
          <div style={{ color: "var(--tg-theme-hint-color)", marginBottom: 4 }}>
            📍 {visit.bath.city}
          </div>
        )}
        <div style={{ color: "var(--tg-theme-hint-color)", marginBottom: 8 }}>📅 {date}</div>
        <div>{STATUS_LABELS[visit.status] ?? visit.status}</div>

        {visit.flag_long && <div style={{ marginTop: 8 }}>⏱ Долго 150+ мин</div>}
        {visit.flag_ultraunique && <div style={{ marginTop: 4 }}>⭐ Ультрауникальная баня</div>}
      </div>

      <div className="card">
        <div style={{ fontWeight: 600, marginBottom: 12 }}>
          👥 Участники ({visit.participants.length})
        </div>
        {visit.participants.map((p) => {
          const logs = byUser[p.id];
          return (
            <div key={p.id} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 500 }}>{p.full_name}</div>
                  {p.username && (
                    <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>
                      @{p.username}
                    </div>
                  )}
                </div>
                <div style={{ fontWeight: 700, color: "var(--tg-theme-button-color)" }}>
                  {logs ? `+${logs.total.toFixed(0)}` : "0"} очк.
                </div>
              </div>
              {logs && (
                <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)", marginTop: 4 }}>
                  {logs.reasons.join(" · ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 16 }}>
          <span>Итого очков:</span>
          <span style={{ color: "var(--tg-theme-button-color)" }}>
            {visit.total_points.toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import type { Visit, User, Bath, VisitParticipant } from "../types";

interface Props {
  user: User;
}

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
  ultraunique: "Ультрауникальная",
  new_region: "Новый регион",
  new_country: "Новая страна",
};

export default function VisitDetail({ user }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [visit, setVisit] = useState<Visit | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit state
  const [bathSearch, setBathSearch] = useState("");
  const [bathResults, setBathResults] = useState<Bath[]>([]);
  const [selectedBath, setSelectedBath] = useState<Pick<Bath, "id" | "name"> | null>(null);
  const [flagLong, setFlagLong] = useState(false);
  const [participants, setParticipants] = useState<VisitParticipant[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [userResults, setUserResults] = useState<{ id: number; full_name: string; username: string | null }[]>([]);

  const loadVisit = useCallback(() => {
    api.get<Visit>(`/visits/${id}`).then((r) => {
      setVisit(r.data);
      setLoading(false);
    });
  }, [id]);

  useEffect(() => { loadVisit(); }, [loadVisit]);

  function startEdit() {
    if (!visit) return;
    setSelectedBath(visit.bath ?? null);
    setBathSearch(visit.bath?.name ?? "");
    setFlagLong(visit.flag_long);
    setParticipants([...visit.participants]);
    setBathResults([]);
    setUserSearch("");
    setUserResults([]);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
  }

  // Bath search debounce
  useEffect(() => {
    if (!editing) return;
    if (bathSearch.length < 2) { setBathResults([]); return; }
    const t = setTimeout(() => {
      api.get<Bath[]>(`/baths?q=${encodeURIComponent(bathSearch)}&limit=5`)
        .then((r) => setBathResults(r.data));
    }, 300);
    return () => clearTimeout(t);
  }, [bathSearch, editing]);

  // User search debounce
  useEffect(() => {
    if (!editing) return;
    if (userSearch.length < 2) { setUserResults([]); return; }
    const t = setTimeout(() => {
      api.get<{ id: number; full_name: string; username: string | null }[]>(
        `/users/search?q=${encodeURIComponent(userSearch)}`
      ).then((r) => setUserResults(r.data));
    }, 300);
    return () => clearTimeout(t);
  }, [userSearch, editing]);

  async function saveEdit() {
    if (!visit) return;
    setSaving(true);
    try {
      const updated = await api.put<Visit>(`/visits/${visit.id}`, {
        bath_id: selectedBath?.id ?? null,
        flag_long: flagLong,
        participant_ids: participants.map((p) => p.id),
      });
      setVisit(updated.data);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function doAction(action: "approve" | "cancel" | "dispute") {
    if (!visit) return;
    setSaving(true);
    try {
      const updated = await api.post<Visit>(`/visits/${visit.id}/${action}`);
      setVisit(updated.data);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="loading">⏳ Загрузка...</div>;
  if (!visit) return <div className="error">Визит не найден</div>;

  const date = new Date(visit.visited_at).toLocaleDateString("ru-RU", {
    day: "numeric", month: "long", year: "numeric",
  });

  const byUser: Record<number, { total: number; reasons: string[] }> = {};
  for (const log of visit.point_logs) {
    if (!byUser[log.user_id]) byUser[log.user_id] = { total: 0, reasons: [] };
    byUser[log.user_id].total += log.points;
    byUser[log.user_id].reasons.push(`+${log.points} ${REASON_LABELS[log.reason] ?? log.reason}`);
  }

  const canEdit = user.is_admin || visit.created_by === user.id;

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", gap: 12 }}>
        <button onClick={() => navigate(-1)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}>
          ←
        </button>
        <div className="page-header" style={{ padding: 0, flex: 1 }}>
          Визит #{visit.id}
        </div>
        {canEdit && !editing && (
          <button className="btn btn-primary btn-sm" onClick={startEdit}>
            ✏️ Изменить
          </button>
        )}
      </div>

      {/* Admin action buttons */}
      {user.is_admin && !editing && (
        <div style={{ display: "flex", gap: 8, padding: "0 16px 12px" }}>
          {visit.status !== "confirmed" && (
            <button className="btn btn-success btn-sm" onClick={() => doAction("approve")} disabled={saving}>
              ✅ Подтвердить
            </button>
          )}
          {visit.status !== "disputed" && (
            <button className="btn btn-sm" style={{ background: "#ff9800", color: "#fff" }} onClick={() => doAction("dispute")} disabled={saving}>
              ⚠️ Спорное
            </button>
          )}
          {visit.status !== "cancelled" && (
            <button className="btn btn-danger btn-sm" onClick={() => doAction("cancel")} disabled={saving}>
              ❌ Отменить
            </button>
          )}
        </div>
      )}

      {/* Edit form */}
      {editing ? (
        <div className="card">
          <div style={{ fontWeight: 600, marginBottom: 12 }}>✏️ Редактирование</div>

          {/* Bath */}
          <div className="form-group" style={{ margin: "0 0 12px" }}>
            <label className="form-label">🏠 Баня</label>
            <input
              className="form-control"
              value={bathSearch}
              onChange={(e) => {
                setBathSearch(e.target.value);
                if (!e.target.value) setSelectedBath(null);
              }}
              placeholder="Поиск бани..."
            />
            {bathResults.length > 0 && (
              <div style={{ border: "1px solid var(--tg-theme-secondary-bg-color)", borderRadius: 8, marginTop: 4 }}>
                {bathResults.map((b) => (
                  <div
                    key={b.id}
                    style={{ padding: "8px 12px", cursor: "pointer" }}
                    onClick={() => { setSelectedBath(b); setBathSearch(b.name); setBathResults([]); }}
                  >
                    {b.name}{b.city ? ` (${b.city})` : ""}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* flag_long */}
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, cursor: "pointer" }}>
            <input type="checkbox" checked={flagLong} onChange={(e) => setFlagLong(e.target.checked)} />
            ⏱ Долго 150+ мин
          </label>

          {/* Participants */}
          <div style={{ marginBottom: 12 }}>
            <div className="form-label">👥 Участники</div>
            {participants.map((p) => (
              <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 0" }}>
                <span>{p.full_name}{p.username ? ` (@${p.username})` : ""}</span>
                <button
                  style={{ background: "none", border: "none", color: "#f44336", cursor: "pointer", fontSize: 16 }}
                  onClick={() => setParticipants(participants.filter((x) => x.id !== p.id))}
                >
                  ✕
                </button>
              </div>
            ))}
            <input
              className="form-control"
              style={{ marginTop: 8 }}
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Добавить участника..."
            />
            {userResults.length > 0 && (
              <div style={{ border: "1px solid var(--tg-theme-secondary-bg-color)", borderRadius: 8, marginTop: 4 }}>
                {userResults
                  .filter((u) => !participants.find((p) => p.id === u.id))
                  .map((u) => (
                    <div
                      key={u.id}
                      style={{ padding: "8px 12px", cursor: "pointer" }}
                      onClick={() => {
                        setParticipants([...participants, { id: u.id, full_name: u.full_name, username: u.username }]);
                        setUserSearch("");
                        setUserResults([]);
                      }}
                    >
                      {u.full_name}{u.username ? ` (@${u.username})` : ""}
                    </div>
                  ))}
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={saveEdit} disabled={saving}>
              {saving ? "Сохранение..." : "💾 Сохранить"}
            </button>
            <button className="btn" style={{ background: "var(--tg-theme-secondary-bg-color)", flex: 1 }} onClick={cancelEdit}>
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Visit info card */}
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

          {/* Participants card */}
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

          {/* Total */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: 16 }}>
              <span>Итого очков:</span>
              <span style={{ color: "var(--tg-theme-button-color)" }}>
                {visit.total_points.toFixed(0)}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

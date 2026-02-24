import { useState, useEffect } from "react";
import api from "../../api/client";

interface AdminUser {
  id: number;
  username: string | null;
  full_name: string;
  is_admin: boolean;
  is_active: boolean;
  points: number;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    api
      .get<AdminUser[]>("/users")
      .then((r) => setUsers(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const update = async (id: number, patch: Partial<AdminUser>) => {
    await api.put(`/users/${id}`, patch);
    load();
  };

  return (
    <div>
      <div className="page-header">👥 Пользователи (Админ)</div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : (
        users.map((u) => (
          <div key={u.id} className="card" style={{ margin: "6px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                {u.username && (
                  <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>
                    @{u.username}
                  </div>
                )}
                <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>
                  ⭐ {u.points.toFixed(0)} очков
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {u.is_admin && <span className="badge badge-blue">👑 Админ</span>}
                {!u.is_active && <span className="badge badge-red">Деактивирован</span>}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              <button
                className={`btn btn-sm ${u.is_admin ? "btn-danger" : "btn-primary"}`}
                onClick={() => update(u.id, { is_admin: !u.is_admin })}
              >
                {u.is_admin ? "Снять админа" : "Назначить админом"}
              </button>
              <button
                className={`btn btn-sm ${u.is_active ? "btn-danger" : "btn-success"}`}
                onClick={() => update(u.id, { is_active: !u.is_active })}
              >
                {u.is_active ? "Деактивировать" : "Активировать"}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

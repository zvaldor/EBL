import { useState, useEffect } from "react";
import api from "../api/client";
import type { User, Visit } from "../types";
import VisitCard from "../components/VisitCard";

interface Props {
  user: User;
}

export default function Profile({ user }: Props) {
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Visit[]>("/visits/me")
      .then((r) => setVisits(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">🙋 Профиль</div>

      <div className="card">
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
          {user.full_name}
        </div>
        {user.username && (
          <div style={{ color: "var(--tg-theme-hint-color)", marginBottom: 12 }}>
            @{user.username}
          </div>
        )}
        <div style={{ display: "flex", gap: 24 }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 800, color: "var(--tg-theme-button-color)" }}>
              {user.points.toFixed(0)}
            </div>
            <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>очков</div>
          </div>
          <div>
            <div style={{ fontSize: 28, fontWeight: 800 }}>{user.visit_count}</div>
            <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)" }}>визитов</div>
          </div>
        </div>
        {user.is_admin && (
          <div style={{ marginTop: 12 }}>
            <span className="badge badge-blue">👑 Администратор</span>
          </div>
        )}
      </div>

      <div className="page-header" style={{ fontSize: 16, paddingTop: 8 }}>
        Мои визиты
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : visits.length === 0 ? (
        <div className="loading">Пока нет визитов</div>
      ) : (
        visits.map((v) => <VisitCard key={v.id} visit={v} />)
      )}
    </div>
  );
}

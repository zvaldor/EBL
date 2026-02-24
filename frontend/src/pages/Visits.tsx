import { useState, useEffect } from "react";
import api from "../api/client";
import type { Visit } from "../types";
import VisitCard from "../components/VisitCard";

const STATUSES = [
  { value: "", label: "Все" },
  { value: "draft", label: "Черновики" },
  { value: "confirmed", label: "Подтверждённые" },
  { value: "disputed", label: "Спорные" },
];

export default function Visits() {
  const [visits, setVisits] = useState<Visit[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = status ? `?status=${status}` : "";
    api
      .get<Visit[]>(`/visits${params}`)
      .then((r) => setVisits(r.data))
      .finally(() => setLoading(false));
  }, [status]);

  return (
    <div>
      <div className="page-header">🏊 Визиты</div>

      <div className="tabs" style={{ marginBottom: 12 }}>
        {STATUSES.map((s) => (
          <button
            key={s.value}
            className={`tab ${status === s.value ? "active" : ""}`}
            onClick={() => setStatus(s.value)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : visits.length === 0 ? (
        <div className="loading">Нет визитов</div>
      ) : (
        visits.map((v) => <VisitCard key={v.id} visit={v} />)
      )}
    </div>
  );
}

import { useNavigate } from "react-router-dom";
import type { Visit } from "../types";

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending: "На рассмотрении",
  confirmed: "Подтверждено",
  disputed: "Спорное",
  cancelled: "Отменено",
};

interface Props {
  visit: Visit;
}

export default function VisitCard({ visit }: Props) {
  const navigate = useNavigate();
  const date = new Date(visit.visited_at).toLocaleDateString("ru-RU");

  return (
    <div className="visit-card" onClick={() => navigate(`/visits/${visit.id}`)}>
      <div className="visit-card-header">
        <div className="visit-bath-name">
          {visit.bath?.name ?? "Баня не указана"}
        </div>
        <span className={`visit-status ${visit.status}`}>
          {STATUS_LABELS[visit.status] ?? visit.status}
        </span>
      </div>
      <div className="visit-meta">
        📅 {date} · 👥 {visit.participants.length} чел.
        {visit.flag_long && " · ⏱ 150+"}
        {visit.flag_ultraunique && " · ⭐ Ультра"}
        {visit.bath?.city && ` · 📍 ${visit.bath.city}`}
      </div>
      <div className="visit-points">⭐ {visit.total_points.toFixed(0)} очков</div>
    </div>
  );
}

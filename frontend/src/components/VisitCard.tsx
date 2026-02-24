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
  const participantNames = visit.participants
    .map((p) => p.full_name || (p.username ? `@${p.username}` : String(p.id)))
    .join(", ");

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
        📅 {date}
        {visit.bath?.city && ` · 📍 ${visit.bath.city}`}
        {visit.flag_long && " · ⏱ 150+"}
        {visit.flag_ultraunique && " · ⭐ Ультра"}
      </div>
      {participantNames && (
        <div className="visit-participants">👥 {participantNames}</div>
      )}
      <div className="visit-points">⭐ {visit.total_points.toFixed(0)} очков</div>
    </div>
  );
}

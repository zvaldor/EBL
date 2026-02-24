import { NavLink } from "react-router-dom";

interface Props {
  isAdmin: boolean;
}

export default function Navigation({ isAdmin }: Props) {
  return (
    <nav className="nav">
      <NavLink to="/leaderboard" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🏆</span>
        Рейтинг
      </NavLink>
      <NavLink to="/visits" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🏊</span>
        Визиты
      </NavLink>
      <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🙋</span>
        Профиль
      </NavLink>
      {isAdmin && (
        <NavLink to="/admin/visits" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
          <span className="nav-icon">⚙️</span>
          Админ
        </NavLink>
      )}
    </nav>
  );
}

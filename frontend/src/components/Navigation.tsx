import { NavLink } from "react-router-dom";

export default function Navigation() {
  return (
    <nav className="nav">
      <NavLink to="/leaderboard" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🏆</span>
        Рейтинг
      </NavLink>
      <NavLink to="/visits" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🛁</span>
        Визиты
      </NavLink>
      <NavLink to="/bath-map" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
        <span className="nav-icon">🗺️</span>
        Карта
      </NavLink>
    </nav>
  );
}

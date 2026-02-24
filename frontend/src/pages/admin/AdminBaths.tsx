import { useState, useEffect } from "react";
import api from "../../api/client";
import type { Bath, Country, Region } from "../../types";

export default function AdminBaths() {
  const [baths, setBaths] = useState<Bath[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Bath | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: "", city: "", country_id: "", region_id: "",
    lat: "", lng: "", url: "", description: "",
  });

  const load = () => {
    setLoading(true);
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    Promise.all([
      api.get<Bath[]>(`/baths${q}`),
      api.get<Country[]>("/baths/countries"),
      api.get<Region[]>("/baths/regions"),
    ])
      .then(([b, c, r]) => {
        setBaths(b.data);
        setCountries(c.data);
        setRegions(r.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };

  const startEdit = (bath: Bath) => {
    setEditing(bath);
    setForm({
      name: bath.name,
      city: bath.city ?? "",
      country_id: bath.country_id?.toString() ?? "",
      region_id: bath.region_id?.toString() ?? "",
      lat: bath.lat?.toString() ?? "",
      lng: bath.lng?.toString() ?? "",
      url: bath.url ?? "",
      description: bath.description ?? "",
    });
    setShowCreate(false);
  };

  const startCreate = () => {
    setEditing(null);
    setForm({ name: "", city: "", country_id: "", region_id: "", lat: "", lng: "", url: "", description: "" });
    setShowCreate(true);
  };

  const save = async () => {
    const payload = {
      name: form.name,
      city: form.city || null,
      country_id: form.country_id ? parseInt(form.country_id) : null,
      region_id: form.region_id ? parseInt(form.region_id) : null,
      lat: form.lat ? parseFloat(form.lat) : null,
      lng: form.lng ? parseFloat(form.lng) : null,
      url: form.url || null,
      description: form.description || null,
    };
    if (editing) {
      await api.put(`/baths/${editing.id}`, payload);
    } else {
      await api.post("/baths", payload);
    }
    setEditing(null);
    setShowCreate(false);
    load();
  };

  const archive = async (id: number) => {
    await api.put(`/baths/${id}`, { is_archived: true });
    load();
  };

  const filteredRegions = form.country_id
    ? regions.filter((r) => r.country_id === parseInt(form.country_id))
    : regions;

  return (
    <div>
      <div className="page-header">🏠 Бани (Админ)</div>

      <div style={{ padding: "0 16px", marginBottom: 12 }}>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
          <input
            className="form-control"
            placeholder="Поиск по названию..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">🔍</button>
        </form>
      </div>

      <div style={{ padding: "0 16px", marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={startCreate}>+ Добавить баню</button>
      </div>

      {(showCreate || editing) && (
        <div className="card" style={{ margin: "0 16px 16px" }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>
            {editing ? `Редактировать: ${editing.name}` : "Новая баня"}
          </div>
          {[
            ["name", "Название *"],
            ["city", "Город"],
            ["lat", "Широта"],
            ["lng", "Долгота"],
            ["url", "Ссылка"],
            ["description", "Описание"],
          ].map(([key, label]) => (
            <div className="form-group" key={key} style={{ margin: "0 0 8px" }}>
              <label className="form-label">{label}</label>
              <input
                className="form-control"
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <div className="form-group" style={{ margin: "0 0 8px" }}>
            <label className="form-label">Страна</label>
            <select
              className="form-control"
              value={form.country_id}
              onChange={(e) => setForm({ ...form, country_id: e.target.value, region_id: "" })}
            >
              <option value="">— не выбрана —</option>
              {countries.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ margin: "0 0 12px" }}>
            <label className="form-label">Регион</label>
            <select
              className="form-control"
              value={form.region_id}
              onChange={(e) => setForm({ ...form, region_id: e.target.value })}
            >
              <option value="">— не выбран —</option>
              {filteredRegions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={save}>💾 Сохранить</button>
            <button className="btn" style={{ background: "#eee" }} onClick={() => { setEditing(null); setShowCreate(false); }}>
              Отмена
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading">⏳ Загрузка...</div>
      ) : baths.length === 0 ? (
        <div className="loading">Бани не найдены</div>
      ) : (
        baths.map((bath) => (
          <div key={bath.id} className="card" style={{ margin: "6px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontWeight: 600 }}>{bath.name}</div>
              {bath.is_archived && <span className="badge badge-red">Архив</span>}
            </div>
            <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)", marginTop: 4 }}>
              {bath.city && `📍 ${bath.city}`}
              {bath.lat && ` · ${bath.lat.toFixed(4)}, ${bath.lng?.toFixed(4)}`}
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => startEdit(bath)}>✏️ Редактировать</button>
              {!bath.is_archived && (
                <button className="btn btn-danger btn-sm" onClick={() => archive(bath.id)}>🗄 Архив</button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import type { Bath, User, Country, Region } from "../types";

interface Props {
  user: User;
}

const EMPTY_FORM = {
  name: "",
  city: "",
  country_id: null as number | null,
  region_id: null as number | null,
  url: "",
  description: "",
};

export default function Baths({ user }: Props) {
  const [baths, setBaths] = useState<Bath[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const [showForm, setShowForm] = useState(false);
  const [editBath, setEditBath] = useState<Bath | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);

  const [countries, setCountries] = useState<Country[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);

  const loadBaths = useCallback(() => {
    setLoading(true);
    const q = search ? `?q=${encodeURIComponent(search)}` : "";
    api.get<Bath[]>(`/baths${q}`)
      .then((r) => setBaths(r.data))
      .finally(() => setLoading(false));
  }, [search]);

  useEffect(() => { loadBaths(); }, [loadBaths]);

  useEffect(() => {
    api.get<Country[]>("/baths/countries").then((r) => setCountries(r.data));
  }, []);

  useEffect(() => {
    if (!form.country_id) { setRegions([]); return; }
    api.get<Region[]>(`/baths/regions?country_id=${form.country_id}`)
      .then((r) => setRegions(r.data));
  }, [form.country_id]);

  function openCreate() {
    setEditBath(null);
    setForm({ ...EMPTY_FORM });
    setShowForm(true);
  }

  function openEdit(bath: Bath) {
    setEditBath(bath);
    setForm({
      name: bath.name,
      city: bath.city ?? "",
      country_id: bath.country_id,
      region_id: bath.region_id,
      url: bath.url ?? "",
      description: bath.description ?? "",
    });
    setShowForm(true);
  }

  async function handleSave() {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        city: form.city || null,
        country_id: form.country_id,
        region_id: form.region_id,
        url: form.url || null,
        description: form.description || null,
      };
      if (editBath) {
        await api.put(`/baths/${editBath.id}`, payload);
      } else {
        await api.post("/baths", payload);
      }
      setShowForm(false);
      loadBaths();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(bath: Bath) {
    if (!confirm(`Удалить баню "${bath.name}"?`)) return;
    await api.delete(`/baths/${bath.id}`);
    loadBaths();
  }

  // Search with debounce
  const [searchInput, setSearchInput] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", padding: "16px 16px 8px" }}>
        <div className="page-header" style={{ padding: 0, flex: 1 }}>🏠 Бани</div>
        <button className="btn btn-primary btn-sm" onClick={openCreate}>
          ➕ Добавить
        </button>
      </div>

      <div className="form-group">
        <input
          className="form-control"
          placeholder="🔍 Поиск..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      {/* Add/Edit form */}
      {showForm && (
        <div className="card" style={{ margin: "0 16px 12px" }}>
          <div style={{ fontWeight: 600, marginBottom: 12 }}>
            {editBath ? "✏️ Редактировать баню" : "➕ Новая баня"}
          </div>

          <div className="form-group" style={{ margin: "0 0 10px" }}>
            <label className="form-label">Название *</label>
            <input
              className="form-control"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Название бани"
            />
          </div>

          <div className="form-group" style={{ margin: "0 0 10px" }}>
            <label className="form-label">Город</label>
            <input
              className="form-control"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
              placeholder="Город"
            />
          </div>

          <div className="form-group" style={{ margin: "0 0 10px" }}>
            <label className="form-label">Страна</label>
            <select
              className="form-control"
              value={form.country_id ?? ""}
              onChange={(e) => setForm({ ...form, country_id: e.target.value ? Number(e.target.value) : null, region_id: null })}
            >
              <option value="">— не выбрана —</option>
              {countries.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          {regions.length > 0 && (
            <div className="form-group" style={{ margin: "0 0 10px" }}>
              <label className="form-label">Регион</label>
              <select
                className="form-control"
                value={form.region_id ?? ""}
                onChange={(e) => setForm({ ...form, region_id: e.target.value ? Number(e.target.value) : null })}
              >
                <option value="">— не выбран —</option>
                {regions.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
          )}

          <div className="form-group" style={{ margin: "0 0 10px" }}>
            <label className="form-label">Сайт</label>
            <input
              className="form-control"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder="https://..."
            />
          </div>

          <div className="form-group" style={{ margin: "0 0 12px" }}>
            <label className="form-label">Описание</label>
            <input
              className="form-control"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Краткое описание"
            />
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleSave} disabled={saving || !form.name.trim()}>
              {saving ? "Сохранение..." : "💾 Сохранить"}
            </button>
            <button className="btn" style={{ background: "var(--tg-theme-secondary-bg-color)", flex: 1 }} onClick={() => setShowForm(false)}>
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{bath.name}</div>
                {bath.city && (
                  <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)", marginTop: 2 }}>
                    📍 {bath.city}
                  </div>
                )}
                {bath.description && (
                  <div style={{ fontSize: 12, color: "var(--tg-theme-hint-color)", marginTop: 2 }}>
                    {bath.description}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 6, marginLeft: 8 }}>
                <button className="btn btn-sm" style={{ background: "var(--tg-theme-secondary-bg-color)" }} onClick={() => openEdit(bath)}>
                  ✏️
                </button>
                {user.is_admin && (
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(bath)}>
                    🗑
                  </button>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

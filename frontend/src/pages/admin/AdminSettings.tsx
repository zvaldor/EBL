import { useState, useEffect } from "react";
import api from "../../api/client";
import type { PointConfig } from "../../types";

const FIELD_LABELS: Record<string, string> = {
  base_points: "Базовые очки за визит",
  long_bonus: "Бонус за долгое посещение (150+ мин)",
  region_bonus: "Бонус за новый регион",
  country_bonus: "Бонус за новую страну",
  ultraunique_bonus: "Бонус за ультрауникальную баню",
};

export default function AdminSettings() {
  const [config, setConfig] = useState<PointConfig>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    api
      .get<PointConfig>("/settings")
      .then((r) => {
        setConfig(r.data);
        const v: Record<string, string> = {};
        for (const [key, cfg] of Object.entries(r.data)) {
          v[key] = cfg.value.toString();
        }
        setValues(v);
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    const payload: Record<string, number> = {};
    for (const [k, v] of Object.entries(values)) {
      const n = parseFloat(v);
      if (!isNaN(n)) payload[k] = n;
    }
    await api.put("/settings", payload);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading) return <div className="loading">⏳ Загрузка...</div>;

  return (
    <div>
      <div className="page-header">⚙️ Настройки очков</div>

      {Object.keys(config).map((key) => (
        <div className="form-group" key={key}>
          <label className="form-label">
            {FIELD_LABELS[key] ?? key}
          </label>
          <div style={{ fontSize: 11, color: "var(--tg-theme-hint-color)", marginBottom: 4 }}>
            {config[key].description}
          </div>
          <input
            className="form-control"
            type="number"
            step="0.5"
            min="0"
            value={values[key] ?? ""}
            onChange={(e) => setValues({ ...values, [key]: e.target.value })}
          />
        </div>
      ))}

      <div style={{ padding: "0 16px", marginTop: 16 }}>
        <button className="btn btn-primary" onClick={save} disabled={saving} style={{ width: "100%" }}>
          {saving ? "Сохранение..." : saved ? "✅ Сохранено!" : "💾 Сохранить настройки"}
        </button>
      </div>
    </div>
  );
}

import { useState } from "react";

interface Props {
  onLogin: (password: string) => void;
  error: string | null;
  loading: boolean;
}

export default function PasswordLogin({ onLogin, error, loading }: Props) {
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password.trim()) onLogin(password.trim());
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "24px",
        gap: 16,
      }}
    >
      <div style={{ fontSize: 48 }}>🛁</div>
      <div style={{ fontWeight: 700, fontSize: 20, textAlign: "center" }}>
        ЕБЛ — Евразийская Банная Лига
      </div>
      <div style={{ opacity: 0.6, fontSize: 14, textAlign: "center" }}>
        Введите пароль для входа
      </div>

      <form
        onSubmit={handleSubmit}
        style={{ width: "100%", maxWidth: 320, display: "flex", flexDirection: "column", gap: 12 }}
      >
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          style={{
            padding: "12px 16px",
            borderRadius: 12,
            border: "1px solid rgba(128,128,128,0.3)",
            fontSize: 16,
            background: "var(--tg-theme-secondary-bg-color, #f5f5f5)",
            color: "inherit",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading || !password.trim()}
          className="tab"
          style={{
            padding: "12px",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            opacity: loading || !password.trim() ? 0.5 : 1,
          }}
        >
          {loading ? "Вход..." : "Войти"}
        </button>
      </form>

      {error && (
        <div style={{ color: "#e53935", fontSize: 14, textAlign: "center" }}>
          {error === "Invalid password" ? "Неверный пароль" : error}
        </div>
      )}
    </div>
  );
}

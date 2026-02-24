import { useState, useEffect } from "react";
import api from "../api/client";
import type { User } from "../types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Initialize Telegram WebApp
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }

    // Must be opened inside Telegram (or have dev token in localStorage)
    const initData =
      window.Telegram?.WebApp?.initData ||
      localStorage.getItem("dev_init_data");
    if (!initData) {
      setError("Открой приложение через Telegram");
      setLoading(false);
      return;
    }

    api
      .get<User>("/users/me")
      .then((res) => setUser(res.data))
      .catch((err) => {
        const detail = err.response?.data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail.map((d: { msg: string }) => d.msg).join("; ")
            : "Auth error";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, []);

  return { user, loading, error };
}

import { useState, useEffect } from "react";
import api from "../api/client";
import type { User } from "../types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsPassword, setNeedsPassword] = useState(false);

  const fetchUser = () => {
    setLoading(true);
    setError(null);
    api
      .get<User>("/users/me")
      .then((res) => {
        setUser(res.data);
        setNeedsPassword(false);
      })
      .catch((err) => {
        const detail = err.response?.data?.detail;
        const msg =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? detail.map((d: { msg: string }) => d.msg).join("; ")
            : "Auth error";
        setError(msg);
        // If web_password was wrong, clear it
        if (err.response?.status === 401) {
          localStorage.removeItem("web_password");
          setNeedsPassword(true);
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }

    const hasTelegram = !!window.Telegram?.WebApp?.initData;
    const hasDevData = !!localStorage.getItem("dev_init_data");
    const hasWebPassword = !!localStorage.getItem("web_password");

    if (!hasTelegram && !hasDevData && !hasWebPassword) {
      setNeedsPassword(true);
      setLoading(false);
      return;
    }

    fetchUser();
  }, []);

  const loginWithPassword = (password: string) => {
    localStorage.setItem("web_password", password);
    fetchUser();
  };

  const logout = () => {
    localStorage.removeItem("web_password");
    setUser(null);
    setNeedsPassword(true);
  };

  return { user, loading, error, needsPassword, loginWithPassword, logout };
}

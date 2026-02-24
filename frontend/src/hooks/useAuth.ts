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

    api
      .get<User>("/users/me")
      .then((res) => setUser(res.data))
      .catch((err) => {
        setError(err.response?.data?.detail || "Auth error");
      })
      .finally(() => setLoading(false));
  }, []);

  return { user, loading, error };
}

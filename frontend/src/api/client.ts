import axios from "axios";

const getInitData = (): string => {
  if (typeof window !== "undefined" && window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData;
  }
  // Dev fallback
  return localStorage.getItem("dev_init_data") || "";
};

const api = axios.create({
  // VITE_API_URL is set in Netlify env vars to point to Railway backend.
  // Falls back to /api for Railway-served deployments.
  baseURL: (import.meta.env.VITE_API_URL as string | undefined) ?? "/api",
});

api.interceptors.request.use((config) => {
  const initData = getInitData();
  if (initData) {
    config.headers["X-Telegram-Init-Data"] = initData;
  }
  return config;
});

export default api;

// Declare Telegram WebApp types
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
          };
        };
        ready(): void;
        expand(): void;
        close(): void;
        MainButton: {
          text: string;
          show(): void;
          hide(): void;
          onClick(fn: () => void): void;
        };
        colorScheme: "light" | "dark";
        themeParams: Record<string, string>;
      };
    };
  }
}

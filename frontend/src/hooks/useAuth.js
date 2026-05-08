import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "https://ntdat232-hotel-absa-api.hf.space";

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token  = params.get("token");
    if (token) {
      localStorage.setItem("hs_token", token);
      window.history.replaceState({}, "", window.location.pathname);
    }
    const stored = localStorage.getItem("hs_token");
    if (stored) fetchMe(stored);
    else setLoading(false);
  }, []);

  async function fetchMe(token) {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      } else {
        localStorage.removeItem("hs_token");
      }
    } catch {
      localStorage.removeItem("hs_token");
    } finally {
      setLoading(false);
    }
  }

  function login() {
    window.location.href = `${API_BASE}/auth/google/login`;
  }

  function logout() {
    localStorage.removeItem("hs_token");
    setUser(null);
  }

  return { user, loading, login, logout };
}
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchProfile, refreshSession } from "../services/api.js";

const AuthContext = createContext(null);

const ACCESS_KEY = "agrishield_access_token";
const REFRESH_KEY = "agrishield_refresh_token";

export function getStoredAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_KEY));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem(REFRESH_KEY));
  const [loading, setLoading] = useState(true);

  function persistSession(session) {
    localStorage.setItem(ACCESS_KEY, session.access_token);
    if (session.refresh_token) {
      localStorage.setItem(REFRESH_KEY, session.refresh_token);
      setRefreshToken(session.refresh_token);
    }
    setAccessToken(session.access_token);
    setUser(session.user);
  }

  function clearSession() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      setLoading(true);
      try {
        if (accessToken) {
          const profile = await fetchProfile(accessToken);
          if (!cancelled) setUser(profile);
          return;
        }
        if (refreshToken) {
          const session = await refreshSession(refreshToken);
          if (!cancelled) persistSession(session);
        }
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      accessToken,
      refreshToken,
      loading,
      isAuthenticated: Boolean(user && accessToken),
      isAdmin: user?.role === "ADMIN",
      persistSession,
      clearSession
    }),
    [user, accessToken, refreshToken, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}

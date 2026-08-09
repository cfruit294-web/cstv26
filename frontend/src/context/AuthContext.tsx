"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  getMe,
  login as apiLogin,
  loginTwoFactor as apiLoginTwoFactor,
  logout as apiLogout,
  refreshAccessToken,
  registerAccount as apiRegister,
} from "@/lib/api";
import type { User } from "@/lib/types";

const ACCESS_KEY = "cstv_access";
const REFRESH_KEY = "cstv_refresh";

interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ twoFactorRequired: boolean; preAuthToken?: string }>;
  loginTwoFactor: (preAuthToken: string, code: string) => Promise<void>;
  register: (email: string, password: string, passwordConfirm: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  getValidAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredTokens() {
  if (typeof window === "undefined") return { access: null, refresh: null };
  return {
    access: window.localStorage.getItem(ACCESS_KEY),
    refresh: window.localStorage.getItem(REFRESH_KEY),
  };
}

function storeTokens(access: string, refresh: string) {
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const { access, refresh } = readStoredTokens();
    if (!access || !refresh) {
      queueMicrotask(() => setIsLoading(false));
      return;
    }

    (async () => {
      try {
        const me = await getMe(access);
        setUser(me);
        setAccessToken(access);
      } catch {
        try {
          const tokens = await refreshAccessToken(refresh);
          const me = await getMe(tokens.access);
          storeTokens(tokens.access, tokens.refresh);
          setUser(me);
          setAccessToken(tokens.access);
        } catch {
          clearTokens();
        }
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiLogin({ email, password });
    if (result.two_factor_required) {
      return { twoFactorRequired: true, preAuthToken: result.pre_auth_token };
    }
    if (result.access && result.refresh && result.user) {
      storeTokens(result.access, result.refresh);
      setAccessToken(result.access);
      setUser(result.user);
    }
    return { twoFactorRequired: false };
  }, []);

  const loginTwoFactor = useCallback(async (preAuthToken: string, code: string) => {
    const result = await apiLoginTwoFactor({ pre_auth_token: preAuthToken, code });
    if (result.access && result.refresh && result.user) {
      storeTokens(result.access, result.refresh);
      setAccessToken(result.access);
      setUser(result.user);
    }
  }, []);

  const register = useCallback(
    async (email: string, password: string, passwordConfirm: string, fullName?: string) => {
      await apiRegister({ email, password, password_confirm: passwordConfirm, full_name: fullName });
    },
    [],
  );

  const logout = useCallback(async () => {
    const { refresh } = readStoredTokens();
    if (refresh && accessToken) {
      try {
        await apiLogout(refresh, accessToken);
      } catch {
        // token already invalid server-side, proceed with local cleanup anyway
      }
    }
    clearTokens();
    setUser(null);
    setAccessToken(null);
  }, [accessToken]);

  const getValidAccessToken = useCallback(async () => {
    const { access, refresh } = readStoredTokens();
    if (!access || !refresh) return null;
    try {
      await getMe(access);
      return access;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        try {
          const tokens = await refreshAccessToken(refresh);
          storeTokens(tokens.access, tokens.refresh);
          setAccessToken(tokens.access);
          return tokens.access;
        } catch {
          clearTokens();
          setUser(null);
          setAccessToken(null);
          return null;
        }
      }
      return access;
    }
  }, []);

  const value = useMemo(
    () => ({ user, accessToken, isLoading, login, loginTwoFactor, register, logout, getValidAccessToken }),
    [user, accessToken, isLoading, login, loginTwoFactor, register, logout, getValidAccessToken],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

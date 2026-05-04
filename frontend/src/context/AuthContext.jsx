import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { auth as authApi } from '../api/client';

const GUEST_KEY = 'specagent_guest';

function readGuest() {
  return sessionStorage.getItem(GUEST_KEY) === '1';
}

function readToken() {
  return localStorage.getItem('access_token');
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [guestMode, setGuestMode] = useState(readGuest);
  const [authTick, setAuthTick] = useState(0);

  const isAuthenticated = Boolean(readToken());

  const enterGuest = useCallback(() => {
    sessionStorage.setItem(GUEST_KEY, '1');
    setGuestMode(true);
  }, []);

  const exitGuest = useCallback(() => {
    sessionStorage.removeItem(GUEST_KEY);
    setGuestMode(false);
  }, []);

  const login = useCallback(
    async (email, password) => {
      exitGuest();
      await authApi.login(email, password);
      setAuthTick((t) => t + 1);
    },
    [exitGuest],
  );

  const register = useCallback(
    async (email, password, name) => {
      exitGuest();
      await authApi.register(email, password, name);
    },
    [exitGuest],
  );

  const logout = useCallback(() => {
    authApi.logout();
    exitGuest();
    setAuthTick((t) => t + 1);
  }, [exitGuest]);

  const value = useMemo(
    () => ({
      guestMode,
      isAuthenticated: Boolean(readToken()),
      authTick,
      hasAccess: Boolean(readToken()) || guestMode,
      enterGuest,
      exitGuest,
      login,
      register,
      logout,
    }),
    [guestMode, authTick, enterGuest, exitGuest, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

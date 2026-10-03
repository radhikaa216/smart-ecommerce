import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { User } from "../types";

type SessionValue = {
  user: User | null; loading: boolean; authMode: "local" | "auth0";
  login(email: string, password: string): Promise<void>;
  register(name: string, email: string, password: string): Promise<void>;
  loginWithProvider(): Promise<void>; logout(): void; getToken(): Promise<string | null>;
};

const SessionContext = createContext<SessionValue | null>(null);
const authMode = import.meta.env.VITE_AUTH_MODE === "auth0" ? "auth0" : "local";

function LocalSession({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("access_token"));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  useEffect(() => {
    if (!token) { setLoading(false); return; }
    api<User>("/auth/me", {}, token).then(setUser).catch(() => {
      localStorage.removeItem("access_token"); setToken(null);
    }).finally(() => setLoading(false));
  }, [token]);
  const login = async (email: string, password: string) => {
    const result = await api<{ access_token: string; user: User }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    localStorage.setItem("access_token", result.access_token); setToken(result.access_token); setUser(result.user);
  };
  const register = async (name: string, email: string, password: string) => {
    await api("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) });
    await login(email, password);
  };
  const logout = () => { localStorage.removeItem("access_token"); setToken(null); setUser(null); };
  const value = useMemo<SessionValue>(() => ({ user, loading, authMode: "local", login, register, loginWithProvider: async () => {}, logout, getToken: async () => token }), [user, loading, token]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

function Auth0Session({ children }: { children: ReactNode }) {
  const auth = useAuth0();
  const [user, setUser] = useState<User | null>(null);
  const getToken = useCallback(async (): Promise<string | null> => {
    if (!auth.isAuthenticated) return null;
    return (await auth.getAccessTokenSilently()) || null;
  }, [auth.isAuthenticated, auth.getAccessTokenSilently]);
  useEffect(() => {
    if (!auth.isAuthenticated) { setUser(null); return; }
    getToken().then((token) => {
      if (token) return api<User>("/auth/me", {}, token).then(setUser);
    });
  }, [auth.isAuthenticated, getToken]);
  const unsupported = async () => { throw new Error("Use Auth0 Universal Login"); };
  const value = useMemo<SessionValue>(() => ({
    user, loading: auth.isLoading || (auth.isAuthenticated && !user), authMode: "auth0",
    login: unsupported, register: unsupported,
    loginWithProvider: async () => auth.loginWithRedirect(),
    logout: () => auth.logout({ logoutParams: { returnTo: window.location.origin } }), getToken,
  }), [user, auth.isLoading, auth.isAuthenticated, getToken]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  if (authMode === "auth0") return (
    <Auth0Provider
      domain={import.meta.env.VITE_AUTH0_DOMAIN || ""}
      clientId={import.meta.env.VITE_AUTH0_CLIENT_ID || ""}
      authorizationParams={{ redirect_uri: window.location.origin, audience: import.meta.env.VITE_AUTH0_AUDIENCE }}
      cacheLocation="localstorage"
    ><Auth0Session>{children}</Auth0Session></Auth0Provider>
  );
  return <LocalSession>{children}</LocalSession>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

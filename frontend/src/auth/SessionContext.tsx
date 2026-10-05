import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { User } from "../types";

type AuthMode = "local" | "auth0" | "hybrid";
type SessionValue = {
  user: User | null; loading: boolean; authMode: AuthMode;
  login(email: string, password: string): Promise<void>;
  register(name: string, email: string, password: string): Promise<void>;
  loginWithProvider(): Promise<void>; logout(): void; getToken(): Promise<string | null>;
};

const SessionContext = createContext<SessionValue | null>(null);
const configuredMode: AuthMode = import.meta.env.VITE_AUTH_MODE === "auth0"
  ? "auth0"
  : import.meta.env.VITE_AUTH_MODE === "hybrid"
    ? "hybrid"
    : "local";

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
  const register = async (name: string, email: string, password: string) => { await api("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }); await login(email, password); };
  const logout = () => { localStorage.removeItem("access_token"); setToken(null); setUser(null); };
  const value = useMemo<SessionValue>(() => ({ user, loading, authMode: "local", login, register, loginWithProvider: async () => {}, logout, getToken: async () => token }), [user, loading, token]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

function Auth0Session({ children, allowLocal }: { children: ReactNode; allowLocal: boolean }) {
  const auth = useAuth0();
  const [auth0User, setAuth0User] = useState<User | null>(null);
  const [localToken, setLocalToken] = useState<string | null>(() => localStorage.getItem("access_token"));
  const [localUser, setLocalUser] = useState<User | null>(null);

  const getToken = useCallback(async (): Promise<string | null> => {
    if (auth.isAuthenticated) return (await auth.getAccessTokenSilently()) || null;
    return allowLocal ? localToken : null;
  }, [allowLocal, auth.isAuthenticated, auth.getAccessTokenSilently, localToken]);

  useEffect(() => {
    if (!auth.isAuthenticated) { setAuth0User(null); return; }
    getToken().then((token) => token ? api<User>("/auth/me", {}, token).then(setAuth0User) : undefined).catch(() => setAuth0User(null));
  }, [auth.isAuthenticated, getToken]);

  useEffect(() => {
    if (!allowLocal || !localToken || auth.isAuthenticated) return;
    api<User>("/auth/me", {}, localToken).then(setLocalUser).catch(() => {
      localStorage.removeItem("access_token"); setLocalToken(null); setLocalUser(null);
    });
  }, [allowLocal, auth.isAuthenticated, localToken]);

  const unsupported = async () => { throw new Error("Use Auth0 Universal Login"); };
  const login = async (email: string, password: string) => {
    if (!allowLocal) return unsupported();
    const result = await api<{ access_token: string; user: User }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    localStorage.setItem("access_token", result.access_token); setLocalToken(result.access_token); setLocalUser(result.user);
  };
  const register = async (name: string, email: string, password: string) => {
    if (!allowLocal) return unsupported();
    await api("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }); await login(email, password);
  };
  const logout = () => {
    localStorage.removeItem("access_token"); setLocalToken(null); setLocalUser(null); setAuth0User(null);
    if (auth.isAuthenticated) auth.logout({ logoutParams: { returnTo: window.location.origin } });
  };
  const user = auth0User || localUser;
  const loading = auth.isLoading || (auth.isAuthenticated && !auth0User) || (allowLocal && Boolean(localToken) && !localUser && !auth.isAuthenticated);
  const value = useMemo<SessionValue>(() => ({
    user, loading, authMode: allowLocal ? "hybrid" : "auth0", login, register,
    loginWithProvider: async () => auth.loginWithRedirect(), logout, getToken,
  }), [allowLocal, auth, getToken, loading, user]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  if (configuredMode !== "local") return (
    <Auth0Provider domain={import.meta.env.VITE_AUTH0_DOMAIN || ""} clientId={import.meta.env.VITE_AUTH0_CLIENT_ID || ""}
      authorizationParams={{ redirect_uri: window.location.origin, audience: import.meta.env.VITE_AUTH0_AUDIENCE }} cacheLocation="localstorage">
      <Auth0Session allowLocal={configuredMode === "hybrid"}>{children}</Auth0Session>
    </Auth0Provider>
  );
  return <LocalSession>{children}</LocalSession>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
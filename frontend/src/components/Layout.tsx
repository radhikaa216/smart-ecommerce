import { Bell, Menu, Package, ShoppingBag, UserRound, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { api, websocketUrl } from "../api";
import { useSession } from "../auth/SessionContext";
import type { AppNotification } from "../types";

type LiveEvent = { type?: string; title?: string; message?: string };

export default function Layout() {
  const { user, logout, getToken } = useSession();
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [toast, setToast] = useState<LiveEvent | null>(null);
  const toastTimer = useRef<number | undefined>(undefined);

  const refreshUnreadCount = useCallback(async () => {
    const token = await getToken();
    if (!token) { setUnreadCount(0); return; }
    const notifications = await api<AppNotification[]>("/notifications?unread_only=true", {}, token);
    setUnreadCount(notifications.length);
  }, [getToken]);

  useEffect(() => {
    const refresh = () => void refreshUnreadCount();
    window.addEventListener("smart-commerce:notification", refresh);
    return () => window.removeEventListener("smart-commerce:notification", refresh);
  }, [refreshUnreadCount]);

  useEffect(() => {
    if (!user) { setUnreadCount(0); return; }
    let socket: WebSocket | undefined;
    let reconnectTimer: number | undefined;
    let closed = false;

    const connect = async () => {
      try {
        const token = await getToken();
        if (!token || closed) return;
        socket = new WebSocket(websocketUrl(token));
        socket.onmessage = (event) => {
          const update = JSON.parse(event.data) as LiveEvent;
          if (update.type === "heartbeat") return;
          window.dispatchEvent(new CustomEvent("smart-commerce:notification"));
          if (update.title && update.message) {
            setToast(update);
            window.clearTimeout(toastTimer.current);
            toastTimer.current = window.setTimeout(() => setToast(null), 5000);
          }
        };
        socket.onerror = () => socket?.close();
        socket.onclose = () => {
          if (!closed) reconnectTimer = window.setTimeout(() => void connect(), 3000);
        };
      } catch {
        if (!closed) reconnectTimer = window.setTimeout(() => void connect(), 3000);
      }
    };

    void refreshUnreadCount();
    void connect();
    return () => {
      closed = true;
      window.clearTimeout(reconnectTimer);
      window.clearTimeout(toastTimer.current);
      socket?.close();
    };
  }, [getToken, refreshUnreadCount, user]);

  return <div className="app-shell">
    <header className="site-header">
      <Link to="/" className="brand" aria-label="Northstar Goods home"><span className="brand-mark">N</span><span>Northstar<small>GOODS</small></span></Link>
      <button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button>
      <nav className={open ? "main-nav open" : "main-nav"} onClick={() => setOpen(false)}>
        <NavLink to="/">Shop</NavLink>
        {user && <NavLink to="/orders"><Package size={18} /> Orders</NavLink>}
        {user && <NavLink to="/notifications" className="notification-link"><Bell size={18} /> Updates{unreadCount > 0 && <span className="notification-badge" aria-label={`${unreadCount} unread notifications`}>{unreadCount > 99 ? "99+" : unreadCount}</span>}</NavLink>}
        {user && <NavLink to="/cart"><ShoppingBag size={18} /> Cart</NavLink>}
        {user ? <button className="nav-user" onClick={logout}><UserRound size={18} /> {user.name}<small>Sign out</small></button> : <NavLink className="button small" to="/login">Sign in</NavLink>}
      </nav>
    </header>
    <main><Outlet /></main>
    {toast && <aside className="live-notification-toast" role="status"><Bell size={18}/><div><strong>{toast.title}</strong><span>{toast.message}</span></div><button onClick={() => setToast(null)} aria-label="Dismiss notification">x</button></aside>}
    <footer><div><strong>Northstar Goods</strong><p>A local production-style commerce demonstration.</p></div></footer>
  </div>;
}
import { BellRing, CheckCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useSession } from "../auth/SessionContext";
import type { AppNotification } from "../types";

export default function NotificationsPage() {
  const { getToken } = useSession();
  const [items, setItems] = useState<AppNotification[]>([]);
  const load = useCallback(async () => {
    const token = await getToken();
    setItems(await api<AppNotification[]>("/notifications", {}, token));
  }, [getToken]);

  useEffect(() => {
    void load();
    const refresh = () => void load();
    window.addEventListener("smart-commerce:notification", refresh);
    return () => window.removeEventListener("smart-commerce:notification", refresh);
  }, [load]);

  const allRead = async () => {
    const token = await getToken();
    await api("/notifications/read-all", { method: "POST" }, token);
    await load();
    window.dispatchEvent(new CustomEvent("smart-commerce:notification"));
  };

  return <section className="content-page narrow"><header className="page-heading split"><div><p className="eyebrow">Live updates</p><h1>Notifications</h1></div><button className="button subtle" onClick={allRead}><CheckCheck size={17}/> Mark all read</button></header>{items.length ? <div className="notification-list">{items.map(item => <article key={item.id} className={item.is_read ? "notification" : "notification unread"}><BellRing/><div><h3>{item.title}</h3><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString()}</small></div></article>)}</div> : <div className="empty-state"><BellRing size={42}/><h2>All quiet</h2><p>Order and payment updates will appear here.</p></div>}</section>;
}
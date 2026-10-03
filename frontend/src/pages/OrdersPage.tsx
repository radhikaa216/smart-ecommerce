import { PackageCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api, formatMoney } from "../api";
import { useSession } from "../auth/SessionContext";
import type { Order } from "../types";

export default function OrdersPage() {
  const { getToken } = useSession(); const [orders, setOrders] = useState<Order[]>();
  useEffect(() => { getToken().then(token => api<Order[]>("/orders", {}, token)).then(setOrders); }, [getToken]);
  if (!orders) return <div className="page-state">Loading order history…</div>;
  return <section className="content-page narrow"><header className="page-heading"><p className="eyebrow">Purchase history</p><h1>Your orders</h1><p>Payment and fulfillment progress in one place.</p></header>{orders.length ? <div className="order-list">{orders.map(order => <article className="order-card" key={order.order_number}><header><div><p>{new Date(order.created_at).toLocaleDateString()}</p><h2>{order.order_number}</h2></div><div className={`status ${order.order_status}`}>{order.order_status.replaceAll("_", " ")}</div></header><div className="order-items">{order.items.map(item => <div key={item.product_sku}><span>{item.quantity} × {item.product_name}</span><strong>{formatMoney(item.line_total, order.currency)}</strong></div>)}</div><footer><span>Payment: <strong>{order.payment_status}</strong></span><strong>{formatMoney(order.total, order.currency)}</strong></footer></article>)}</div> : <div className="empty-state"><PackageCheck size={44}/><h2>No orders yet</h2><p>Your completed checkouts will appear here.</p></div>}</section>;
}

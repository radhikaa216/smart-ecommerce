import { ArrowLeft, Check, Minus, Plus, ShieldCheck, Truck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, formatMoney } from "../api";
import { useSession } from "../auth/SessionContext";
import type { Product } from "../types";

export default function ProductPage() {
  const { slug = "" } = useParams(); const navigate = useNavigate();
  const { user, getToken } = useSession(); const [product, setProduct] = useState<Product>();
  const [quantity, setQuantity] = useState(1); const [status, setStatus] = useState("");
  useEffect(() => { api<Product>(`/products/${slug}`).then(setProduct).catch(() => navigate("/")); }, [slug, navigate]);
  if (!product) return <div className="page-state">Loading product…</div>;
  const add = async () => { if (!user) return navigate("/login", { state: { from: `/products/${slug}` } }); try { const token = await getToken(); await api("/cart/items", { method: "POST", body: JSON.stringify({ product_id: product.id, quantity }) }, token); setStatus("Added to cart"); } catch (error) { setStatus(error instanceof Error ? error.message : "Unable to add"); } };
  return <section className="detail-page"><Link to="/" className="back-link"><ArrowLeft size={17}/> Back to collection</Link><div className="detail-grid"><div className="detail-visual">{product.image_url ? <img src={product.image_url} alt={product.name}/> : <div className="product-placeholder large"><span>{product.category_name}</span><strong>{product.name.charAt(0)}</strong></div>}</div><div className="detail-copy"><p className="eyebrow">{product.category_name} · {product.sku}</p><h1>{product.name}</h1><p className="detail-price">{formatMoney(product.price, product.currency)}</p><p className="detail-description">{product.description}</p><div className="availability"><Check size={18}/>{product.stock ? `${product.stock} available` : "Currently unavailable"}</div><div className="buy-row"><div className="quantity"><button onClick={() => setQuantity(Math.max(1, quantity - 1))}><Minus size={16}/></button><strong>{quantity}</strong><button onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}><Plus size={16}/></button></div><button className="button primary grow" disabled={!product.stock} onClick={add}>Add to cart</button></div>{status && <p className="inline-status">{status}</p>}<div className="promise-grid"><div><Truck/><span><strong>Quick dispatch</strong>Prepared locally for demo</span></div><div><ShieldCheck/><span><strong>Secure test payment</strong>Powered by Stripe Checkout</span></div></div></div></div></section>;
}

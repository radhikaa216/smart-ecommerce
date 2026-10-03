import { Search, SlidersHorizontal, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../auth/SessionContext";
import ProductCard from "../components/ProductCard";
import type { Category, ProductPage } from "../types";

const emptyPage: ProductPage = { items: [], page: 1, page_size: 12, total: 0, pages: 0 };

export default function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState<ProductPage>(emptyPage);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState(params.get("q") || "");
  const { user, getToken } = useSession();
  const navigate = useNavigate();
  useEffect(() => { api<Category[]>("/categories").then(setCategories); }, []);
  useEffect(() => {
    setLoading(true);
    api<ProductPage>(`/products?${params.toString()}`).then(setProducts).finally(() => setLoading(false));
  }, [params]);
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); value ? next.set(key, value) : next.delete(key); next.delete("page"); setParams(next); };
  const submitSearch = (event: FormEvent) => { event.preventDefault(); update("q", search); };
  const add = async (productId: number) => {
    if (!user) { navigate("/login", { state: { from: "/" } }); return; }
    try { const token = await getToken(); await api("/cart/items", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: 1 }) }, token); setMessage("Added to your cart"); setTimeout(() => setMessage(""), 1800); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to add item"); }
  };
  return <>
    <section className="hero"><div className="hero-copy"><p className="eyebrow light"><Sparkles size={15} /> Thoughtfully selected essentials</p><h1>Useful things,<br/><em>beautifully considered.</em></h1><p>Technology, homeware and everyday carry chosen for longevity—not novelty.</p><a href="#catalog" className="button warm">Explore collection</a></div><div className="hero-art"><div className="orb one"></div><div className="orb two"></div><div className="hero-card"><span>CURATED / 2026</span><strong>06</strong><p>Everyday objects<br/>worth keeping.</p></div></div></section>
    <section className="catalog-section" id="catalog">
      <header className="section-heading"><div><p className="eyebrow">The collection</p><h2>Find your next favorite</h2></div><p>{products.total} carefully chosen products</p></header>
      <div className="catalog-tools"><form onSubmit={submitSearch}><Search size={19}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search products or SKU"/><button>Search</button></form><div className="filters"><SlidersHorizontal size={18}/><select value={params.get("category") || ""} onChange={e => update("category", e.target.value)}><option value="">All categories</option>{categories.map(item => <option value={item.slug} key={item.id}>{item.name}</option>)}</select><select value={params.get("sort") || "newest"} onChange={e => update("sort", e.target.value)}><option value="newest">Newest</option><option value="popularity">Most popular</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option></select></div></div>
      {message && <div className="toast">{message}</div>}
      {loading ? <div className="page-state">Curating the collection…</div> : products.items.length ? <div className="product-grid">{products.items.map(product => <ProductCard key={product.id} product={product} onAdd={add}/>)}</div> : <div className="empty-state"><h3>No products found</h3><p>Try changing your search or filters.</p></div>}
      {products.pages > 1 && <div className="pagination"><button disabled={products.page === 1} onClick={() => update("page", String(products.page - 1))}>Previous</button><span>Page {products.page} of {products.pages}</span><button disabled={products.page === products.pages} onClick={() => update("page", String(products.page + 1))}>Next</button></div>}
    </section>
  </>;
}

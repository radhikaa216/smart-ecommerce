import { ArrowUpRight, ShoppingBag } from "lucide-react";
import { Link } from "react-router-dom";
import { formatMoney } from "../api";
import type { Product } from "../types";

export default function ProductCard({ product, onAdd }: { product: Product; onAdd?: (id: number) => void }) {
  return <article className="product-card">
    <Link className="product-visual" to={`/products/${product.slug}`}>
      {product.image_url ? <img src={product.image_url} alt={product.name} /> : <div className="product-placeholder"><span>{product.category_name}</span><strong>{product.name.charAt(0)}</strong></div>}
      {product.stock <= 5 && product.stock > 0 && <span className="stock-badge">Only {product.stock} left</span>}
    </Link>
    <div className="product-copy"><p className="eyebrow">{product.category_name}</p><Link to={`/products/${product.slug}`}><h3>{product.name}</h3></Link><div className="product-row"><strong>{formatMoney(product.price, product.currency)}</strong>{onAdd ? <button disabled={!product.stock} onClick={() => onAdd(product.id)} aria-label={`Add ${product.name} to cart`}><ShoppingBag size={17} />{product.stock ? "Add" : "Sold out"}</button> : <ArrowUpRight />}</div></div>
  </article>;
}

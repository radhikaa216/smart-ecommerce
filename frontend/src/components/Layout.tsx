import { Bell, Menu, Package, ShoppingBag, UserRound, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useSession } from "../auth/SessionContext";

export default function Layout() {
  const { user, logout } = useSession();
  const [open, setOpen] = useState(false);
  return <div className="app-shell">
    <header className="site-header">
      <Link to="/" className="brand" aria-label="Northstar Goods home"><span className="brand-mark">N</span><span>Northstar<small>GOODS</small></span></Link>
      <button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle navigation">{open ? <X /> : <Menu />}</button>
      <nav className={open ? "main-nav open" : "main-nav"} onClick={() => setOpen(false)}>
        <NavLink to="/">Shop</NavLink>
        {user && <NavLink to="/orders"><Package size={18} /> Orders</NavLink>}
        {user && <NavLink to="/notifications"><Bell size={18} /> Updates</NavLink>}
        {user && <NavLink to="/cart"><ShoppingBag size={18} /> Cart</NavLink>}
        {user ? <button className="nav-user" onClick={logout}><UserRound size={18} /> {user.name}<small>Sign out</small></button> : <NavLink className="button small" to="/login">Sign in</NavLink>}
      </nav>
    </header>
    <main><Outlet /></main>
    <footer><div><strong>Northstar Goods</strong><p>A local production-style commerce demonstration.</p></div></footer>
  </div>;
}

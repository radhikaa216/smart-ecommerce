import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import CartPage from "./pages/CartPage";
import CatalogPage from "./pages/CatalogPage";
import CheckoutSuccessPage from "./pages/CheckoutSuccessPage";
import LoginPage from "./pages/LoginPage";
import NotificationsPage from "./pages/NotificationsPage";
import OrdersPage from "./pages/OrdersPage";
import ProductPage from "./pages/ProductPage";

const protectedPage = (node: React.ReactNode) => <ProtectedRoute>{node}</ProtectedRoute>;

export default function App() {
  return <BrowserRouter><Routes><Route element={<Layout/>}><Route index element={<CatalogPage/>}/><Route path="products/:slug" element={<ProductPage/>}/><Route path="login" element={<LoginPage/>}/><Route path="cart" element={protectedPage(<CartPage/>)}/><Route path="orders" element={protectedPage(<OrdersPage/>)}/><Route path="notifications" element={protectedPage(<NotificationsPage/>)}/><Route path="checkout/success" element={protectedPage(<CheckoutSuccessPage/>)}/><Route path="*" element={<CatalogPage/>}/></Route></Routes></BrowserRouter>;
}

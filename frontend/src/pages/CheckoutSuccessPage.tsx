import { CircleCheckBig } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../auth/SessionContext";

export default function CheckoutSuccessPage() {
  const [params] = useSearchParams();
  const { getToken } = useSession();
  const [status, setStatus] = useState("Confirming your order...");
  const completionStarted = useRef(false);
  const order = params.get("order");
  const isDemo = params.get("demo") === "1";

  useEffect(() => {
    if (!isDemo || !order) {
      setStatus("Payment received. Your order will update when Stripe confirms the webhook.");
      return;
    }
    if (completionStarted.current) return;
    completionStarted.current = true;
    getToken()
      .then(token => api(`/checkout/demo-complete/${order}`, { method: "POST" }, token))
      .then(() => setStatus("Your order is confirmed."))
      .catch(error => setStatus(error.message));
  }, [isDemo, order, getToken]);

  return <section className="success-page"><CircleCheckBig/><p className="eyebrow">Thank you</p><h1>Checkout complete</h1><p>{status}</p><div><Link className="button primary" to="/orders">View orders</Link><Link className="button subtle" to="/">Continue shopping</Link></div></section>;
}

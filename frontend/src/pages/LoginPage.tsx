import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useSession } from "../auth/SessionContext";

export default function LoginPage() {
  const { user, authMode, login, register, loginWithProvider } = useSession();
  const [creating, setCreating] = useState(false); const [name, setName] = useState("");
  const [email, setEmail] = useState("customer@example.com"); const [password, setPassword] = useState("customer123");
  const [error, setError] = useState(""); const navigate = useNavigate(); const location = useLocation();
  const destination = (location.state as { from?: string } | null)?.from || "/";
  if (user) return <Navigate to={destination} replace/>;
  const submit = async (event: FormEvent) => { event.preventDefault(); setError(""); try { creating ? await register(name, email, password) : await login(email, password); navigate(destination); } catch (err) { setError(err instanceof Error ? err.message : "Authentication failed"); } };
  return <section className="auth-page"><div className="auth-story"><p className="eyebrow light">Member access</p><h1>Your collection,<br/><em>kept together.</em></h1><p>Save a cart, follow every order, and receive live updates.</p></div><div className="auth-card">{authMode === "auth0" ? <><p className="eyebrow">Secure sign in</p><h2>Continue to Northstar</h2><p>Use email, Google, or Facebook through Auth0 Universal Login.</p><button className="button primary full" onClick={loginWithProvider}>Continue with Auth0</button></> : <><p className="eyebrow">{creating ? "Create account" : "Welcome back"}</p><h2>{creating ? "Join Northstar" : "Sign in"}</h2><form onSubmit={submit}>{creating && <label>Name<input required minLength={2} value={name} onChange={e => setName(e.target.value)}/></label>}<label>Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)}/></label><label>Password<input required minLength={8} type="password" value={password} onChange={e => setPassword(e.target.value)}/></label>{error && <p className="form-error">{error}</p>}<button className="button primary full">{creating ? "Create account" : "Sign in"}</button></form><button className="text-button" onClick={() => setCreating(!creating)}>{creating ? "Already registered? Sign in" : "New here? Create an account"}</button><p className="demo-note">Demo: customer@example.com / customer123</p></>}</div></section>;
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, token } from "../api";
import { Seal } from "../Seal";

export function Login() {
  const [email, setEmail] = useState("analyst@wekil.app");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await api<{ token: string }>("/api/login", { method: "POST", json: { email, password } });
      token.set(r.token);
      nav("/");
    } catch (err) { setError((err as Error).message); }
  }

  return (
    <main className="login">
      <Seal tier="low" size={148} />
      <h1>Wekil compliance desk</h1>
      <p className="muted">Merchant onboarding and monitoring for the payment gateway.</p>
      <form onSubmit={submit} className="form">
        <label>Work email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn--primary">Sign in</button>
      </form>
    </main>
  );
}

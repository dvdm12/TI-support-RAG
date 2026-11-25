import { useState } from "react";
import Brand from "../ui/Brand.jsx";

export default function Login({ onSignIn, configured }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await onSignIn(email, password);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <form className="login-card" onSubmit={submit} aria-labelledby="login-title">
        <Brand />
        <h1 id="login-title">Inicia sesión</h1>
        <p className="login-lead">
          Usa tu cuenta de Supabase. Tus conversaciones se guardan y solo tú
          puedes verlas.
        </p>
        {!configured ? (
          <p className="login-error" role="alert">
            Falta configurar Supabase: define SUPABASE_URL y
            SUPABASE_PUBLISHABLE_KEY (ver frontend/.env.example).
          </p>
        ) : (
          <>
            <label>
              Correo electrónico
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Contraseña
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {error && (
              <p className="login-error" role="alert">
                {error}
              </p>
            )}
            <button className="login-submit" type="submit" disabled={busy}>
              {busy ? "Entrando…" : "Entrar"}
            </button>
          </>
        )}
      </form>
    </main>
  );
}

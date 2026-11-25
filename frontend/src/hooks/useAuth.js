import { useEffect, useState } from "react";
import { supabase, supabaseConfigurado } from "../services/supabase.js";

export function useAuth() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(supabaseConfigurado);

  useEffect(() => {
    if (!supabase) return undefined;
    let activo = true;
    supabase.auth.getSession().then(({ data }) => {
      if (activo) {
        setSession(data.session);
        setLoading(false);
      }
    });
    const { data } = supabase.auth.onAuthStateChange((_event, nueva) => {
      setSession(nueva);
    });
    return () => {
      activo = false;
      data.subscription.unsubscribe();
    };
  }, []);

  async function signIn(email, password) {
    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (error)
      throw new Error(
        error.status === 400
          ? "Correo o contraseña incorrectos."
          : "No se pudo iniciar sesión. Inténtalo de nuevo.",
      );
  }

  async function signOut() {
    await supabase.auth.signOut();
  }

  return {
    configured: supabaseConfigurado,
    loading,
    session,
    user: session?.user ?? null,
    signIn,
    signOut,
  };
}

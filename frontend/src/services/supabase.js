import { createClient } from "@supabase/supabase-js";

// Solo la URL del proyecto y la clave publishable llegan al navegador: son
// públicas por diseño y RLS protege los datos de cada usuario. El token del
// backend Django sigue fuera del navegador (lo añade el proxy de Vite).
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

export const supabaseConfigurado = Boolean(url && key);

export const supabase = supabaseConfigurado
  ? createClient(url, key, {
      auth: {
        // La sesión vive en esta pestaña: sobrevive a recargar, no a cerrarla.
        storage: window.sessionStorage,
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
      },
    })
  : null;

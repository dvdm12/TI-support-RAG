// Tickets de demostración en Supabase (tabla public.tickets).
// Lectura: cualquiera. Escritura: cualquier usuario con sesión (RLS); el
// servidor fija actualizado_en/actualizado_por. El cliente solo envía estado y detalle.

export const ESTADOS = [
  "Abierto",
  "Asignado",
  "En revisión",
  "Pendiente de información",
  "Pendiente de aprobación",
  "Escalado",
  "Resuelto",
  "Cerrado",
];

export const DETALLE_MAX = 500;
const COLUMNAS = "codigo, estado, detalle, actualizado_en";

export class TicketsError extends Error {}

export async function listarTickets(client) {
  const { data, error } = await client.from("tickets").select(COLUMNAS).order("codigo");
  if (error) throw new TicketsError("No se pudieron cargar los tickets.");
  return data ?? [];
}

export function validarCambios({ estado, detalle }) {
  const limpio = (detalle ?? "").trim();
  if (!ESTADOS.includes(estado)) return "Elige un estado válido.";
  if (!limpio) return "El detalle no puede quedar vacío.";
  if (limpio.length > DETALLE_MAX) return `El detalle admite hasta ${DETALLE_MAX} caracteres.`;
  return "";
}

export async function actualizarTicket(client, codigo, cambios) {
  const problema = validarCambios(cambios);
  if (problema) throw new TicketsError(problema);
  const { data, error } = await client
    .from("tickets")
    .update({ estado: cambios.estado, detalle: cambios.detalle.trim() })
    .eq("codigo", codigo)
    .select(COLUMNAS);
  if (error) throw new TicketsError("No se pudo guardar el ticket.");
  // RLS no da error al bloquear un UPDATE: simplemente no afecta filas.
  if (!data?.length) throw new TicketsError("No se pudo modificar el ticket. Vuelve a iniciar sesión.");
  return data[0];
}

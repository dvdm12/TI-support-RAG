// Historial de conversaciones en Supabase (tablas `conversaciones` y `mensajes`).
// Son las mismas tablas y políticas RLS que usa la app Gradio (app/almacenamiento.py):
// cada operación se hace con la sesión del usuario y RLS limita el acceso a sus filas.
// Las funciones reciben el cliente para poder probarlas sin red.

const TITULO_MAX = 200;
const CONTENIDO_MAX = 20000;

export class HistorialError extends Error {
  constructor(message) {
    super(message);
    this.name = "HistorialError";
  }
}

export function tituloDesde(texto) {
  const limpio = String(texto ?? "").replace(/\s+/g, " ").trim();
  if (!limpio) return "Nueva consulta";
  return limpio.length > TITULO_MAX
    ? `${limpio.slice(0, TITULO_MAX - 1)}…`
    : limpio;
}

function recortar(texto) {
  const limpio = String(texto ?? "").trim();
  return limpio.slice(0, CONTENIDO_MAX);
}

// Texto visible de una respuesta de la API (igual que Message.jsx).
export function textoRespuesta(data) {
  if (!data) return "";
  const documental = data.respuesta_documental?.respuesta;
  if (documental) return documental;
  if (data.respuesta) return data.respuesta;
  if (data.pasajes)
    return data.pasajes.length
      ? "Encontré estos pasajes en los manuales de soporte. Abre cada referencia para consultar su contenido."
      : "No se encontraron pasajes para esta consulta. Prueba con el equipo, servicio o mensaje de error específico.";
  return "";
}

export function fuentesRespuesta(data) {
  const fuentes = data?.fuentes || data?.pasajes || [];
  return Array.isArray(fuentes) ? fuentes : [];
}

export async function listarConversaciones(client) {
  const { data, error } = await client
    .from("conversaciones")
    .select("id, titulo, actualizada_en")
    .order("actualizada_en", { ascending: false });
  if (error) throw new HistorialError("No se pudieron cargar tus conversaciones.");
  return data || [];
}

export async function crearConversacion(client, titulo) {
  // usuario_id lo pone la base de datos (DEFAULT auth.uid()).
  const { data, error } = await client
    .from("conversaciones")
    .insert({ titulo: tituloDesde(titulo) })
    .select("id, titulo, actualizada_en")
    .single();
  if (error || !data) throw new HistorialError("No se pudo crear la conversación.");
  return data;
}

// Ordena por creado_en. Los dos mensajes de un turno se insertan juntos y
// comparten marca de tiempo (now() de la transacción): a igual hora, la
// pregunta del usuario va antes que la respuesta.
export function ordenarFilas(filas) {
  const peso = (rol) => (rol === "usuario" ? 0 : 1);
  return [...filas].sort(
    (a, b) =>
      String(a.creado_en).localeCompare(String(b.creado_en)) ||
      peso(a.rol) - peso(b.rol),
  );
}

export function aMensajesUI(filas) {
  return ordenarFilas(filas).map((fila) =>
    fila.rol === "usuario"
      ? { id: fila.id, role: "user", content: fila.contenido, stored: true }
      : {
          id: fila.id,
          role: "assistant",
          status: "done",
          stored: true,
          data: {
            respuesta: fila.contenido,
            fuentes: Array.isArray(fila.fuentes) ? fila.fuentes : [],
          },
        },
  );
}

export async function cargarMensajes(client, conversacionId) {
  const { data, error } = await client
    .from("mensajes")
    .select("id, rol, contenido, fuentes, creado_en")
    .eq("conversacion_id", conversacionId)
    .order("creado_en", { ascending: true });
  if (error) throw new HistorialError("No se pudieron cargar los mensajes.");
  return aMensajesUI(data || []);
}

export async function guardarTurno(client, conversacionId, pregunta, data) {
  const respuesta = recortar(textoRespuesta(data)) || "(respuesta sin texto)";
  const filas = [
    { conversacion_id: conversacionId, rol: "usuario", contenido: recortar(pregunta), fuentes: [] },
    { conversacion_id: conversacionId, rol: "asistente", contenido: respuesta, fuentes: fuentesRespuesta(data) },
  ];
  const { error } = await client.from("mensajes").insert(filas);
  if (error) throw new HistorialError("No se pudo guardar el turno en tu historial.");
}

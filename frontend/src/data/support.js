export const categories = [
  { id: "redes", label: "Redes" },
  { id: "hardware", label: "Hardware" },
  { id: "software", label: "Software" },
  { id: "cuentas", label: "Cuentas" },
  { id: "seguridad", label: "Seguridad" },
  { id: "acceso", label: "Acceso" },
  { id: "otros", label: "Otros" },
];

export const suggestions = [
  {
    label: "Problemas de conexión",
    description: "Wi-Fi, red e Internet",
    prompt:
      "No puedo conectarme al Wi-Fi. ¿Qué comprobaciones indica el manual?",
  },
  {
    label: "Mi equipo no responde",
    description: "Equipos y periféricos",
    prompt: "Mi equipo no enciende. ¿Qué puedo comprobar de forma segura?",
  },
  {
    label: "Recuperar mi acceso",
    description: "Cuentas y contraseñas",
    prompt:
      "No puedo acceder a mi cuenta. ¿Qué información necesita soporte para ayudarme?",
  },
  {
    label: "Detectar un mensaje sospechoso",
    description: "Seguridad y buenas prácticas",
    prompt:
      "Recibí un correo con un enlace sospechoso y no lo he abierto. ¿Qué debo hacer?",
  },
];

// Texto legible para un estado sin etiqueta: nunca se muestra el código interno.
export function stateLabel(state) {
  if (!state) return "";
  if (stateLabels[state]) return stateLabels[state];
  const text = state.replace(/^OK_/, "").replaceAll("_", " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const stateLabels = {
  OK_VALIDADO: "Validación automática superada",
  OK_PIDE_ACLARACION: "Necesito más información",
  OK_REQUIERE_HUMANO: "Requiere soporte humano",
  OK_RESPUESTA_DIRECTA: "Respuesta directa",
  OK_TICKET_CONSULTADO: "Ticket consultado",
  TICKET_NO_ENCONTRADO: "Ticket no encontrado",
  OPERACION_NO_PERMITIDA: "Operación no permitida",
  OK_TICKETS_LISTADOS: "Tickets listados",
  OK_SOLICITUD_HUMANO: "Derivación a soporte humano",
  OK_RESPUESTA_PARCIAL: "Respuesta parcial",
  OK_EVIDENCIA_INSUFICIENTE: "Evidencia insuficiente",
  ERROR_TECNICO: "Error técnico",
  ERROR_FORMATO: "Respuesta no válida",
  respondida: "Respuesta documental",
  parcial: "Respuesta parcial",
  aclaracion: "Por aclarar",
  evidencia_insuficiente: "Evidencia insuficiente",
};

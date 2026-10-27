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

export const stateLabels = {
  OK_VALIDADO: "Validación automática superada",
  OK_PIDE_ACLARACION: "Necesito más información",
  OK_REQUIERE_HUMANO: "Requiere soporte humano",
  respondida: "Respuesta documental",
  parcial: "Respuesta parcial",
  aclaracion: "Por aclarar",
  evidencia_insuficiente: "Evidencia insuficiente",
};

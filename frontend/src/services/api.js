export class ApiError extends Error {
  constructor(
    message,
    { status = 0, code = "network_error", requestId, retryAfter } = {},
  ) {
    super(message);
    this.name = "ApiError";
    Object.assign(this, { status, code, requestId, retryAfter });
  }
}

const messages = {
  unauthorized:
    "No pudimos autenticar la conexión. Revisa DJANGO_API_TOKEN en el servidor local.",
  api_not_configured: "El servidor necesita configurar su token de acceso.",
  input_too_large:
    "La consulta es demasiado larga. Resume el equipo afectado y el síntoma principal.",
  provider_rate_limited:
    "El proveedor alcanzó su cuota. Espera antes de volver a consultar.",
  service_busy:
    "El asistente está atendiendo otra solicitud. Espera un momento y vuelve a intentarlo.",
  service_unavailable:
    "El servicio no está disponible en este momento. Inténtalo más tarde.",
  invalid_provider_response:
    "La respuesta no superó las comprobaciones automáticas. Puedes volver a consultar.",
  invalid_input:
    "Revisa la consulta: debe contener texto y respetar los límites de entrada.",
};

export async function request(path, { body, signal, fetcher = fetch } = {}) {
  let response;
  try {
    response = await fetcher(`/api/v1/${path}`, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : {},
      ...(body ? { body: JSON.stringify(body) } : {}),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      "No pudimos conectar con la API. Comprueba que Django y el proxy local estén activos.",
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      "El servidor devolvió una respuesta inesperada. Comprueba la conexión con Django.",
      { status: response.status, code: "invalid_response" },
    );
  }
  if (!response.ok) {
    const code = data.error?.code || "unknown_error";
    throw new ApiError(
      messages[code] || "No se pudo completar la consulta. Inténtalo de nuevo.",
      {
        status: response.status,
        code,
        requestId: data.request_id,
        retryAfter: response.headers.get("Retry-After"),
      },
    );
  }
  return data;
}

export const getHealth = (signal) => request("health/", { signal });
export const querySupport = (question, signal) =>
  request("rag/query/", { body: { pregunta: question }, signal });
export const searchManuals = (question, category, signal) =>
  request("rag/search/", {
    body: { pregunta: question, ...(category ? { categoria: category } : {}) },
    signal,
  });

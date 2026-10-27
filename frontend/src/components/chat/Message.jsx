import { AlertCircle, BookOpen, Check, Copy, RotateCcw } from "../ui/Icons.jsx";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import Brand from "../ui/Brand.jsx";
import IconButton from "../ui/IconButton.jsx";
import Sources from "./Sources.jsx";
import { stateLabels } from "../../data/support.js";

export default function Message({ message, onRetry, pending }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  if (message.role === "user")
    return (
      <article className="message message--user">
        <div className="user-bubble">{message.content}</div>
        <span className="message-user-avatar">TÚ</span>
      </article>
    );
  const { data, status, error } = message;
  const documentary = data?.respuesta_documental;
  const sources = data?.fuentes || data?.pasajes || [];
  const content =
    documentary?.respuesta ||
    (data?.pasajes
      ? data.pasajes.length
        ? "Encontré estos pasajes en los manuales de soporte. Abre cada referencia para consultar su contenido."
        : "No se encontraron pasajes para esta consulta. Prueba con el equipo, servicio o mensaje de error específico."
      : "");
  const markdown = content.replace(
    /\[(F\d+)\]/g,
    (_, id) => `[${id}](#source-${message.id}-${id})`,
  );
  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  }
  return (
    <article className="message message--assistant">
      <Brand compact />
      <div className="assistant-content">
        <div className="assistant-label">
          TI Support<span>ASISTENTE</span>
        </div>
        {status === "loading" && (
          <div className="thinking" role="status">
            <span>
              <i />
              <i />
              <i />
            </span>
            {message.mode === "search"
              ? "Consultando los manuales…"
              : "Analizando tu consulta y buscando respaldo documental…"}
            <small>
              La consulta puede tardar mientras el proveedor está ocupado.
            </small>
          </div>
        )}
        {status === "cancelled" && (
          <div className="message-notice">
            Dejaste de esperar esta respuesta. El servidor puede seguir
            procesándola.
            <button onClick={onRetry} disabled={pending}>
              Volver a consultar
            </button>
          </div>
        )}
        {status === "error" && (
          <div className="error-message" role="alert">
            <AlertCircle size={18} />
            <div>
              <strong>No pudimos completar la consulta</strong>
              <p>{error.message}</p>
              {error.retryAfter && (
                <small>Reintenta después de {error.retryAfter} segundos.</small>
              )}
              {error.requestId && <small>Referencia: {error.requestId}</small>}
              <button onClick={onRetry} disabled={pending}>
                <RotateCcw size={13} />
                Volver a intentar
              </button>
            </div>
          </div>
        )}
        {status === "done" && (
          <>
            <div className="response-badges">
              {data.estado && (
                <span
                  className={`response-state response-state--${data.estado}`}
                >
                  <Check size={12} />
                  {stateLabels[data.estado] || data.estado}
                </span>
              )}
              {documentary && <span>{stateLabels[documentary.estado]}</span>}
              {data.clasificacion && (
                <span>
                  {data.clasificacion.categoria} · prioridad{" "}
                  {data.clasificacion.prioridad}
                </span>
              )}
            </div>
            <div className="markdown">
              <ReactMarkdown
                skipHtml
                components={{
                  img: ({ alt }) => (alt ? <span>{alt}</span> : null),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      {...(href?.startsWith("#source-")
                        ? {
                            onClick: () => {
                              const target = document.getElementById(
                                href.slice(1),
                              );
                              if (target) target.open = true;
                            },
                          }
                        : { target: "_blank", rel: "noopener noreferrer" })}
                    >
                      {children}
                    </a>
                  ),
                }}
              >
                {markdown}
              </ReactMarkdown>
            </div>
            {documentary?.limitacion && (
              <div className="limitation">
                <AlertCircle size={15} />
                <p>{documentary.limitacion}</p>
              </div>
            )}
            {!!data.clasificacion?.datos_faltantes?.length && (
              <div className="missing-info">
                <strong>Para orientar mejor tu caso</strong>
                <ul>
                  {data.clasificacion.datos_faltantes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {!!sources.length && (
              <div className="message-sources">
                <div className="sources-label">
                  <BookOpen size={13} />
                  {message.mode === "search"
                    ? "PASAJES RECUPERADOS"
                    : "FUENTES CITADAS"}
                  <span>{sources.length}</span>
                </div>
                <Sources sources={sources} messageId={message.id} />
              </div>
            )}
            <div className="message-actions">
              <IconButton
                label={copied ? "Respuesta copiada" : "Copiar respuesta"}
                onClick={copy}
              >
                {copied ? <Check size={15} /> : <Copy size={15} />}
              </IconButton>
              <IconButton
                label="Volver a consultar"
                onClick={onRetry}
                disabled={pending}
              >
                <RotateCcw size={14} />
              </IconButton>
              {copyError && (
                <small>No se pudo copiar. Puedes seleccionar el texto.</small>
              )}
              {data.latencia_segundos != null && (
                <span>{data.latencia_segundos.toFixed(1)} s · pipeline</span>
              )}
            </div>
          </>
        )}
      </div>
    </article>
  );
}

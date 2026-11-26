import { useState } from "react";
import Sources from "./components/chat/Sources.jsx";
import ServiceStatus from "./components/ui/ServiceStatus.jsx";
import { stateLabel } from "./data/support.js";
import { useHealth } from "./hooks/useHealth.js";
import { querySupport } from "./services/api.js";
import "./styles/router-demo.css";

const routes = [
  ["respuesta_directa", "Respuesta directa", "¿Qué puedes hacer?"],
  ["consulta_documental", "Consulta documental", "¿Qué requisitos exige el manual de software para instalar una aplicación?"],
  ["consulta_ticket", "Consulta de ticket", "¿Cómo va el ticket TI-1001?"],
  ["aclaracion", "Aclaración", "¿Cómo va mi ticket?"],
  ["operacion_prohibida", "Operación prohibida", "Cierra el ticket TI-1001"],
  ["listar_tickets", "Listar tickets", "¿Qué tickets hay disponibles?"],
  ["solicitud_humano", "Atención humana", "¿Puedes escalar a un humano?"],
];

export default function RouterDemo() {
  const { status } = useHealth();
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState(null);

  async function send(value) {
    const query = value.trim();
    if (!query || pending) return;
    setQuestion(query);
    setPending(true);
    setResult(null);
    try {
      const data = await querySupport(query);
      setResult({ data, trace: data.traza, requestId: data.request_id });
    } catch (error) {
      setResult({ error, trace: error.trace, requestId: error.requestId });
    } finally {
      setPending(false);
    }
  }

  const trace = result?.trace;
  const data = result?.data;
  const answer = data?.respuesta ?? data?.respuesta_documental?.respuesta;
  const statusLabel = stateLabel(data?.estado);
  const selectedRoute = routes.find(([route]) => route === trace?.ruta)?.[1];

  return (
    <main className="router-demo">
      <header className="router-demo-header">
        <a href="/">← Chat de soporte</a>
        <ServiceStatus status={status} />
      </header>

      <div className="router-demo-intro">
        <h1>Enrutador de soporte TI</h1>
        <p>Envía una pregunta y observa cómo Django decide qué hacer.</p>
      </div>

      <div className="router-demo-grid">
        <section className="router-demo-panel" aria-labelledby="router-query-heading">
          <h2 id="router-query-heading">Consulta</h2>
          <form onSubmit={(event) => { event.preventDefault(); send(question); }}>
            <label htmlFor="router-question">Pregunta de soporte</label>
            <textarea
              id="router-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={4}
              maxLength={8000}
              disabled={pending}
            />
            <button className="router-demo-send" disabled={pending || !question.trim()}>
              {pending ? "Ejecutando…" : "Ejecutar consulta"}
            </button>
          </form>

          <div className="router-demo-report" aria-live="polite" aria-busy={pending}>
            {pending && <p role="status">Esperando respuesta de Django…</p>}
            {result && (
              <>
                <h2>Resultado de la consulta</h2>
                <dl className="router-demo-summary">
                  <div><dt>Ruta elegida</dt><dd>{selectedRoute ?? "Sin ruta"}</dd></div>
                  <div><dt>Salida</dt><dd>{statusLabel ?? "Error de consulta"}</dd></div>
                  {trace && (
                    <>
                      <div><dt>Operación</dt><dd><code>{trace.operacion ?? "Ninguna"}</code></dd></div>
                      <div><dt>Resultado de Django</dt><dd><code>{trace.resultado}</code></dd></div>
                      <div><dt>Motivo de salida</dt><dd><code>{trace.motivo_salida}</code></dd></div>
                    </>
                  )}
                  {result.requestId && <div><dt>Solicitud</dt><dd><code>{result.requestId}</code></dd></div>}
                </dl>
                {!trace && <p className="router-demo-muted">La API no devolvió una traza para esta consulta.</p>}
              </>
            )}
            {result?.error && <p role="alert">{result.error.message} {result.error.status > 0 && `(HTTP ${result.error.status})`}</p>}
            {answer && (
              <div className="router-demo-answer">
                <h3>Respuesta</h3>
                <p>{answer}</p>
                {data.respuesta_documental?.limitacion && <p className="router-demo-muted">{data.respuesta_documental.limitacion}</p>}
                <Sources sources={data.fuentes} messageId={data.request_id} />
              </div>
            )}
          </div>
        </section>

        <section className="router-demo-panel" aria-labelledby="router-trace-heading">
          <h2 id="router-trace-heading">Casos de prueba</h2>
          <ul className="router-demo-routes">
            {routes.map(([route, label, example]) => (
              <li key={route}>
                <button
                  type="button"
                  data-active={trace?.ruta === route}
                  aria-current={trace?.ruta === route ? "true" : undefined}
                  title={example}
                  disabled={pending}
                  onClick={() => send(example)}
                >
                  <span className="router-demo-case"><strong>{label}</strong><small>{example}</small></span>
                  {trace?.ruta === route ? <span className="router-demo-selected">Ruta elegida</span> : <span aria-hidden="true">↗</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}

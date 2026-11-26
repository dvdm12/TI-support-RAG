import { useEffect, useState } from "react";
import { RefreshCw } from "../ui/Icons.jsx";
import {
  DETALLE_MAX,
  ESTADOS,
  actualizarTicket,
  listarTickets,
  validarCambios,
} from "../../services/tickets.js";

const fecha = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "short",
});

function TicketRow({ ticket, onSave }) {
  const [estado, setEstado] = useState(ticket.estado);
  const [detalle, setDetalle] = useState(ticket.detalle);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    setEstado(ticket.estado);
    setDetalle(ticket.detalle);
  }, [ticket]);

  const dirty = estado !== ticket.estado || detalle.trim() !== ticket.detalle;
  const problema = dirty ? validarCambios({ estado, detalle }) : "";

  async function save(event) {
    event.preventDefault();
    if (!dirty || problema || saving) return;
    setSaving(true);
    setMessage(null);
    try {
      await onSave(ticket.codigo, { estado, detalle });
      setMessage({ ok: true, text: "Guardado." });
    } catch (error) {
      setMessage({ ok: false, text: error.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ticket-card" onSubmit={save} aria-label={`Ticket ${ticket.codigo}`}>
      <div className="ticket-head">
        <strong>{ticket.codigo}</strong>
        <span className="ticket-date">
          Actualizado {fecha.format(new Date(ticket.actualizado_en))}
        </span>
      </div>
      <label>
        Estado
        <select value={estado} onChange={(event) => setEstado(event.target.value)}>
          {ESTADOS.map((opcion) => (
            <option key={opcion}>{opcion}</option>
          ))}
        </select>
      </label>
      <label>
        Detalle
        <textarea
          rows={2}
          maxLength={DETALLE_MAX}
          value={detalle}
          onChange={(event) => setDetalle(event.target.value)}
        />
      </label>
      <div className="ticket-actions">
        {(problema || message) && (
          <span
            className={problema || !message.ok ? "ticket-error" : "ticket-ok"}
            role={problema || !message.ok ? "alert" : "status"}
          >
            {problema || message.text}
          </span>
        )}
        {dirty && (
          <button
            type="button"
            className="ticket-secondary"
            onClick={() => {
              setEstado(ticket.estado);
              setDetalle(ticket.detalle);
              setMessage(null);
            }}
            disabled={saving}
          >
            Descartar
          </button>
        )}
        <button type="submit" className="ticket-save" disabled={!dirty || !!problema || saving}>
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </form>
  );
}

export default function SupportTickets({ client }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      setTickets(await listarTickets(client));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  async function save(codigo, cambios) {
    const actualizado = await actualizarTicket(client, codigo, cambios);
    setTickets((current) =>
      current.map((ticket) => (ticket.codigo === codigo ? actualizado : ticket)),
    );
    setNotice(`${codigo} guardado: ${actualizado.estado}.`);
  }

  const visibles = filter ? tickets.filter((ticket) => ticket.estado === filter) : tickets;

  return (
    <main id="main" className="support-main">
      <div className="support-inner">
        <div className="support-top">
          <div>
            <h1>Tickets</h1>
            <p>
              Gestión de los tickets de demostración. Los cambios de estado se
              reflejan al consultar el ticket desde el chat.
            </p>
          </div>
          <div className="support-tools">
            <select
              aria-label="Filtrar por estado"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            >
              <option value="">Todos los estados</option>
              {ESTADOS.map((opcion) => (
                <option key={opcion}>{opcion}</option>
              ))}
            </select>
            <button className="ticket-secondary" onClick={load} disabled={loading}>
              <RefreshCw size={15} /> Recargar
            </button>
          </div>
        </div>
        {notice && (
          <p className="ticket-ok" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="login-error" role="alert">
            {error}
          </p>
        )}
        {loading ? (
          <p className="support-empty">Cargando tickets…</p>
        ) : visibles.length ? (
          <div className="ticket-list">
            {visibles.map((ticket) => (
              <TicketRow key={ticket.codigo} ticket={ticket} onSave={save} />
            ))}
          </div>
        ) : (
          !error && <p className="support-empty">No hay tickets con ese estado.</p>
        )}
      </div>
    </main>
  );
}

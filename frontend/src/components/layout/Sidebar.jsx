import {
  BookOpen,
  Compose,
  MessageSquare,
  Search,
  Settings2,
  X,
} from "../ui/Icons.jsx";
import Brand from "../ui/Brand.jsx";
import IconButton from "../ui/IconButton.jsx";
import { useRef, useState } from "react";

export default function Sidebar({
  chats,
  activeId,
  pending,
  onNew,
  onSelect,
  mode,
  onMode,
  onSettings,
  open,
  onClose,
  user,
  loadingHistory,
  historyError,
}) {
  const [filter, setFilter] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchInput = useRef(null);
  const saved = chats.filter((chat) => chat.convId || chat.messages.length);
  const recent = saved.filter((chat) =>
    chat.title.toLowerCase().includes(filter.toLowerCase()),
  );
  function toggleSearch() {
    setSearchOpen((value) => !value);
    setFilter("");
    requestAnimationFrame(() => searchInput.current?.focus());
  }
  return (
    <>
      {open && (
        <button
          className="sidebar-backdrop"
          aria-label="Cerrar navegación"
          onClick={onClose}
        />
      )}
      <aside
        className={`sidebar ${open ? "sidebar--open" : ""}`}
        aria-label="Navegación principal"
      >
        <div className="sidebar-brand">
          <Brand />
          <div>
            <IconButton
              label="Buscar en consultas"
              aria-expanded={searchOpen}
              onClick={toggleSearch}
            >
              <Search size={17} />
            </IconButton>
            <IconButton
              label="Cerrar navegación"
              className="mobile-only"
              onClick={onClose}
            >
              <X size={17} />
            </IconButton>
          </div>
        </div>
        <button className="new-chat" onClick={onNew} disabled={pending}>
          <Compose size={17} />
          <span>Nueva consulta</span>
          <kbd>↗</kbd>
        </button>
        <nav className="main-nav" aria-label="Herramientas">
          <button
            className={mode === "query" ? "active" : ""}
            onClick={() => onMode("query")}
            disabled={pending}
          >
            <MessageSquare size={16} />
            Chat de soporte
          </button>
          <button
            className={mode === "search" ? "active" : ""}
            onClick={() => onMode("search")}
            disabled={pending}
          >
            <BookOpen size={16} />
            Manuales
          </button>
        </nav>
        <div className="history-heading">
          <span>Consultas</span>
          <span>
            {saved.length || ""}
          </span>
        </div>
        {searchOpen && (
          <label className="history-search">
            <Search size={14} />
            <input
              ref={searchInput}
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="Buscar consulta…"
              aria-label="Buscar consulta reciente"
            />
          </label>
        )}
        {historyError && (
          <p className="history-error" role="alert">
            {historyError}
          </p>
        )}
        <div className="history-list">
          {recent.length ? (
            recent.map((chat) => (
              <button
                className={`history-item ${chat.id === activeId ? "active" : ""}`}
                key={chat.id}
                onClick={() => onSelect(chat.id)}
                disabled={pending}
              >
                <span>{chat.title}</span>
              </button>
            ))
          ) : (
            <p className="empty-history">
              {loadingHistory
                ? "Cargando tus conversaciones…"
                : filter
                  ? "No hay coincidencias."
                  : "Tus consultas aparecerán aquí."}
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <p className="session-hint">
            Historial guardado en Supabase.
            <br />
            Solo tú puedes verlo.
          </p>
          <button className="session-button" onClick={onSettings}>
            <span className="avatar">
              {(user?.email || "tú").slice(0, 2).toLowerCase()}
            </span>
            <span className="session-email" title={user?.email}>
              {user?.email || "Sesión"}
            </span>
            <Settings2 size={16} />
          </button>
        </div>
      </aside>
    </>
  );
}

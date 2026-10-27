import { ArrowUp, Square } from "../ui/Icons.jsx";
import { useEffect, useRef } from "react";
import { categories } from "../../data/support.js";

export default function Composer({
  value,
  onChange,
  onSubmit,
  pending,
  onCancel,
  mode,
  onMode,
  category,
  onCategory,
}) {
  const input = useRef(null);
  useEffect(() => {
    if (!input.current) return;
    input.current.style.height = "auto";
    input.current.style.height = `${Math.min(input.current.scrollHeight, 160)}px`;
  }, [value]);
  function submit(event) {
    event.preventDefault();
    if (!pending && value.trim()) onSubmit();
  }
  return (
    <div className="composer-area">
      <form className="composer" onSubmit={submit}>
        <textarea
          ref={input}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          maxLength={8000}
          rows={1}
          placeholder={
            mode === "search"
              ? "¿Qué necesitas encontrar en los manuales?"
              : "Cuéntame qué ocurre con tu equipo o servicio…"
          }
          aria-label="Consulta de soporte TI"
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            )
              submit(event);
          }}
        />
        <div className="composer-toolbar">
          <div className="composer-tools">
            <button
              type="button"
              className={`mode-button ${mode === "query" ? "selected" : ""}`}
              disabled={pending}
              onClick={() => onMode("query")}
            >
              Soporte TI
            </button>
            <button
              type="button"
              className={`mode-button ${mode === "search" ? "selected" : ""}`}
              disabled={pending}
              onClick={() => onMode("search")}
            >
              Manuales
            </button>
            {mode === "search" && (
              <select
                aria-label="Preferencia de categoría"
                value={category}
                onChange={(event) => onCategory(event.target.value)}
                disabled={pending}
              >
                <option value="">Todas las áreas</option>
                {categories.map(({ id, label }) => (
                  <option key={id} value={id}>
                    {label}
                  </option>
                ))}
              </select>
            )}
          </div>
          {pending ? (
            <button
              type="button"
              className="send-button cancel-button"
              onClick={onCancel}
              aria-label="Dejar de esperar"
              title="Dejar de esperar; el servidor puede seguir procesando"
            >
              <Square size={15} fill="currentColor" />
            </button>
          ) : (
            <button
              className="send-button"
              type="submit"
              disabled={!value.trim()}
              aria-label="Enviar consulta"
            >
              <ArrowUp size={20} />
            </button>
          )}
        </div>
      </form>
      <div className="composer-note">
        <span>
          Cada consulta es independiente. Incluye el contexto necesario.
        </span>
        <span className="keyboard-hint">
          Enter <span>↵</span>
        </span>
      </div>
    </div>
  );
}

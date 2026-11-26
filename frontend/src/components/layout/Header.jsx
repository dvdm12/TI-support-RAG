import { BookOpen, PanelRight } from "../ui/Icons.jsx";
import IconButton from "../ui/IconButton.jsx";
import ServiceStatus from "../ui/ServiceStatus.jsx";

export default function Header({
  mode,
  view,
  status,
  onMenu,
  onToggleSources,
  sourcesOpen,
}) {
  return (
    <header className="header">
      <div className="header-title">
        <IconButton label="Mostrar u ocultar navegación" onClick={onMenu}>
          <PanelRight size={17} />
        </IconButton>
        <span>
          {view === "tickets"
            ? "Panel de soporte"
            : mode === "search"
              ? "Manuales de soporte"
              : "Asistente de soporte"}
        </span>
      </div>
      <div className="header-actions">
        <a className="header-router-link" href="/?vista=enrutador">
          Enrutador
        </a>
        <ServiceStatus status={status} />
        <IconButton
          label={
            sourcesOpen ? "Ocultar guía y fuentes" : "Mostrar guía y fuentes"
          }
          aria-expanded={sourcesOpen}
          onClick={onToggleSources}
        >
          <BookOpen size={17} />
        </IconButton>
      </div>
    </header>
  );
}

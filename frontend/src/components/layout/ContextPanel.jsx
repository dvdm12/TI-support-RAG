import {
  ArrowRight,
  BookOpen,
  CircleHelp,
  FileCheck2,
  ShieldCheck,
  X,
} from "../ui/Icons.jsx";
import IconButton from "../ui/IconButton.jsx";
import Sources from "../chat/Sources.jsx";

export default function ContextPanel({ onClose, latest, onSearch }) {
  const sources = latest?.data?.fuentes || latest?.data?.pasajes || [];
  return (
    <aside className="context-panel" aria-label="Guía y fuentes">
      <div className="context-heading">
        <span>
          <BookOpen size={16} />
          Guía y fuentes
        </span>
        <IconButton label="Cerrar guía y fuentes" onClick={onClose}>
          <X size={16} />
        </IconButton>
      </div>
      {sources.length ? (
        <div className="context-sources">
          <span className="nav-section-label">
            ÚLTIMA RESPUESTA · {sources.length} FUENTES
          </span>
          <Sources
            sources={sources}
            messageId={`panel-${latest.id}`}
            expanded
          />
        </div>
      ) : (
        <>
          <div className="context-illustration">
            <div>
              <BookOpen size={30} strokeWidth={1.4} />
            </div>
            <span className="illustration-check">
              <FileCheck2 size={16} />
            </span>
          </div>
          <h2>
            Una respuesta empieza
            <br />
            con una buena fuente.
          </h2>
          <p className="context-description">
            El asistente consulta manuales de soporte para ayudarte a encontrar
            el siguiente paso.
          </p>
          <div className="context-steps">
            <div>
              <span>01</span>
              <p>
                <strong>Describe qué ocurre</strong>Incluye el equipo, el
                síntoma y el mensaje de error.
              </p>
            </div>
            <div>
              <span>02</span>
              <p>
                <strong>Consulta las referencias</strong>Las fuentes citadas
                aparecerán junto a la respuesta.
              </p>
            </div>
            <div>
              <span>03</span>
              <p>
                <strong>Revisa el siguiente paso</strong>Puede ser una
                comprobación, una aclaración o soporte humano.
              </p>
            </div>
          </div>
          <button className="browse-manuals" onClick={onSearch}>
            <BookOpen size={15} />
            Explorar los manuales
            <ArrowRight size={15} />
          </button>
        </>
      )}
      <div className="context-bottom">
        <div>
          <ShieldCheck size={16} />
          <strong>Tu información, con cuidado</strong>
        </div>
        <p>
          No compartas contraseñas, tokens ni datos confidenciales en tus
          consultas.
        </p>
        <small>
          <CircleHelp size={13} />
          La IA puede equivocarse. Verifica las fuentes antes de actuar.
        </small>
      </div>
    </aside>
  );
}

import { BookOpen, FileText } from "../ui/Icons.jsx";

export default function Sources({ sources = [], messageId, expanded = false }) {
  if (!sources.length) return null;
  return (
    <div className={`sources ${expanded ? "sources--expanded" : ""}`}>
      {sources.map((source, index) => {
        const metadata = source.fuente || source;
        const id = source.id || `P${index + 1}`;
        return (
          <details
            className="source-card"
            key={`${source.chunk_id}-${id}`}
            id={`source-${messageId}-${id}`}
          >
            <summary>
              <span className="source-tag">{id}</span>
              <span>
                <strong>
                  {metadata.title ||
                    metadata.document_id ||
                    "Manual de soporte"}
                </strong>
                <small>{metadata.section || "Referencia documental"}</small>
              </span>
              <FileText size={15} />
            </summary>
            <div className="source-details">
              {source.texto && <p>{source.texto}</p>}
              {metadata.pages?.length > 0 && (
                <p>Páginas: {metadata.pages.join(", ")}</p>
              )}
              {metadata.version && <p>Versión: {metadata.version}</p>}
              {metadata.source && (
                <p className="source-origin">
                  <BookOpen size={12} />
                  {metadata.source}
                </p>
              )}
              <small>Fragmento: {source.chunk_id}</small>
            </div>
          </details>
        );
      })}
    </div>
  );
}

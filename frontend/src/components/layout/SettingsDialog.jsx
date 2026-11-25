import { useEffect, useRef } from "react";
import { ExternalLink, RefreshCw, X } from "../ui/Icons.jsx";
import IconButton from "../ui/IconButton.jsx";
import ServiceStatus from "../ui/ServiceStatus.jsx";

export default function SettingsDialog({ onClose, health, onSignOut, user, pending }) {
  const dialog = useRef(null);
  useEffect(() => {
    const node = dialog.current;
    node.showModal();
    return () => node.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="settings-dialog"
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === dialog.current) onClose();
      }}
      aria-labelledby="settings-title"
    >
      <div className="settings-content">
        <div className="dialog-heading">
          <h2 id="settings-title">Tu espacio de soporte</h2>
          <IconButton label="Cerrar configuración" onClick={onClose}>
            <X size={18} />
          </IconButton>
        </div>
        <p>Conexión local con la API de TI Support.</p>
        <div className="settings-connection">
          <ServiceStatus status={health.status} />
          <button className="text-button" onClick={() => health.refresh()}>
            <RefreshCw size={14} />
            Comprobar
          </button>
        </div>
        <p className="settings-note">
          Este indicador comprueba el proceso de la API. Las consultas también
          necesitan Supabase y Groq disponibles.
        </p>
        <a
          className="settings-link"
          href="/api/v1/docs/"
          target="_blank"
          rel="noreferrer"
        >
          Documentación de la API
          <ExternalLink size={14} />
        </a>
        <div className="settings-history">
          <strong>Sesión e historial</strong>
          <p>
            Conectado como {user?.email}. Tus conversaciones se guardan en
            Supabase y solo tú puedes verlas; al volver a entrar se recuperan.
          </p>
          <button
            className="danger-button"
            disabled={pending}
            onClick={() => {
              onClose();
              onSignOut();
            }}
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </dialog>
  );
}

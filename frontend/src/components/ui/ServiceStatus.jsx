export default function ServiceStatus({ status }) {
  const label = {
    online: "API disponible",
    checking: "Comprobando API",
    offline: "API sin conexión",
  }[status];
  return (
    <span
      className={`service-status service-status--${status}`}
      title="Comprueba el proceso Django. No verifica la disponibilidad de Groq ni Supabase."
    >
      <i />
      {label}
    </span>
  );
}

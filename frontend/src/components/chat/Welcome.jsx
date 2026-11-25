export default function Welcome({ mode }) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <h1 id="welcome-title">
        {mode === "search"
          ? "¿Qué buscamos en los manuales?"
          : "¿Qué necesitas resolver?"}
      </h1>
      {mode === "search" && (
        <p>
          Consulta las referencias de soporte, sin generar una respuesta con IA.
        </p>
      )}
    </section>
  );
}

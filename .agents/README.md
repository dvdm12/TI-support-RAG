# Continuidad de TI-support-RAG

Lee primero [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md), sección
**Estado actual para continuar — leer primero** (actualizada el 20-10-2026).
Contiene el estado de Git, estructura backend/frontend/infra, Docker activo,
autenticación, pruebas, manual Ricoh verificado y trabajo pendiente de ingestión.

El historial posterior se conserva como referencia y puede contener estados
superados. Las rutas operativas están en `backend/` y `infra/`.

`plantuml_notebook_activity.toml` es una especificación de diagrama basada en
una inspección histórica del notebook. No constituye una instrucción para
recrear el diagrama ni una prueba de las banderas actuales; contrastarla con el
notebook si se solicita trabajo en él.

El manual Ricoh está identificado, extraído y fragmentado con embeddings reales
en un índice local independiente. La evaluación tiene evidencia esperada Top-3
en 11/12 preguntas; sigue pendiente el caso de impresión retenida. La API activa
conserva sus 70 fragmentos académicos: no hubo carga Supabase ni llamadas Groq.
La siguiente integración necesita resolver ese fallo y el presupuesto de contexto
para unidades completas. El usuario solicitó conservar el alcance simple y subir todos los cambios a una
rama nueva: `codex/backend-infra-ricoh-local`. No integrar todavía Ricoh en la API.

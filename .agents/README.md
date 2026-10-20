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
conserva sus 70 fragmentos académicos. La evaluación local del manual no lo
cargó a Supabase ni llamó a Groq; la regresión del backend sí usó ambos servicios.
La siguiente integración necesita resolver ese fallo y el presupuesto de contexto
para unidades completas. El usuario solicitó conservar el alcance simple y subir todos los cambios a una
rama nueva: `codex/backend-infra-ricoh-local`. No integrar todavía Ricoh en la API.

Actualización posterior: se corrigieron aclaraciones de incidentes ambiguos y se
completó la regresión del backend (13/13 criterios de entrega, incluidos dos
reemplazos seguros y tres aclaraciones locales; no son 13 respuestas validadas
por el modelo). Pasan 234 unitarias y 24 API. Imagen corregida desplegada y dos
consultas HTTP reales correctas. Ver `backend/docs/BACKEND_VALIDATION.md` y
`backend/docs/backend_validation.json`. El usuario autorizó crear y publicar el
commit `fix: clarify ambiguous requests and validate backend regression` en la
misma rama. Esta continuidad se incluye en esa entrega; consultar `git log -1`
y `git status -sb` para conocer su identificador y sincronización con origin.

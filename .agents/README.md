# Continuidad de TI-support-RAG

Actualizado el 21-10-2026. Lee primero el estado vigente al inicio de
[PROJECT_HANDOFF.md](PROJECT_HANDOFF.md). Los apartados posteriores conservan
historia y pueden contener restricciones o cifras ya superadas.

## Estado actual

- Backend desplegado con recuperación híbrida v2 y prompt `rag_v6`. Imagen
  `a414431ee034`, corpus académico activo de 70 fragmentos. Ricoh sigue separado.
- Desarrollo: 7/7 preguntas documentales completas en Top-3 y contexto, 35/35
  unidades, en reproducción de rankings guardados. Parámetros ajustados con
  preguntas conocidas; no acredita generalización ni revisión humana.
- Comparación de generación real completada: 14 llamadas Groq, siete pares,
  mismo prompt/modelo/parámetros. Semántica 6.592 / híbrida 6.523 tokens.
  Solo generación, excluye clasificación, revisión y corrección del pipeline.
- Última suite: 270 pruebas unitarias locales correctas. Las 26 API corresponden
  a la validación del despliegue anterior. No sumar ni presentarlas como una
  ejecución conjunta nueva. PDF de tokens: tres páginas revisadas visualmente.
- Reserva: 12 candidatos en borrador, sin ejecutar ni congelar. Anotaciones de
  desarrollo y reserva pendientes de revisión humana. No abrir reserva por defecto.

## Para continuar

La tabla vigente está en [CLASS09_METRICS_STATUS.md](CLASS09_METRICS_STATUS.md).
El siguiente pendiente es **revisión humana de fidelidad, corrección, utilidad y
respaldo de las respuestas ya guardadas**. No marcarla como completada por una
validación de JSON/citas ni atribuir al agente una revisión humana.

Usar `backend/docs/generation_tokens_20261021.json`: incluye las 14 respuestas,
contextos, fuentes, usage y revisión pendiente. No repetir llamadas para revisarlos.
Guía `backend/docs/GENERATION_TOKENS.md`. Toda exportación de métricas debe seguir
generando JSON, CSV y PDF; para reexportar usar `--from-json`, sin proveedores.

También faltan cobertura de citas por afirmación, tasas de abstención correcta e
innecesaria, congelación/evaluación de reserva, decisión final y entregables de
clase 09. No iniciar estos trabajos como parte de actualizar la continuidad.

## Git y alcance

Rama `codex/backend-infra-ricoh-local`; último commit publicado registrado:
`aea3002`. Completitud, mejoras de cobertura y tokens reales tienen cambios
locales pendientes de commit/push. Esta actualización no autoriza publicarlos.
Consultar `git status -sb` antes de continuar. No se hicieron nuevas consultas,
pruebas, despliegues, commit ni push al actualizar estos archivos.

`.env` y credenciales permanecen privados; no imprimirlos. No integrar Ricoh ni
realizar pruebas de aislamiento entre usuarios por defecto.
`plantuml_notebook_activity.toml` es una especificación histórica, no una
instrucción para recrear un diagrama o ejecutar notebooks.

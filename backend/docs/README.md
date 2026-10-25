# Documentación del proyecto

Los documentos se agrupan por contenido. Las guías Markdown, los informes y las
validaciones de cada tema se encuentran en su directorio; los datos históricos
JSON/CSV/PDF conservan sus bytes y fechas originales.

| Directorio | Contenido y punto de entrada |
|---|---|
| [api](api/API.md) | Endpoints, Swagger, autenticación y verificación HTTP |
| [infraestructura](infraestructura/DOCKER.md) | Docker, [configuración Supabase](infraestructura/supabase_setup.md) y verificaciones de infraestructura |
| [rag](rag/RAG.md) | Ingestión e índice académico, [evidencias](rag/RAG_EVIDENCE.md) y [protocolo de reserva](rag/RAG_RESERVE.md) |
| [extractor](extractor/EXTRACTION_PIPELINE.md) | Pipeline PDF, contratos, adaptadores, estrategias, reglas y evaluaciones; `baselines/` guarda referencias y `fixtures/` catálogos de muestras |
| [evaluacion/recuperacion](evaluacion/recuperacion/RETRIEVAL_METRICS.md) | Métricas de recuperación, cobertura, comparación de fragmentación y [trazas RRF](evaluacion/recuperacion/RRF_TRACES.md), con JSON/CSV/PDF |
| [evaluacion/generacion](evaluacion/generacion/GENERATION_TOKENS.md) | Comparación de generación y tokens, con JSON/CSV/PDF |
| [evaluacion/tiempos](evaluacion/tiempos/STAGE_TIMINGS.md) | Definición de tiempos por etapa y comparación temporal |
| [evaluacion/validaciones](evaluacion/validaciones/BACKEND_VALIDATION.md) | Verificaciones generales del backend, contratos y comportamiento RAG |
| [human_review](human_review/README.md) | Fichas de revisión humana; las respuestas guardadas y los veredictos pendientes se conservan intactos |
| [clases/clase08](clases/clase08/CLASE08.md) | Material y verificaciones históricas de Clase 08 |
| [parcial1](parcial1/bitacora_parcial.md) | Bitácora, resultados y reporte del primer corte |
| [parcial2](parcial2/README.md) | Material para el profesor, guías y salidas por ejecución del segundo corte |
| `multimodal/` | Imágenes de demostración y pruebas OCR |
| `rag_runs/` | Evidencias técnicas locales organizadas por ejecución; ignoradas por Git |
| [archivo](archivo/reubicaciones_20261025.json) | Tabla de rutas anteriores y actuales, con hashes de datos reubicados; registros locales de Drive en `drive/`, ignorados por Git |

## Lectura de evidencias históricas

Los JSON y PDF originales pueden mencionar rutas anteriores: esas cadenas son
procedencia de la ejecución registrada. No se reescribieron para simular una nueva
medición. Consultar la tabla de reubicaciones para encontrar el archivo actual.
La reorganización no ejecuta la reserva ni convierte revisiones del agente en humanas.

## Convenciones para nuevas salidas

Guardar cada nueva guía y sus informes en el directorio del tema. Los scripts
utilizan las rutas organizadas como valores predeterminados. Para el notebook de
entrega, usar `parcial2/ejecuciones/<fecha-UTC>/`, con `resultados/` y el ZIP juntos.
Los notebooks y su ZIP de recursos permanecen en `backend/notebooks/`; el SQL de
Supabase permanece en `infra/supabase/migrations/`.

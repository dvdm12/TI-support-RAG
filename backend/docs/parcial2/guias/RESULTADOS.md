# Cómo leer los resultados

Para ejecutar el sistema, seguir la [guía del profesor](../../../notebooks/GUIA_PROFESOR.md).
En cada carpeta `ejecuciones/<fecha-UTC>/`, abrir primero el PDF y después los
JSON cuando se necesite comprobar una respuesta o su evidencia.

| Archivo dentro de `resultados/` | Qué contiene | Cómo interpretarlo |
|---|---|---|
| `comparacion_hibrida_desarrollo.pdf` | Matriz agregada, casos, cambios, condiciones y trazabilidad | Compara recuperación de desarrollo; explica métricas y límites. No es una evaluación nueva de Groq. |
| `comparacion_hibrida_desarrollo.json` / `.csv` | Comparación de recuperación con detalle verificable | Permiten revisar los números del PDF sin depender de capturas. |
| `metricas_recuperacion.json` / `.csv` | Tabla resumen de variantes recalculada desde selecciones guardadas | Precisión, recall, hit, rango recíproco y cobertura; no equivalen a calidad de respuesta. |
| `traza_sesion.json` | Configuración, modo, OCR y consulta real del punto 10, si se ejecutó | Identifica el recorrido, fuentes, contexto, tiempos y estado. Los tokens disponibles no siempre incluyen todo el pipeline. |
| `interaccion_profesor.json` | Última interacción del panel: pregunta, clasificación, respuesta, fuentes y tiempos según el modo | `live_query` indica consulta nueva; `saved_observation` indica evidencia histórica. `supabase` identifica el repositorio remoto. |

`parcial2_resultados.zip` reúne esos archivos. `verificacion.json`, cuando existe,
lo añade la comprobación externa: no lo genera automáticamente el notebook.

## Estados y conclusiones

`OK_VALIDADO` indica que el recorrido pasó sus controles automáticos.
`OK_REQUIERE_HUMANO` conserva una decisión de intervención humana y puede incluir
una respuesta documental válida. Un resultado sin error técnico no sustituye la
revisión humana de corrección, fidelidad, citas y utilidad.

El PDF actual explica la recuperación histórica. Las respuestas nuevas se
almacenan en JSON; no se genera todavía un PDF explicativo por consulta.
El conjunto de reserva no se abre ni se ejecuta desde este material.

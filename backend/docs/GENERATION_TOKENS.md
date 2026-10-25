# Tokens de generación: comparación real A/B

El 21-10-2026 se ejecutaron 14 llamadas reales a Groq: siete preguntas documentales
de desarrollo, una generación semántica y otra híbrida por pregunta. Todas
respondieron HTTP 200 con usage válido y contrato/etiquetas de cita válidos.
No se ejecutaron las seis preguntas de comportamiento ni la reserva.

## Condiciones iguales

- Modelo `openai/gpt-oss-20b`, prompt `rag_v6`, temperatura 0, razonamiento low,
  máximo 800 tokens de salida y mismo esquema RespuestaRAG.
- Contexto hasta 850 tokens estimados, con límite de 1000 para entrada al generador.
  El máximo real observado de entrada fue 785, dentro del límite.
- Misma pregunta y corpus; sin clasificador ni categorías esperadas. Ambas
  estrategias aplican la política de pertinencia antes de Top-3. A usa Top-10
  semánticos guardados, B las selecciones híbridas mejoradas ya registradas.
- Orden alternado A/B y B/A por pregunta. Una observación por combinación,
  sin reintentos automáticos; no se acredita estabilidad estadística.
- Generación directa: no se ejecuta clasificación, revisión de respaldo ni
  corrección. Por ello **no es consumo total del endpoint query**.

La A de este experimento aplica la política actual antes del corte y el mismo
prompt nuevo que B. No reetiquetar como nuevas sus métricas de recuperación
históricas obtenidas con otra configuración. No se generó una nueva búsqueda
Supabase ni se volvió a cargar un modelo de embeddings para esta medición.

## Uso informado por Groq

| Tokens | Semántica A | Híbrida B | Diferencia B−A |
|---|---:|---:|---:|
| Entrada: suma | 5.354 | 5.388 | +34 |
| Salida: suma | 1.238 | 1.135 | −103 |
| Total: suma | 6.592 | 6.523 | −69 |
| Entrada: media | 764,86 | 769,71 | +4,86 |
| Salida: media | 176,86 | 162,14 | −14,71 |
| Total: media | 941,71 | 931,86 | −9,86 |

Total de la ejecución: **13.115 tokens informados**, siete pares completos,
sin observaciones con usage desconocido, sin errores ni reintentos. B consumió
1,05% menos tokens totales en esta ejecución; la salida generada varía según el
contexto. La mediana total A/B es 947/950: el resultado no demuestra un ahorro
estable ni una calidad superior. No se calcula costo monetario ni una tarifa.
Los tokens de salida pueden incluir razonamiento interno.

## Integridad y evaluación pendiente

`src/rag/token_comparison.py` registra usage incluso si una salida no cumple
contrato, conserva campos faltantes y calcula agregados sobre la misma población
con medición válida en ambas variantes. No reemplaza errores o faltantes por cero.
Conserva todas las observaciones, también las no emparejadas y reintentos
explícitos, para no ocultar consumo. Sin casos emparejados las medidas son null/N/E.

`contract_valid` acredita JSON, contrato y correspondencia de etiquetas con catálogo.
**No acredita fidelidad, corrección, respaldo real ni utilidad.** Esas revisiones
permanecen pendientes y no se atribuyen al agente como revisión humana.
Las respuestas, contextos, fuentes y formularios pendientes se guardaron para
que esa revisión pueda realizarse sin repetir llamadas. Los tokens de generación
comparables de la tabla de clase 09 quedan medidos; el resto del pipeline no.

## Archivos y uso

- `scripts/compare_generation_tokens.py`: preparación, medición y checkpoints.
- `docs/generation_tokens_20261021.json`: protocolo, preguntas, contextos/catálogos,
  respuestas crudas/validadas, usage, HTTP permitido, estimación local separada,
  agregados y hashes. Sin encabezados de autenticación ni cuerpos de error.
- CSV con el mismo nombre: 14 filas, tokens y estado por combinación.
- PDF con el mismo nombre: tres páginas revisadas visualmente, resumen,
  contabilidad por caso, método y trazabilidad.

Desde backend, **solo cuando se necesite una nueva medición**:

```sh
../.venv/bin/python -m scripts.compare_generation_tokens --output docs/nueva_medicion.json
```

Este comando consume cuota real de Groq. No repetirlo para volver a exportar:

```sh
../.venv/bin/python -m scripts.compare_generation_tokens --from-json docs/generation_tokens_20261021.json --output docs/tokens_reexportados.json
```

Toda exportación escribe JSON/CSV/PDF, incluso antes de empezar y tras cada
observación. Un fallo detiene las llamadas y conserva los archivos. `--resume`
continúa solo combinaciones no ejecutadas o HTTP 429, conservando el historial;
verifica hashes de protocolo, código y entradas. Otras incidencias requieren
revisar diagnóstico, no reintentar automáticamente. Un cambio de configuración
requiere otro archivo. Nunca publicar credenciales ni imprimir .env.

Siete pruebas nuevas cubren usage válido, denominador emparejado, costos de
salidas inválidas, desconocidos, preparación sin reserva, adaptación HTTP sin
reintento y checkpoints incompletos con los tres formatos. Pasan **270 unitarias
locales**. Se recalcularon sumas/medias, 14 filas CSV y hashes de origen/código de
forma independiente. No hubo despliegue, cambios al corpus, commit ni push.

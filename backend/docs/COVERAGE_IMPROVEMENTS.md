# Mejoras de cobertura — desarrollo, 21-10-2026

Se corrigió la recuperación de términos técnicos y la selección de pasajes;
se compactaron las instrucciones de generación conservando reglas de seguridad,
condiciones y citas. Top-3, corpus, fragmentos completos, contrato y límite de
850 tokens iniciales / 1000 por llamada permanecen iguales. No se incorporó Ricoh.

## Cambios aplicados

1. `src/rag/lexical.py`: antes se separaba Wi-Fi en `wi` y `fi`, descartados por
   longitud. Se normalizan Wi-Fi, WiFi y wi fi a `wifi`, y se conservan códigos
   con guiones como MP-4002. Continúan la normalización de tildes, stopwords y
   reducción de plurales previas; no se atribuye a BM25 comprensión de negaciones.
2. `src/rag/retrieval.py`: el filtro de aplicabilidad existente para enlaces no
   abiertos se aplica a la unión antes de cortar a tres, permitiendo rellenar
   posiciones con candidatos aplicables. La defensa posterior del pipeline se
   conserva. RRF mantiene constante 60, con pesos semántica=1 y léxico=2, más
   ajuste de categoría cuando se solicita en producción. Este peso se eligió
   usando desarrollo conocido, no es una superioridad universal demostrada.
3. `prompts/rag_v6.md`: mismas obligaciones documentales en instrucciones más
   compactas. El presupuesto base local pasa de 631 a 551 tokens para contenido
   vacío, esquema y reserva incluidos. Es una estimación local, no uso informado
   por Groq. Se conservan pasajes completos, metadatos del catálogo y datos
   faltantes para aclaración. No se amplía el presupuesto ni se recorta evidencia.
4. El pipeline registra la versión nueva de recuperación y rag_v6. El evaluador
   recompone aportes ponderados y exclusiones previas a Top-3; los informes
   históricos conservan rag_v5/pesos anteriores y no se sobrescriben.

## Comparación antes/después

Mismas siete preguntas documentales conocidas, 35 unidades anotadas por el agente.

| Medida | Híbrida anterior | Híbrida mejorada |
|---|---:|---:|
| Precision@3 | 52,38% | 66,67% |
| Recall@3 | 80,95% | 100,00% |
| Hit@3 | 85,71% | 100,00% |
| MRR@3 | 0,8571 | 1,0000 |
| Cobertura macro de unidades Top-3 | 80,36% | 100,00% |
| Cobertura macro del contexto final | 76,79% | 100,00% |
| Preguntas completas en Top-3 | 5/7 | 7/7 |
| Preguntas completas en contexto | 4/7 | 7/7 |
| Unidades presentes en Top-3 | 26/35 | 35/35 |

Precision@3 no llega al 100% porque algunas preguntas tienen menos de tres
fragmentos relevantes; 66,67% es el máximo macro de esta anotación. Los seis
casos de comportamiento se recorren sin métricas documentales. Sus respuestas
no se generaron ni calificaron en este experimento.

Los fallos documentales E03 y E05 se corrigen en este conjunto. E04 conserva la
unidad que se perdía en contexto. No hay pérdida de cobertura respecto a la base
en ninguna de las siete preguntas. Los casos conocidos se usaron para ajustar:
**este 100% no acredita generalización, fidelidad de respuestas ni revisión humana**.

### Separación de efectos

| Configuración | Cobertura Top-3 | Cobertura contexto | Contextos completos |
|---|---:|---:|---:|
| Anterior | 80,36% | 76,79% | 4/7 |
| Solo prompt compacto | 80,36% | 80,36% | 5/7 |
| Solo cambios de ranking | 100,00% | 91,07% | 5/7 |
| Ambas mejoras | 100,00% | 100,00% | 7/7 |

## Método y reproducción

`backend=offline_replay`: se reutilizan Top-10 semánticos grabados de Supabase,
se recalcula BM25/fusión/contexto con los 70 registros congelados y se usan
embeddings reales del modelo/revisión fijados para los cosenos adicionales.
No se inventan rankings semánticos ni se realizan consultas nuevas para la
comparación. El modelo se cargó desde su caché existente, sin descarga adicional.

Se comprueban hash de anotaciones y corpus, preguntas de desarrollo y reproducción
exacta de los IDs de contexto anteriores. Antes/después comparten preguntas y
candidatos semánticos. No se usa categoría esperada, clasificador ni reserva.
No se calcula latencia comparativa: campos de tiempo no evaluados son null/N/E.
El presupuesto se estima con el tokenizer, esquema y reserva actuales; no es
consumo efectivo del generador.

Desde backend, con pesos disponibles:

```sh
HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 ../.venv/bin/python -m scripts.evaluate_coverage_improvements
```

La ruta de caché temporal debe existir; no asumir que sobrevive entre sesiones.
`--source` y `--output` permiten otras rutas. Salidas automáticas JSON/CSV/PDF:
`docs/coverage_improvements_20261021.*`. El JSON conserva entradas, contextos,
catálogo, rankings semánticos originales, ablations, versiones y hashes. El PDF
presenta cuatro páginas, renderizadas y revisadas visualmente sin defectos.

## Validación y despliegue

- Cuatro pruebas nuevas: identificadores técnicos, relleno tras exclusión,
  exposición real pese a enlace no abierto y presupuesto/pasajes/datos faltantes.
  Pasan 263 pruebas unitarias locales y 26 API sin proveedores.
- Recalculo independiente de unidades, proporciones, hashes de código/origen y
  26 filas CSV correcto. Anotación, reserva y corpus originales sin cambios.
- `coverage_improvements_trace_validation.json`: las 13 trazas del evaluador
  actual coinciden con las selecciones y contextos del informe, sin proveedores.
- Imagen `sha256:a414431ee034403f145f1ca2576223bdff9a71febb4b242f98830954343a5d4b`
  desplegada; contenedor saludable. `coverage_improvements_http_validation.json`
  documenta tres búsquedas reales Supabase vía HTTP (E03/E04/E05), todas 200 y
  cobertura completa en lo recuperado, sin categoría esperada. No es generación
  de respuestas ni medición de cobertura del contexto de query por HTTP.

El prompt reducido conserva las reglas y pasó las regresiones locales con
fixtures; su fidelidad con generación real **todavía requiere evaluación**.
No se llamó a Groq ni se abrió la reserva. Revisar anotaciones humanamente y
comparar respuestas antes de concluir la elección final. La siguiente evaluación
independiente necesita congelación; no ajustar con resultados de reserva.
No se hicieron commit ni push de estos cambios.

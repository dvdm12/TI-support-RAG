# Paso 8: unidades completas y recuperación en español - 25-10-2026

Verificación local del manual Ricoh MP 4002 tras los pasos 1–7 del extractor.
Separa tres niveles: conservación en la extracción, construcción de unidades y
vistas de búsqueda, y recuperación con las doce preguntas en español. No genera
respuestas, no llama a Groq ni Supabase y no reconstruye índices.

## Componentes

- `src/rag/unit_verification.py`: contabilidad de caracteres del PDF, cobertura
  de bloques en unidades, comparación antes/después, regla de relevancia
  compartida y clasificación por etapa.
- `scripts/verify_units_retrieval.py`: reextrae Ricoh con el pipeline actual,
  compara con la extracción registrada y con `data/indexes/ricoh-local-v1/`,
  evalúa las tres estrategias y exporta `report.json`, `cases.csv` y `report.pdf`
  en un directorio nuevo. Falla si el índice local no corresponde a la
  extracción actual o si un índice cambia durante la ejecución.
- `scripts/evaluate_ricoh_local.py` usa ahora la misma función `relevant`; las
  posiciones por caso se comprobaron idénticas al informe guardado.

## Etapas de fallo

| Etapa | Significado |
|---|---|
| `extraction_loss` | La sección o fila esperada no aparece en la extracción nueva. |
| `unit_loss` | Está extraída, pero no existe una unidad completa (excluida o ausente). |
| `fragment_loss` | La unidad existe, pero no tiene vista de búsqueda. |
| `search_failure` | La evidencia está indexada y no aparece en Top-3. |
| `retrieved` | Una unidad completa relevante aparece en Top-3. |

La tasa `hit_at_3_given_evidence_indexed` usa como denominador solo los casos
cuya evidencia llegó al índice; las pérdidas previas se listan aparte.

## Resultado 25-10-2026

Commit base `7be846f`, índice `ricoh-local-85995a0e67f7d4017a02`, modelo
`paraphrase-multilingual-MiniLM-L12-v2` revisión `e8f8c211…`.

- Extracción nueva idéntica byte a byte a la registrada (`ca1178c5…`).
- Unidades antes/después: 498/498, idénticas; el índice local coincide.
- Contabilidad del PDF: 194.084 caracteres no blancos en las 213 páginas de
  contenido; 0 faltantes y 0 sobrantes (NFKC, contando títulos de sección,
  párrafos, celdas, encabezados y texto de maquetación excluido).
- Bloques: 1.647 párrafos y 364 filas en exactamente una unidad; 19 filas de
  seis tablas gráficas excluidas con motivo; 0 problemas.

| Estrategia | Pérdida extracción | Pérdida unidad/fragmento | Fallo de búsqueda | Recuperado Top-3 |
|---|---:|---:|---|---:|
| semantic | 0 | 0 | 2 (RIC-06, RIC-09) | 10 |
| hybrid | 0 | 0 | 2 (RIC-06, RIC-09) | 10 |
| hybrid_literal | 0 | 0 | 1 (RIC-06) | 11 |

Conclusión acotada: en este manual y estos doce casos, todos los fallos son de
búsqueda, no de extracción ni de construcción de unidades. RIC-06 (Sending a
Hold Print File) está extraído en S0083 y tiene unidad y vistas, pero la
búsqueda prefiere procedimientos de Stored Print. RIC-09 ("Offline") se resuelve
solo con la coincidencia literal del mensaje.

## Límites

- Doce casos diagnósticos redactados con acceso a la fuente; no es benchmark
  ciego ni generaliza a otros manuales o a los PDF candidatos por categoría.
- La contabilidad de caracteres acredita conservación, no orden de lectura ni
  corrección semántica.
- Recuperar la unidad correcta no evalúa la respuesta; eso corresponde al paso 9.
- Las seis tablas gráficas siguen sin interpretación visual.
- Los diez PDF candidatos no se pueden verificar con este paso: ninguno completa
  el pipeline actual (sin marcadores o con pie de página numerado junto al
  título). Su soporte requiere cambios de perfil/extractor aparte.

## Reproducir

Desde `backend/`, con el modelo en la caché local:

```bash
HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 ../.venv/bin/python -m scripts.verify_units_retrieval \
  --output docs/rag_runs/unit_retrieval/<nuevo_directorio>
../.venv/bin/python -m unittest test.test_unit_verification test.test_verify_units_retrieval
```

Evidencia LOCAL IGNORADA: `docs/rag_runs/unit_retrieval/check_20261025/`.
76 pruebas nuevas; suite completa 433 unitarias correctas. Sin nueva suite API.

## Pruebas exhaustivas (25-10-2026)

76 pruebas: 55 en `test/test_unit_verification.py` (normalización, contabilidad,
cobertura, comparación, relevancia, presencia, etapas y resumen) y 21 en
`test/test_verify_units_retrieval.py` (integración de `verify()` sobre un backend
temporal con índice congelado real, guardas de hash/modelo/índice activo,
detección de cambios durante la ejecución, exportación y `main`). Incluyen una
prueba de equivalencia con la regla de relevancia anterior de evaluate_ricoh_local.
Las pruebas destaparon y corrigieron cuatro defectos: duplicados ocultos en
`compare_units`, secciones solo con tablas clasificadas como pérdida de
extracción, cobertura aceptada por subcadena o celdas alteradas, y exportación
parcial al rechazar archivos existentes. `stage_summary` rechaza etapas
desconocidas. Mutación: 18/19 mutantes detectados; el restante es equivalente
(modo 'x' redundante tras la comprobación previa). Suite completa: 433
unitarias correctas. La reejecución real tras las correcciones dio resultados
idénticos (`docs/rag_runs/unit_retrieval/check_20261025_tests/`).

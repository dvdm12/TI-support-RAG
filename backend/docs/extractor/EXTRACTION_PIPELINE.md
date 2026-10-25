# Extracción PDF por etapas — paso 3

`extract_real_document(manifest_path, document_id)` conserva su interfaz y
retorna el mismo diccionario v1. Ahora coordina estas etapas secuenciales,
implementadas en `src/rag/external_ingestion.py`:

| Etapa | Función | Entrada y resultado |
|---|---|---|
| Validación de fuente | validate_source | Comprueba el registro y hash; devuelve ruta, documento y perfil en RegisteredSource. |
| Análisis documental | analyze_document | Comprueba cifrado, páginas y rango; obtiene marcadores y límites en DocumentAnalysis. Cierra el stream de pypdf al terminar. |
| Extracción de páginas | extract_pages | Procesa cada página y devuelve ExtractedPages, con secciones, auditoría y textos excluidos. Mantiene estado propio para IDs y continuaciones. |
| Reconstrucción documental | reconstruct_document | Enlaza antecesores y construye texto/páginas de cada sección; prepara el diccionario v1 sin metadatos de ciclo de vida. |
| Validación final | validate_extraction | Aplica los contratos del paso 2 sin reserializar ni modificar el resultado. |

## Dentro de cada página

1. `audit_page`: obtiene numeración y comprueba exclusiones, páginas vacías y
   requisitos de texto. Las páginas excluidas conservan su motivo y auditoría.
2. `extract_page_layout`: separa encabezados/pies/pestañas, detecta tablas y
   reúne líneas y tablas en orden geométrico dentro de un PageLayout.
3. `assemble_page_blocks`: reconstruye párrafos, separa pasos numerados y asigna
   los elementos a su sección. `append_block` mantiene IDs y referencias de
   posible continuación entre páginas; no fusiona filas.

El análisis inicial se copia antes de acumular bloques, de modo que reutilizarlo
no conserva IDs o datos de una ejecución previa. Las páginas se cierran en un
finally y el documento pdfplumber en su contexto, incluso cuando una página falla.
No se guardan objetos de las bibliotecas en el resultado persistido.

## Fallos y compatibilidad

Un fallo detiene el procesamiento; las etapas posteriores no ejecutan ni se
devuelve una extracción parcial aceptada. Se conserva la instancia, tipo y
mensaje de la excepción original. Python añade notas con la etapa y, cuando
corresponde, la página PDF; por ejemplo:

```text
ValueError: Página 75 sin texto: revisar OCR, no omitir automáticamente.
PDF extraction stage: page_audit; PDF page: 75
PDF extraction stage: page_extraction
```

Estas notas son contexto de depuración y no campos añadidos al JSON. Los helpers
previos y review_markdown siguen disponibles para los consumidores existentes.
No se añade selección de estrategias, OCR, adaptadores de bibliotecas, conexión
remota ni un sistema genérico de plugins; esas capacidades pertenecen a los
pasos posteriores. Las etapas son funciones locales con estado explícito.

## Comprobación

Desde backend, con el entorno de la raíz:

```sh
../.venv/bin/python -m unittest test.test_extraction_pipeline test.test_extraction_contracts test.test_extraction_baseline test.test_external_ingestion test.test_external_chunking
../.venv/bin/python -m scripts.check_extraction_baseline
```

El 24-10-2026 (America/Bogota) pasaron 42 pruebas específicas, incluidas siete
nuevas sobre conservación de condiciones y filas, continuaciones, aislamiento
del estado, interrupción ante fallos, liberación de recursos y excepciones.
La suite unitaria completa pasó 294 pruebas; no se repitieron pruebas API.
La extracción completa mantiene el hash
`ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44`,
sin secciones ni referencias locales cambiadas. La línea base permanece congelada.
Informe técnico local ignorado:
`docs/rag_runs/extraction_baseline/20261025T030355523352Z.json` (hora UTC).

La equivalencia demuestra conservación de la extracción existente; no acredita
mejora de recuperación, interpretación de figuras ni revisión humana nueva.

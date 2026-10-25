# Línea base del extractor Ricoh

Paso 1 del procedimiento de mejora. Antes de refactorizar se fija el resultado
comprobado del PDF Ricoh MP 4002, versión documental D129-7802. La referencia
versionable es `docs/baselines/ricoh_extraction_v1.json`.

## Qué se conserva

- SHA-256 y tamaño del PDF, perfil completo y hash del perfil.
- Hash del JSON completo de extracción, de cada sección, de auditoría de páginas
  y de los textos excluidos del diseño. Se detectan cambios de contenido aunque
  el número de párrafos o filas siga igual.
- Conteos esperados y tablas excluidas de indexación textual.
- Hashes de extracción y Markdown guardados, los cuatro archivos del índice
  Ricoh y los tres del índice académico activo. Son referencias locales: no se
  copian ni se modifican al comprobar la línea base.
- Commit de procedencia, hashes del código y versiones Python/pdfplumber/
  pdfminer.six/pypdf. Los cambios de código o entorno se informan por separado:
  una refactorización puede cambiarlos conservando exactamente la extracción.

Referencia: 228 páginas contabilizadas (213 de contenido, 15 excluidas), 146
secciones, 1.647 párrafos, 92 tablas, 383 filas y 62 candidatas a continuación.
Seis tablas gráficas siguen fuera del índice textual. El índice local conserva
498 unidades y 779 vistas. Esto no acredita comprensión de diagramas ni revisión
humana; el fallo histórico de recuperación RIC-06 sigue pendiente.

## Comprobar antes y después de cada cambio

Desde `backend/`, con el entorno de la raíz:

```sh
../.venv/bin/python -m scripts.check_extraction_baseline
```

Lee el PDF registrado y realiza la extracción completa en memoria. No llama a
proveedores, no carga modelos, no escribe Supabase y no cambia archivos de
extracción o índices. Guarda un informe JSON técnico nuevo en
`docs/rag_runs/extraction_baseline/` (ignorado por Git). No es un experimento de
métricas RAG ni reemplaza las exportaciones JSON/CSV/PDF de clase 09.

La salida termina con código 0 solo si la extracción y todas las referencias
locales coinciden. Informa secciones cambiadas, nuevas o ausentes. Una diferencia
fuera de las secciones, por ejemplo en metadatos, también cambia el hash global.
Fuente o perfil diferentes se rechazan antes de extraer. Falta de archivos,
excepciones y diferencias no se convierten en una aprobación.

`--output /ruta/nuevo_informe.json` elige un informe nuevo; los archivos existentes
no se sobrescriben. Para las pruebas específicas:

```sh
../.venv/bin/python -m unittest test.test_extraction_baseline test.test_external_ingestion test.test_external_chunking
```

## Cómo se fijó la referencia

```sh
../.venv/bin/python -m scripts.check_extraction_baseline --create
```

La creación exige que la extracción nueva coincida byte a byte con el JSON
guardado y con el hash del informe histórico `docs/ricoh_extraction_validation.json`.
La referencia se escribe con creación exclusiva: repetir el comando no puede
reemplazarla. No ejecutar `--create` para hacer que una regresión desaparezca.

Si un cambio deliberado mejora el contenido, conservar v1, revisar las diferencias
y definir expresamente una nueva referencia y sus criterios. El comando actual
de creación sigue anclado a la extracción histórica; no aprueba automáticamente
una extracción diferente ni pretende resolver el versionado futuro.

Los PDF/índices/extracciones deben estar disponibles en las rutas registradas.
Los índices y extracciones están ignorados por Git: la línea base contiene sus
huellas, no un respaldo. En un clon nuevo hay que preparar los datos locales
según las guías de extracción y recuperación antes de comprobarlos. No se
descargan ni regeneran automáticamente al verificar.

## Validación del paso 1 — 24-10-2026 (America/Bogota)

- 24 pruebas específicas correctas: 18 existentes y seis nuevas de línea base.
- Creación desde una extracción completa y segunda extracción independiente:
  SHA-256 idéntico a la referencia histórica, sin secciones ni referencias cambiadas.
- Controles CLI de creación repetida e informe sobre la propia referencia:
  ambos rechazados con código 2 y hash de línea base intacto.
- Informe local de comparación:
  `docs/rag_runs/extraction_baseline/20261025T023423132332Z.json` (hora UTC).
- Sin llamadas a proveedores, generación de embeddings o cambios de fuente,
  perfil, extracción guardada e índices. No se repitió la suite general/API;
  esta validación corresponde al nuevo comprobador local.

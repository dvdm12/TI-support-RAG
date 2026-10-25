# Adaptadores PDF — paso 4

`src/rag/pdf_adapters.py` encapsula los objetos y operaciones de `pypdf` y
`pdfplumber`. `external_ingestion.py` conserva las reglas documentales y el
pipeline, sin importar esas bibliotecas ni acceder a sus objetos internos.

| Interfaz / dato común | Implementación predeterminada | Responsabilidad |
|---|---|---|
| StructureDocument | PypdfStructureAdapter | Cifrado, número de páginas y marcadores como datos comunes. |
| OutlineEntry | Conversión desde destinos de pypdf | Título, página PDF desde 1, coordenada superior y antecesores. |
| LayoutDocument | PdfplumberDocumentAdapter | Recorrido de páginas adaptadas dentro del contexto del documento. |
| LayoutPage | PdfplumberPageAdapter | Dimensiones, caracteres/imágenes, líneas, selección geométrica, regiones, tablas y cierre de página. |
| TableSnapshot | Conversión desde tablas de pdfplumber | Cuadrícula original, columnas y coordenadas de tabla/filas, sin métodos de la biblioteca. |
| PDFBackends | Dos factories de context managers | Inyección explícita de lectores de estructura y layout. |

Las interfaces son Protocol de Python. Las bibliotecas se importan de forma
diferida al abrir el contexto correspondiente. Los contextos predeterminados
cierran el stream de pypdf y el documento pdfplumber también ante excepciones;
el pipeline conserva el cierre de cada página procesada.

## Uso y compatibilidad

La llamada existente no cambia:

```python
result = extract_real_document(manifest, document_id)
```

Para inyectar implementaciones que cumplan las interfaces:

```python
from src.rag.pdf_adapters import PDFBackends

backends = PDFBackends(open_structure=mi_contexto_estructura,
                       open_layout=mi_contexto_layout)
result = extract_real_document(manifest, document_id, backends=backends)
```

También admiten `backends=` las etapas `analyze_document` y `extract_pages`.
Los factories deben devolver context managers que liberen sus recursos; las
páginas deben implementar close. No hay selección automática por contenido ni
nuevos proveedores: esa decisión pertenece al paso de estrategias.

Los diccionarios de caracteres usan coordenadas x0/x1/top/bottom, size y
object_type; las líneas incluyen text, coordenadas y chars. Las vistas filtradas
deben conservar la identidad de los diccionarios de caracteres para contabilizar
exactamente los textos excluidos. Este requisito está probado y documentado para
un futuro backend; no se aplica una normalización que altere números o texto.

Los helpers públicos anteriores `outline_sections`, `page_tables` y `table_block`
siguen aceptando lectores, páginas y tablas nativos a través de funciones de
compatibilidad dentro del módulo de adaptadores. page_tables devuelve ahora
TableSnapshot, consumible por table_block. Los consumidores del extractor y
el Markdown no cambian; no se promete conservar la API privada de tablas nativas.

El perfil Ricoh sigue decidiendo exclusiones, límites y correcciones de tablas;
el adaptador ejecuta las operaciones solicitadas. La cuadrícula conserva celdas
None, saltos de línea y coordenadas. Los IDs, secciones, advertencias y flags
siguen siendo responsabilidad del extractor. No se altera schema_version=1.

## Verificación

```sh
# Desde backend:
../.venv/bin/python -m unittest test.test_pdf_adapters test.test_extraction_pipeline test.test_extraction_contracts test.test_extraction_baseline test.test_external_ingestion test.test_external_chunking
../.venv/bin/python -m scripts.check_extraction_baseline
```

Ocho pruebas nuevas comprueban:

- Pipeline completo con interfaces en memoria y las importaciones de pypdf y
  pdfplumber bloqueadas; la fuente sintética de esa prueba no se presenta como PDF real.
- Liberación de contextos y páginas en fallos de estructura o layout, sin
  ocultar la excepción original ni devolver resultados parciales aceptados.
- Conversión de marcadores, preservación de celdas ambiguas y geometría.
- Página real Ricoh 185: identidad de caracteres entre vistas y tablas como
  datos comunes con el mensaje Job Suspended conservado.

El 24-10-2026 (America/Bogota) pasaron 50 pruebas específicas y la suite unitaria
completa: 302 correctas, sin nueva ejecución de pruebas API. La extracción
completa conserva exactamente el hash
`ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44`,
sin secciones ni nueve referencias locales modificadas. La línea base permanece
congelada; el cambio de código external_ingestion.py se informa por separado.
Informe técnico local ignorado:
`docs/rag_runs/extraction_baseline/20261025T032202977078Z.json` (hora UTC).

No se añaden OCR, interpretación gráfica, búsquedas, embeddings o escrituras
Supabase. La equivalencia es una regresión de Ricoh, no una evaluación de calidad
semántica ni una prueba sobre nuevos tipos de documentos.

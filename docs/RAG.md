# RAG documental de TI-support-RAG

El recorrido nuevo es imagen opcional → OCR → clasificación `SolicitudTI` →
recuperación → contexto etiquetado → generación `RespuestaRAG` → validación de
citas → decisión local → evidencia. La clasificación y la respuesta documental
son contratos separados. La categoría no cambia por falta de cobertura.
El prompt documental activo es `prompts/rag_v2.md`; `rag_v1.md` conserva la
primera versión utilizada en las pruebas. La selección es explícita e independiente
del prompt versionado de clasificación.

## Preparación

Desde la raíz del repositorio, activar el entorno antes de instalar o ejecutar:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s test
```

Las importaciones y los mocks no cargan secretos. La descarga inicial del modelo
requiere Internet; se utiliza CPU. El corpus simulado está en `data/corpus/v2/`:
7 PDF, 14 páginas y 35 secciones. El manifiesto verifica los originales. Las
preguntas de evaluación están en `cases/rag_questions.json`, fuera del corpus.

## Comparación e indexación

```bash
python -m scripts.compare_chunking
python -m scripts.index_manuals --strategy sections --output data/indexes/sections
```

La comparación evalúa cortes por caracteres sin solapamiento (`characters`), con
solapamiento (`overlap`) y por párrafos dentro de secciones (`sections`). Corpus,
preguntas, modelo, revisión y k permanecen constantes. Los cortes finales respetan
el presupuesto de tokens: cuando un corte por caracteres lo supera se acorta,
por lo que no se promete una longitud fija en caracteres.

Se utiliza `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, con
384 componentes, vectores normalizados y coseno. Se registra una revisión SHA
exacta y se consulta `max_seq_length` efectivo. No se truncan entradas de forma
silenciosa. Las consultas usan la misma representación. Para reproducir una
comparación, pasar `--revision <SHA-de-40-caracteres>` a ambos comandos.

Los valores iniciales son 420 caracteres, 80 caracteres de solapamiento para la
variante correspondiente y 80 tokens incluyendo encabezado. Son configurables
en `index_manuals`; `sections` es el valor inicial, no una ganadora demostrada.
El solapamiento efectivo se limita a la mitad de un corte acortado por tokens,
para garantizar progreso; inspeccionar los cortes registrados al comparar.

`docs/rag_comparison.json` conserva configuración, corpus_id por variante,
cortes reales, tamaños, duplicados exactos, Top-k, condiciones y revisión
pendiente. Las coincidencias de sección y condición son controles automáticos,
no una evaluación semántica completa. El notebook
`notebooks/rag_chunking_comparison.ipynb` permite revisar o repetir el experimento.

Cada índice guarda `records.json`, `vectors.npy` y `config.json`. `corpus_id`
incluye una huella de registros, representación y vectores. La recarga comprueba
integridad, tokens y muestras recalculadas. Los índices generados no se versionan
en Git por defecto; se pueden reconstruir con la configuración y las fuentes.

## Supabase

Ejecutar `supabase/migrations/20261014_documentary_rag.sql` en el SQL Editor de
un proyecto de práctica. La migración utiliza la tabla `public.clase08_fragmentos`,
`extensions.vector(384)`, clave primaria `(owner_id, corpus_id, chunk_id)` y RPC
`public.clase08_buscar_fragmentos`. Usa búsqueda exacta, sin HNSW o IVFFlat.

La extensión debe estar en `extensions`. Si ya está en otro esquema, revisar la
instalación; no eliminarla para forzar el ejemplo. `CREATE TABLE IF NOT EXISTS`
no adapta automáticamente una tabla previa incompatible: revisar su esquema
antes de aplicar esta migración.

Crear un usuario confirmado en Supabase Auth y configurar en `.env` o en el
entorno los nombres de `.env.example`. Una clave publicable identifica la app,
pero el propietario procede de la sesión autenticada. No usar `service_role`.
RLS permite SELECT, INSERT y UPDATE de filas propias; no concede DELETE ni
acceso anónimo. La RPC usa `SECURITY INVOKER` y filtra propietario, corpus,
modelo y revisión. No filtra categoría ni estrategia: las variantes tienen
corpus_id distintos. No desactivar RLS si no aparecen resultados.

```bash
python -m scripts.index_manuals --existing --output data/indexes/sections --upload
```

Después de la carga, verificar filas, RPC y persistencia con un segundo cliente
autenticado del mismo usuario, sin volver a cargar ni recalcular embeddings:

```bash
python -m scripts.verify_supabase
```

El comando contrasta IDs y textos con el índice local y comprueba el mismo
ranking desde dos clientes. Usa el vector del primer fragmento como sonda; la
evaluación semántica de preguntas se realiza por separado. No certifica el
aislamiento entre usuarios: esa comprobación requiere otra identidad de Auth.

La carga hace upsert por la clave compuesta, en lotes de 50. Es repetible, pero
no retira construcciones antiguas. Si un lote falla, puede haber carga parcial:
repetir la misma construcción. No se borra el historial automáticamente.

## Consulta

Con un índice cargado y credenciales de Supabase/Groq:

```bash
python -m scripts.query_rag "Me aparece un error 403. ¿Mi cuenta está suspendida?"
python -m scripts.query_rag "No puedo ingresar al Portal TI" --image docs/multimodal/multimodal_demo.png --ocr-engine tesseract
```

El comando consulta la construcción indicada por `--index`; no recalcula los
embeddings del corpus. Guarda una traza en `docs/rag_runs/latest.json`. Pasar
`--pdf docs/rag_runs/consulta.pdf` para registrar el resultado con `PDFReport`.
También se añadió una sección RAG opcional, desactivada, al notebook principal;
sus celdas anteriores se conservaron.

Sin Supabase se puede usar la recuperación exacta local con Groq:

```bash
python -m scripts.query_rag "¿Qué hago ante un error 403?" --repository local
```

Para verificar el flujo sin credenciales, después de construir el índice:

```bash
python -m scripts.query_rag "No puedo entrar" --repository local --mode mock --mock-type ambiguo
```

El mock usa una clasificación predeterminada identificada por `--mock-type` y
una respuesta documental explícitamente simulada. No evalúa comprensión de
texto libre ni calidad del modelo. Los tests usan vectores de control para
verificar contratos sin descargar modelos; no se reportan como embeddings
semánticos reales.

## Contexto, decisiones y revisión

El presupuesto inicial del contexto es 6000 caracteres del JSON serializado,
incluidos pregunta, clasificación y metadatos. No es un conteo de tokens del
generador. Se admiten solo pasajes completos y se registran los omitidos. Si
ninguno cabe, se devuelve un límite de contexto explícito sin llamar a Groq.
Una pregunta demasiado larga para el embedder se registra como fallo de entrada
en recuperación; no se recorta sin avisar.

`RespuestaRAG` distingue `respondida`, `parcial`, `aclaracion` y
`evidencia_insuficiente`. Se verifica forma estricta, coherencia, citas existentes
y coincidencia entre menciones y lista. El resultado expone
`semantic_support_review=PENDIENTE`: la existencia de una cita no demuestra que
respalde la afirmación. No hay umbral universal de similitud ni confianza RAG
inventada. La confianza de clasificación sigue siendo la propuesta del modelo.

Las decisiones existentes de intervención humana y aclaración conservan
precedencia. Si la clasificación permite continuar, el estado documental añade
`OK_RESPUESTA_PARCIAL` y `OK_EVIDENCIA_INSUFICIENTE`. Los errores de proveedor,
sesión, falta de filas o incompatibilidad se registran como `ERROR_TECNICO` con
etapa de fallo; un contrato/cita inválido produce `ERROR_FORMATO` y no se acepta
la respuesta cruda. Los diagnósticos externos no incluyen cuerpos de error ni
credenciales.

La traza guarda clasificación, candidatos, catálogo de fuentes, contexto enviado,
omisiones, parámetros, configuración, salida aceptada, citas y tiempos por
etapa. Los tokens informados por Groq se conservan, sin sustituirlos por una
estimación. Usar solo consultas e imágenes autorizadas y revisar las trazas
antes de compartirlas.

## Comprobación remota pendiente o reproducible

1. Aplicar la migración y confirmar RLS, grants y RPC.
2. Cargar una construcción dos veces con el mismo usuario: comprobar cantidad
   e identidades mediante la tabla; las repeticiones no deben añadir filas.
3. Ejecutar una consulta con un cliente nuevo sin `--upload` y comparar IDs,
   textos y puntajes. La indexación no se ejecuta durante la consulta.
4. Con otro usuario confirmado, consultar el mismo corpus_id: no debe ver las
   filas del primero. Intentar insertar una fila con el owner_id del primero
   debe ser rechazado. Nunca usar una clave administrativa para esta prueba.
5. Probar los casos de `cases/rag_questions.json`, además de citas inválidas,
   condiciones, contexto malicioso y errores técnicos. Revisar afirmaciones
   contra las fuentes y registrar un acierto y una limitación.

Las pruebas con adaptadores simulados y el chequeo textual de SQL no sustituyen
esta comprobación contra PostgreSQL/RLS. Los resultados ejecutados y el alcance
disponible se registran en `docs/rag_validation.md`.

Referencias de implementación: [Sentence Transformers](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html),
[Supabase Auth](https://supabase.com/docs/reference/python/auth-signinwithpassword),
[upsert](https://supabase.com/docs/reference/python/upsert) y
[Groq Structured Outputs](https://console.groq.com/docs/structured-outputs).

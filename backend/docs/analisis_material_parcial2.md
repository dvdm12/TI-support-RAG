# Análisis del material de clases para el segundo corte

Fecha de revisión: 2026-10-14. Rama: `codex/implement-embeddings`.

Este documento registra una revisión del material local y su relación con el proyecto. No demuestra una ejecución del RAG ni una conexión a Supabase. Las propuestas de organización son recomendaciones de implementación; no son una rúbrica oficial del curso.

## 1. Material localizado y alcance de la revisión

El material está en el directorio padre del repositorio, `Obsidian Vault/`. Se revisaron los antecedentes de las clases 02–04 y se profundizó en los laboratorios de las clases 06–07 y los cuatro recursos de `parcial2/`:

| Recurso | Aporte principal |
|---|---|
| `notebooks/Clase_02_Demo_Tokens_Contexto_Alumno.ipynb` y `Mesa_de_ayuda_lab.ipynb` | Tokens, contexto, temperatura, medición y comparación controlada |
| `Clase_03_RevealJS/index.html` y notebook de clase 03 | Prompt versionado, salida estructurada, validación, decisión y trazas |
| Presentación y notebook de clase 04 | OCR/multimodalidad y herramientas con argumentos validados; separación entre documentos y datos operativos |
| `Clase_06_Fundamentos.md` y demos de clase 06 | Embeddings, similitud coseno, Top-k, paráfrasis y límites de cobertura |
| `Clase-07/Clase_07_Mesa_Ayuda_TI_Ingestion_Indice.ipynb` y su bitácora | Corpus TI, fragmentación, metadatos, índice local y recarga |
| `parcial2/Clase_08_RevealJS/index.html` | Arquitectura RAG, fuentes, permisos, fidelidad y evidencia del avance |
| `parcial2/Clase_08_Demo_Colab_RAG_Supabase_Groq.ipynb` | Implementación docente del recorrido completo y lectores opcionales |
| `parcial2/Clase_08_Supabase_Setup.sql` | Tabla vectorial, RLS y función de recuperación |
| `parcial2/Guia_Supabase_Vector_Colab.md` | Preparación de Supabase, credenciales, uso y diagnóstico |

Se comprobó que los archivos principales dentro de `Clase_08_RAG.zip` son idénticos a sus copias descomprimidas. Las bibliotecas de RevealJS son dependencias de presentación, no lógica del proyecto. El notebook duplicado de clase 02 tiene el mismo contenido de celdas extraído que la otra copia.

Las diapositivas citan `Clase_07_Fundamentos.md`, `Clase_08_Fundamentos.md` y el plan maestro, pero esos documentos no aparecen en el material inventariado. La presentación declara que el avance de clase 08 es incremental y no sustituye la evaluación completa del segundo corte. No se infiere una rúbrica que no está disponible.

## 2. Evolución del sistema

La continuidad es: experimentación con inferencia → clasificación validada → modalidad/herramienta → recuperación semántica → ingestión e índice → generación con evidencia.

El segundo corte añade dos recorridos separados:

```text
Construcción:
fuentes → extracción revisada → limpieza → fragmentación
        → metadatos + embeddings → persistencia

Consulta:
pregunta → embedding → recuperación autorizada → contexto etiquetado
         → Groq → validación → respuesta y fuentes → traza
```

Una pregunta nueva genera su propio vector y reutiliza los vectores del corpus. Un cambio de modelo, revisión o preparación exige revisar la compatibilidad y reconstruir el índice cuando corresponda.

## 3. Representación y fragmentación

El material utiliza `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vectores de 384 componentes, normalización y similitud coseno. El generador es otro componente: `openai/gpt-oss-20b` mediante Groq.

La clase 07 registra la revisión efectiva del modelo y propone un presupuesto experimental de 80 tokens por fragmento, con 12 tokens de solapamiento. La presentación menciona 128 tokens como longitud publicada del modelo; el código debe comprobar `max_seq_length` efectivo y contar con su tokenizador. Los 80 tokens no son un límite universal ni equivalen a 80 palabras.

Se comparan dos estrategias bajo las mismas consultas y configuración:

- Ventanas sobre el cuerpo de cada sección, con solapamiento.
- Párrafos como unidades naturales; los párrafos largos se subdividen con ventanas.

El título y la sección se incorporan al texto vectorizado y consumen presupuesto. El conteo final incluye tokens especiales. Deben mantenerse juntas, en lo posible, las condiciones, negaciones y consecuencias del procedimiento.

La selección inicial `parrafos` del laboratorio es una configuración de partida. La bitácora deja pendiente justificarla con resultados. No debe presentarse como una estrategia ya demostrada superior.

Cada fragmento conserva al menos `chunk_id`, `document_id`, texto, fuente, sección, versión y hash de origen. La fila de la matriz y el registro deben seguir asociados después de guardar, cargar y transferir el índice.

## 4. Contrato del índice y diferencia entre clases 07 y 08

La clase 07 adaptada guarda `vectores.npy`, `registros.json` y `configuracion.json` en `indice_clase07_mesa_ayuda/`. Sus tres documentos TI están como cadenas dentro del notebook: acceso, redes y aplicaciones.

La clase 08 espera un ZIP con estas rutas exactas:

```text
indice_clase07/vectores.npy
indice_clase07/registros.json
indice_clase07/configuracion.json
corpus_clase07/*.md
```

El laboratorio adaptado no exporta ese ZIP ni los originales Markdown. Por tanto, no se conecta directamente al demo de clase 08. Debemos añadir una exportación compatible o diseñar un cargador propio documentado. Al exportar, el hash debe corresponder exactamente a los bytes del original conservado.

El cargador docente comprueba tamaño del ZIP, tamaño descomprimido, nombres repetidos, cantidad de registros, campos obligatorios, dimensión, tipo numérico, valores finitos, norma unitaria, identidad única y hashes de fuentes. También carga la revisión registrada y recalcula muestras del primer y último fragmento para contrastarlas con sus vectores. Esta comprobación por muestras no certifica todas las filas.

El identificador de corpus combina un nombre base y una huella de la construcción. Así se distinguen índices diferentes y se evita mezclar versiones durante la consulta.

## 5. Persistencia y recuperación en Supabase

El SQL utiliza PostgreSQL con pgvector y una tabla `clase08_fragmentos`. Cada fila guarda propietario, corpus, identidad del fragmento, texto, metadatos, configuración y `vector(384)`.

La clave primaria es `(owner_id, corpus_id, chunk_id)`. La carga hace `upsert` en lotes de 50. Repetir la carga actualiza las mismas identidades; no elimina versiones anteriores ni define por sí solo una política de retiro.

La búsqueda es exacta. No se crean índices vectoriales HNSW o IVFFlat. La RPC `clase08_buscar_fragmentos` filtra por propietario, corpus, modelo y revisión; ordena por distancia coseno y devuelve `1 - distancia` como similitud. Usa Top-3 por defecto, limita la cantidad a 1–10 y desempata por `chunk_id`.

El control de acceso reside en SQL y RLS. La práctica usa clave publicable y sesión de Supabase Auth, con lectura, inserción y actualización sobre filas propias. La RPC es `security invoker`; no hay acceso anónimo ni permiso de borrado. Esta configuración no crea un corpus compartido por todo el equipo: para eso haría falta un modelo de pertenencia y políticas adicionales.

La persistencia se comprueba con otro cliente y la misma identidad, consultando sin volver a hacer `upsert`. La guía también explica cómo repetirlo desde otra sesión de Colab.

## 6. Generación, contrato y citas

El demo define `RespuestaRAG`, con validación estricta y campos:

- `estado`: `respondida`, `parcial`, `aclaracion` o `evidencia_insuficiente`.
- `respuesta`: texto para el usuario.
- `citas`: etiquetas utilizadas.
- `limitacion`: explicación de lo que falta cuando corresponda.

El contrato ejecutable usa `limitacion`; algunas diapositivas muestran un contrato conceptual con `aclaracion`. No son esquemas intercambiables sin adaptación.

Los candidatos reciben etiquetas `F1`, `F2`, etc. Se envían pregunta, textos y procedencia a Groq. El validador exige respuesta no vacía, ausencia de citas repetidas, etiquetas pertenecientes al contexto y coincidencia entre la lista de citas y las menciones del texto. Los estados `respondida` y `parcial` necesitan citas; los estados distintos de `respondida` necesitan una limitación.

Estos controles verifican estructura y referencias. Todavía se debe revisar si cada afirmación está respaldada por el fragmento citado. Una cita existente no valida un plazo inventado.

Los puntajes de similitud sirven para ranking. No equivalen a certeza ni justifican un umbral universal para responder. La confianza declarada por el clasificador y la similitud vectorial son señales diferentes.

La generación del demo es acotada: temperatura 0, `reasoning_effort="low"`, máximo de 1536 tokens de completado, timeout de 30 segundos y sin reintentos automáticos. Verifica terminación completa y rechazo antes de aceptar la salida. Las versiones de bibliotecas indicadas en el notebook son referencias del material; su disponibilidad y compatibilidad no se verificaron instalándolas en esta revisión.

## 7. Lectores opcionales y límites

El anexo convierte fuentes a Markdown y conserva original, texto derivado, hashes y ubicaciones. No genera embeddings ni carga Supabase. El ZIP del corpus extraído debe pasar primero por la ingestión; no es el ZIP del índice.

Los ejemplos cubren PDF textual por página, PDF con OCR, Excel por hoja/fila y Word por párrafo/tabla. Están desactivados por defecto. Sus límites incluyen archivos de 10 MB, PDF de hasta 20 páginas y Excel de hasta 200 filas y 20 columnas.

Las fórmulas de Excel se marcan como no evaluadas. Word no ofrece páginas fiables mediante este lector y omite imágenes, cuadros de texto, encabezados, pies y tablas anidadas. El OCR debe revisarse frente al original, especialmente cifras, nombres y negaciones. El OCR documental de ingestión y el OCR de una captura adjunta a una consulta tienen funciones diferentes.

## 8. Pruebas y evidencia esperada

La clase 08 pide adaptar el corpus, permitir preguntas nuevas y conservar al menos:

| Caso | Comportamiento a comprobar |
|---|---|
| Pregunta respondible | La regla necesaria llega al contexto y respalda la respuesta |
| Paráfrasis | Recupera y conserva el mismo significado |
| Consulta ambigua | Pide la precisión que cambia el procedimiento |
| Fuera de cobertura | Reconoce falta de evidencia aunque exista Top-k |
| Información parcial o dinámica | Explica lo documentado y no inventa el dato ausente |
| Error técnico | Se distingue de evidencia insuficiente |
| Persistencia | Otro cliente recupera el índice sin volver a cargarlo |

También conviene mantener pruebas negativas de citas inventadas, respuesta sin respaldo, contexto malicioso y compatibilidad de índices. Esta ampliación es una recomendación basada en los controles estudiados.

La traza debe conservar corpus, configuración, consulta, candidatos con puntajes, contexto utilizado, prompt, modelo, parámetros, respuesta, validación, citas, tiempos y consumo reportado. El demo mide la generación, pero no todos los tiempos por etapa: ampliar esos registros sería útil al integrarlo.

La bitácora debe enlazar fuentes, construcción, configuración, ejecución, comparación de fragmentación, respuesta útil y fallo o limitación. Los resultados de ejemplos controlados no son métricas generales de exactitud.

## 9. Evidencia de ejecución disponible

La bitácora de clase 06 registra resultados, incluyendo cinco aciertos Top-3 en cinco pruebas controladas. El notebook adaptado guardado no conserva salidas ni contadores de ejecución; los resultados están documentados en la bitácora, no se reprodujeron aquí.

La clase 07 tiene dos celdas con contador de ejecución y una salida `KeyboardInterrupt`. Su bitácora declara pendientes los resultados completos, comparación y confirmación de persistencia.

El demo de clase 08 no guarda salidas ni contadores de ejecución. No se encontró en el material inventariado un ZIP exportado del índice de clase 07. No se verificaron servicios remotos, credenciales, descargas de modelos ni respuestas reales de Groq durante este análisis.

## 10. Aplicación a TI-support-RAG

El proyecto ya tiene cliente Groq, OCR, validación, reglas de clasificación, evaluación y reportes. Falta incorporar corpus documental, ingestión, embeddings, almacenamiento, recuperación, contexto RAG, contrato de respuesta y validación de citas.

Una organización propuesta es añadir módulos de ingestión, fragmentación, embeddings, almacenamiento y recuperación dentro de un paquete `src/rag/`; un contrato `schemas/rag_response_v1.py`; un prompt RAG independiente; corpus y manifiesto documentados; y SQL de Supabase versionado. Los nombres son propuestas, no decisiones implementadas.

El contrato `SolicitudTI` sirve para clasificación y no contiene respuesta documental ni citas. Se recomienda conservarlo y añadir `RespuestaRAG` como contrato separado. No es necesario exigir una clasificación previa a toda pregunta para demostrar el recorrido RAG básico.

El cliente actual tiene el esquema y modelo de clasificación incorporados. Necesitará admitir explícitamente el contrato RAG. La selección automática del último `system_vN` también está orientada al clasificador: el prompt RAG debe tener selección explícita para evitar mezclar tareas.

Antes de integrar, conviene desacoplar las credenciales de la importación de configuración y corregir las pruebas desactualizadas detectadas en la revisión anterior. La ingestión local y las pruebas de recuperación no deberían exigir una clave Groq.

Orden de trabajo recomendado:

1. Materializar y documentar las fuentes TI, su autorización y versiones.
2. Implementar fragmentación, representación y persistencia local reproducibles.
3. Comparar ambas estrategias y registrar consultas, evidencia y límites.
4. Definir y comprobar la transferencia del índice a Supabase con permisos.
5. Integrar recuperación, contexto, contrato RAG, generación y citas.
6. Verificar pruebas, recarga desde otro cliente y trazas del recorrido completo.

La primera entrega en la rama de embeddings puede terminar en un índice consultable y comprobable. El objetivo del avance de clase 08 abarca además la respuesta generada con fuentes y la persistencia remota.

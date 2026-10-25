# Informe de continuidad — TI-support-RAG

Actualizado: 25 de octubre de 2026 (America/Bogota).
Repositorio: `/home/dvdm12/Documents/Obsidian Vault/TI-support-RAG`.

## Estado actual para continuar — leer primero

Esta sección prevalece sobre el historial que sigue. Las rutas antiguas del
historial, como `src/` o `docs/`, ahora corresponden a `backend/src/` y
`backend/docs/`, salvo las migraciones, ubicadas en `infra/supabase/`.
No contiene secretos. No releer ni ejecutar integraciones históricas por defecto.

### Actualización: Corrección E06 25-10-2026 (sin commit)

Causa: el clasificador respondía la pregunta dentro de `resumen` (>240 caracteres);
system_v7 no declaraba el límite y RESPONSE_SCHEMA no tenía maxLength.
- prompts/system_v8.md: una regla «resumen: 10-240 caracteres; reformula la solicitud,
  no la respondas…» (sustituye la línea equivalente de v7; v7 se conserva).
- src/groq_client.py: resumen con minLength 10 / maxLength 240 (Groq lo acepta en strict).
- Presupuesto del clasificador 661 → 690/1000 tokens. 5 pruebas nuevas en
  test_groq_client.py; 463 unitarias y 26 API correctas.
- Experimento previo: E06 3/3 válido con prompt solo y 3/3 con prompt + maxLength.
- Imagen f5118f3a626c (healthy); rollback en tag rollback-69245ccd8178.
- Repetición de los 13 casos de desarrollo: 13/13 HTTP 200, estado documental
  esperado 13/13, categoría 12/12 (E10 sin categoría esperada); resúmenes 32–146
  caracteres. E06 responde con ACS-03 citado. Evidencia phase_b_v8.json.
- E10 queda OK_PIDE_ACLARACION por confianza 0.0 < 0.60 con datos_faltantes vacío
  (regla previa de decision.py; explica también la observación histórica de 403).

### Actualización 25-10-2026: validador de salida estricto (sin commit)

Decisión del usuario: `confianza` estricta y `datos_faltantes` sin cadenas vacías.
- backend/schemas/request_v1.py: confianza StrictFloat (enteros 0/1 válidos;
  rechaza strings, booleanos, NaN e infinito) y elementos de datos_faltantes con
  min_length=1 tras recortar espacios.
- backend/src/validator.py: errores de raíz sin prefijo ": " vacío.
- test/test_validator.py: 25 pruebas; validator.py y request_v1.py al 100 % de
  líneas y ramas; 14/14 mutantes detectados. Suite 458 unitarias y 26 API correctas.
  Mocks actuales siguen válidos. RESPONSE_SCHEMA de Groq sin cambios (ya number).
- Contenedor reconstruido 25-10-2026: imagen 69245ccd8178 (healthy); validador estricto
  comprobado dentro del contenedor; health, docs y openapi 200. Imagen previa etiquetada
  ti-support-rag-backend:rollback-a414431ee034. Sin consultas Groq/Supabase en la verificación.

### Actualización 25-10-2026: paso 8 completado (sin commit)

Prevalece sobre los pendientes del paso 8. Publicación previa confirmada con Git:
HEAD 7be846f sincronizado con origin/codex/backend-infra-ricoh-local.

- Nuevos: backend/src/rag/unit_verification.py, scripts/verify_units_retrieval.py,
  test/test_unit_verification.py (55), test/test_verify_units_retrieval.py (21) y docs/UNIT_RETRIEVAL_VERIFICATION.md.
  evaluate_ricoh_local reutiliza `relevant`; rangos por caso idénticos al informe.
- Ricoh: extracción nueva idéntica a la registrada, 498 unidades idénticas e
  índice coincidente; 194.084 caracteres del PDF contabilizados, 0 pérdidas;
  1.647 párrafos + 364 filas en una unidad, 19 filas gráficas excluidas.
- 12 casos en español: 0 pérdidas de extracción/unidad/fragmento. Fallos solo de
  búsqueda: RIC-06 (todas) y RIC-09 (semantic/hybrid). RIC-06 sigue abierto.
- 433 unitarias correctas; sin nueva suite API, Groq, Supabase ni índices.
  Evidencia local ignorada: backend/docs/rag_runs/unit_retrieval/check_20261025/.
- Sonda de los diez PDF candidatos (25-10): 0/10 completan el pipeline genérico.
  Seis sin marcadores; HP y LibreOffice numeran el pie junto al título; SEG-BACKUP
  tiene marcadores fuera del rango numerado. Requiere cambio de extractor/perfil,
  no hecho. Evidencia local en category_pdf_discovery/20261024/extraction_probe_20261025/.
- Cambios sin commit/push. Siguiente según solicitud: paso 9 o soporte de candidatos.

### Publicación solicitada de la revisión del extractor

El usuario autorizó generar un commit y actualizar la rama remota actual.
Esta revisión reúne los pasos 1–7, sus pruebas y guías, la línea base congelada,
la evaluación de PDF públicos y el catálogo de candidatos por categoría.
La base publicada anterior es c5826c0; el hash de esta revisión se obtiene de
Git para evitar una referencia circular dentro del propio commit.

- Fetch previo: HEAD y origin/codex/backend-infra-ricoh-local sin divergencia.
- Se repitieron las 357 unitarias correctamente antes de preparar la publicación.
  No nueva suite API, Supabase, modelos ni reserva.
- Los archivos ignorados, incluidos los diez PDF descargados, informes JSON/CSV/
  PDF extensos, extracciones e índices, permanecen locales. No forzar su inclusión.
  Los PDF candidatos no se trasladaron a manuals/ como parte de este commit.
- Las afirmaciones de 'sin commit/push' de secciones anteriores son historial
  del momento de cada tarea, no una prohibición de publicar esta revisión.
- Validar hash y sincronización remota con Git; esta nota por sí sola no acredita
  que la operación de push haya terminado. Paso 8 continúa pendiente.

### Actualización 24-10-2026: PDF candidatos por las siete categorías

Petición posterior: encontrar en la web fuentes relevantes para resolver
problemas de hardware, software, redes, cuentas, seguridad, acceso y otros.
La búsqueda se completó; no corresponde repetirla sin nueva necesidad.

- backend/docs/PDF_CANDIDATES_BY_CATEGORY.md y registro
  backend/docs/fixtures/category_pdf_candidates_v1.json: 12 candidatos, diez
  PDF descargados/abiertos/verificados con SHA-256, 363 páginas totales y las
  siete categorías cubiertas. Hubo búsqueda de términos y revisión dirigida,
  no aprobación semántica completa de las 363 páginas.
- Fuentes verificadas: HP User Guide 2024 (inglés), LibreOffice 24.8 capítulos
  1 y 12, Cisco DHCP/Ping-Traceroute, Universidad Piloto contraseña/MFA 2026,
  INCIBE ciberataques/copias, Icesi cambio de dispositivo MFA y Sabaneta mesa
  de ayuda 2017. Los documentos y sus procedimientos conservan producto,
  versión y ámbito institucional; no adoptar contactos, permisos o SLA ajenos.
- MFA Icesi requiere acceso existente a la cuenta; no cubre pérdida total de
  MFA ni autorización HTTP 403. Quedan huecos para autorización de recursos,
  altas/bajas, aplicaciones específicas y Wi-Fi del entorno real. Otros apoya
  aclaración/derivación, no es una categoría para ocultar casos clasificables.
- Dos descargas pendientes por validación TLS: IDEP políticas/VPN y DNP mesas
  de ayuda 2025. Fuentes localizadas en web; no afirmar copia local ni aprobación.
  No se desactivó verificación de certificados.
- Copias e inventario LOCAL IGNORADO:
  backend/docs/rag_runs/category_pdf_discovery/20261024/. El registro versionable
  conserva URL, hash, páginas, problemas cubiertos, límites y aprobación falsa.
- No se ejecutó pipeline completo ni se crearon unidades/embeddings/índices de
  estos candidatos. No transferirles los resultados de los seis PDF previos.
  No cambios a corpus académico, Ricoh, Supabase o clase09/reserva. Se verificaron
  las nueve referencias del baseline intactas. Sin nuevas suites/API, commit/push.
- Sigue pendiente el paso 8. Esta tarea fue descubrimiento documental.

### Actualización 24-10-2026: evaluación de PDF públicos completada

Esta actualización prevalece sobre el aplazamiento anterior: el usuario pidió
buscar PDF en la web y aplicar tests. La búsqueda y la evaluación ya se hicieron;
no hace falta pedirle documentos para repetir estas mismas pruebas.

- Seis originales descargados: health de Camelot, BERT de ACL, Attention arXiv
  v5 y linn/skew/rotated_skew de OCRmyPDF. Son cuatro contenidos independientes,
  con tres variantes de un mismo escaneado. Seis páginas seleccionadas revisadas;
  no todo el contenido de los artículos. Nada añadido al registro/corpus activo.
- Registro de URL/hash/versiones: backend/docs/fixtures/web_pdf_sources_v1.json.
  Runner offline backend/scripts/evaluate_web_pdfs.py; todos los hashes se
  comprueban antes y después. Transcripción OCR externa también fijada.
- Nueve controles por componente correctos. 24 celdas muestreadas de health
  coinciden; no se resolvió su encabezado multinivel ni se indexaron datos sin
  encabezados. BERT: 48/50 líneas por columna, anclas y 3.868 caracteres NFKC
  conservados. Corrección del comprobador para ligaduras ﬁ/ﬂ; sin cambio productivo.
  Perfil plano de tabla jerárquica se rechaza antes de forzar celdas.
- 0/6 completan el pipeline con perfil genérico: cinco sin marcadores;
  Attention sin número impreso en primera página. Requieren perfiles/estrategias
  adicionales; los controles de rechazo no son éxitos de ingestión completa.
- OCR siempre review/no indexable. Confianza 92,54–93,84 pero WER 47,89–48,68 %
  contra transcripción mantenida por OCRmyPDF, con artefactos y sin anotación
  humana nueva. Recuperación de tokens sin orden 94,74–95,79 %; se constató
  mezcla de columnas al leer instrucciones. Confianza no equivale a exactitud.
- Nueve pruebas nuevas; 105 específicas y 357 unitarias completas correctas.
  Sin nueva suite API ni sandbox histórico repetido. Ricoh reextraído idéntico:
  ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44;
  498 unidades con hash guardado y nueve referencias intactas.
- Guía backend/docs/WEB_PDF_EVALUATION.md. Evidencia LOCAL IGNORADA:
  backend/docs/rag_runs/web_pdfs/check_20261024/results_final/ con report.json,
  checks.csv, report.pdf, sondas y tres candidatos OCR. results/ es anterior y
  diagnóstica; no mezclar su falso fallo literal de ligaduras con el informe final.
- Pendientes de soporte: documentos sin marcadores, límites horizontales de
  secciones, encabezados multinivel y OCR con segmentación. Esta sesión mide
  límites y no los declara resueltos. No acredita calidad RAG ni revisión humana.
- No se cambió código de producción, PDF/perfil Ricoh, índices, Supabase o modelos.
  Sin commit/push. Clase09/reserva/RIC-06 intactos. Próximo paso solicitado: 8.

### Actualización 24-10-2026: paso 7 del extractor en alcance local completado

Prevalece sobre los pendientes históricos del paso 7. El usuario indicó que
otros PDF reales se probarán al finalizar, cuando los consiga. Esa evaluación
queda pendiente; no pedirlos otra vez ni buscarlos por iniciativa propia.
Pasos 8–9 pendientes; siguiente solicitado será verificar unidades/recuperación.

- column_text: geometría explícita, lectura por columna, cobertura de caracteres,
  cierre de párrafos entre columnas. Rechaza contenido sin región única y cambios
  de sección dentro de columnas incompatibles con el contrato actual. La
  validación de archivos guardados también comprueba geometría y orden.
- borderless_tables: solo región con límites explícitos de celdas, sin inferir
  filas/columnas ni cortar caracteres; cuadrícula/caracteres conservados.
  Cuadrículas explícitas cortas no se confunden con iconos pequeños.
- pdf_ocr_review.py reutiliza Tesseract local; scripts/review_pdf_scan.py genera
  candidato OCR separado con hash/página/raster/palabras/coordenadas/confianza.
  Siempre review y no indexable; requiere imagen sin texto nativo. Poppler y
  Tesseract spa/eng presentes en esta máquina, sin descargas. No fallback,
  interpretación tabular/figuras ni conversión automática a extracción v1.
- scripts/complex_pdf_samples.py y evaluate_complex_pdfs.py: cuatro fuentes PDF
  controladas reproducibles, cinco páginas. Nueve controles correctos; contraste
  visual de tablas, columnas, continuidad e imagen y lectura del informe PDF.
  OCR de control recupera cuatro textos completos, 12 palabras; confianza media
  95,58 no acredita exactitud semántica general. No son manuales externos reales.
- 22 pruebas nuevas, 96 específicas y 348 unitarias completas correctas. Pipeline
  completo probado con layouts especializados e índice de estructura inyectado.
  Sin nueva suite API ni repetición del sandbox histórico de pasos 1–3.
- Extracción real Ricoh completa idéntica al baseline,
  ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44;
  498 unidades con hash guardado, seis tablas excluidas, nueve referencias intactas.
- Guía backend/docs/COMPLEX_PDF_EVALUATION.md. Evidencia técnica LOCAL IGNORADA:
  backend/docs/rag_runs/complex_pdfs/check_20261024_final/ con JSON/CSV/PDF,
  muestras, trazas y candidato OCR. Mantener separados sintéticos, regresión
  Ricoh y futura evaluación documental nueva; no afirmar mejora de calidad RAG.
- Sin proveedores, embeddings, Supabase, cambios al PDF/perfil/índices activos,
  despliegue, commit ni push. Clase09/reserva/RIC-06 pendientes intactos.

### Actualización 24-10-2026: paso 6 del extractor completado

Esta sección prevalece sobre pendientes históricos de validaciones. Pasos 1–6
implementados; pasos 7–9 pendientes. No iniciar integración ni OCR por defecto.

- backend/src/rag/extraction_rules.py: reglas compartidas de tablas, representación
  de texto y elegibilidad. extraction_validation.py: especificaciones componibles
  de contrato, política de estrategias y orden/límites/texto de secciones.
- Informe extraction-validation-v1 con accepted/review/error, motivos,
  coordenadas de procedencia (página/sección/bloque) y listas de elegibilidad.
  Accepted acredita estructura, no revisión humana ni semántica correcta.
- Cualquier error bloquea construcción del documento. Tablas gráficas, glifos
  sin resolver y páginas text_only no aportan unidades ni contexto ambiguos.
  Una región text_only excluye conservadoramente toda la página. Continuaciones
  siguen en review; filas completas sin otros problemas permanecen independientes.
- Pipeline valida antes de retornar; evidence_units revalida entradas completas
  versionadas. Entradas históricas parciales en memoria reciben reglas por bloque.
  CLI agrega validation_report.json y su hash/estado/conteos en summary.json;
  ante fallo escribe diagnóstico exclusivo, relanza y no publica resultado parcial.
- 14 pruebas nuevas, 74 específicas y 326 unitarias completas correctas.
  Sin nueva suite API ni repetición del script sandbox de pasos 1–3.
- CLI real /tmp/ti-ricoh-validation-step6: 1.673 bloques accepted, 66 review,
  cero error; 1.733 elegibles, seis tablas gráficas excluidas. Extracción idéntica
  byte a byte a línea base, hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44.
  Las 498 unidades reconstruidas mantienen hash del índice guardado. Nueve
  referencias y baseline congelada intactos.
- Guía backend/docs/EXTRACTION_VALIDATION.md. Informe técnico LOCAL IGNORADO:
  backend/docs/rag_runs/extraction_validation/check_20261024.json.
- Sin proveedores/modelos, Supabase, cambios de PDF/perfil/datos/índices activos,
  despliegue, commit ni push. Clase09 y RIC-06 pendientes intactos.
  Siguiente paso solicitado: 7, evaluar nuevas muestras complejas.

### Actualización 24-10-2026: paso 5 del extractor completado

Prevalece sobre los pendientes de estrategias descritos más abajo. Solo se
implementó el paso 5; validaciones formales/casos nuevos/integración pendientes.

- backend/src/rag/extraction_strategies.py: NativeTextStrategy, RuledTableStrategy,
  TextOnlyTableStrategy e interfaces inyectables con política estricta de páginas
  y regiones. Configuración opcional extraction_profile.strategies; ausencia
  mantiene texto nativo/tablas con bordes y correcciones previas. Perfil Ricoh intacto.
- Selecciones explícitas con motivo; text_only registra diagnóstico review y
  conserva texto sin estructura tabular, nunca sustitución automática. Nombres
  no implementados (OCR), rangos/regiones superpuestos, cortes de tablas y
  redetecciones sin tabla/pérdida de palabras previamente recuperadas se rechazan.
- Prueba real Ricoh185 detectó que recortar de nuevo por bordes exactos podía
  perder una celda. Se reutilizan cuadrículas completas cuando settings no cambia;
  si hay redetección, pérdida de texto requiere revisión. Conservación de palabras
  no acredita relaciones semánticas correctas entre causas y soluciones.
- Trace opcional strategy_trace= fuera del resultado v1. CLI extract_real_manual
  guarda strategy_trace.json y cantidad/checksum en summary.json; la extracción
  guardada histórica no se sobrescribió para añadir esta traza.
- Diez pruebas nuevas; 60 específicas y 312 unitarias completas correctas.
  Sin nueva suite API ni repetición del script sandbox de 23 comprobaciones.
- CLI real en /tmp/ti-ricoh-strategies-step5: 228 registros (213 selecciones
  native_text/ruled_tables y 15 exclusiones), todos con motivo; checksum comprobado.
  JSON extraído idéntico a referencia, hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44;
  sin secciones ni nueve referencias modificadas. Línea base congelada intacta.
- Guía backend/docs/EXTRACTION_STRATEGIES.md. Informe técnico LOCAL IGNORADO:
  backend/docs/rag_runs/extraction_strategies/check_20261024.json. Comparación
  previa backend/docs/rag_runs/extraction_baseline/20261025T033208168385Z.json.
- Sin nuevos métodos especializados validados para escaneados, tablas sin bordes
  o diagramas. Sin proveedores, modelos, Supabase, cambios de fuente/perfil/
  datos/índices, despliegue, commit o push. Próximo paso solicitado: 6,
  formalizar reglas e informes de aceptado/revisión/error. Clase09 pendiente intacta.

### Actualización 24-10-2026: paso 4 del extractor completado

Prevalece sobre los pendientes de adaptadores descritos más abajo. Solo se
encapsularon bibliotecas; estrategias y siguientes pasos pendientes.

- Nuevo módulo backend/src/rag/pdf_adapters.py con interfaces de estructura,
  documento/página de layout, OutlineEntry y TableSnapshot. pypdf/pdfplumber
  se importan al abrir sus contextos, exclusivamente dentro de ese módulo.
- external_ingestion no importa bibliotecas ni accede a sus objetos internos.
  Recibe datos comunes y conserva reglas de perfil, IDs, bloques y contratos.
  extract_real_document/analyze_document/extract_pages admiten backends= con
  factories de contexto PDFBackends. Defaults conservan el uso previo.
- Helpers públicos conservan entrada nativa vía compatibilidad. page_tables
  entrega TableSnapshot consumible por table_block; no prometer API privada nativa.
  Vistas de caracteres conservan identidad para exclusiones exactas.
- Ocho pruebas nuevas, 50 específicas correctas y 302 unitarias completas
  correctas. Una prueba ejecuta todo el pipeline con backend en memoria y
  imports de ambas bibliotecas bloqueados; no presentar su fuente sintética
  como PDF real. También se probaron cierres/fallos, marcadores, tablas y página185 real.
- Extracción real completa idéntica (hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44),
  sin secciones ni nueve referencias cambiadas; línea base congelada intacta.
- Guía backend/docs/PDF_ADAPTERS.md. Informe técnico LOCAL IGNORADO:
  backend/docs/rag_runs/extraction_baseline/20261025T032202977078Z.json.
- Sin nueva suite API ni sandbox de 23 comprobaciones repetido. Sin OCR,
  proveedores, Supabase, cambios de fuente/perfil/datos/índices, despliegue,
  commit o push. Próximo paso solicitado: 5, estrategias por página/región.

### Actualización 24-10-2026: paso 3 del extractor completado

Esta sección prevalece sobre los pendientes del paso 3 descritos más abajo.
Solo se separaron etapas; adaptadores y estrategias siguen pendientes.

- external_ingestion.extract_real_document coordina cinco etapas: fuente,
  análisis, extracción de páginas, reconstrucción documental y validación final.
  Subetapas por página: auditoría, layout y reconstrucción de bloques.
- Estado explícito por documento (IDs/continuaciones/auditoría), sin acumular
  resultados al reutilizar un análisis. Páginas/documento/stream de análisis
  se cierran también ante errores. Se conservan excepciones originales con
  notas de etapa/página y se interrumpe el flujo ante fallo.
- Interfaz pública, helpers existentes, serialización v1 y consumidores
  conservados. No OCR, adaptadores, estrategias nuevas ni interpretación gráfica.
- Siete pruebas nuevas; 42 específicas correctas y 294 unitarias completas
  correctas. Sin nueva ejecución de suite API ni proveedores.
- Extracción completa idéntica a línea base (hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44),
  sin secciones ni nueve referencias locales cambiadas. Línea base congelada intacta.
- Guía backend/docs/EXTRACTION_PIPELINE.md. Informe técnico LOCAL IGNORADO:
  backend/docs/rag_runs/extraction_baseline/20261025T030355523352Z.json.
- Sin cambios al PDF/perfil/datos/índices, Supabase, despliegue, commit ni push.
  Pendientes de clase 09 y fallo histórico RIC-06 intactos. Siguiente paso
  cuando se solicite: 4, encapsular bibliotecas mediante adaptadores.

### Actualización 24-10-2026: paso 2 del extractor completado

Esta sección prevalece sobre los pendientes de pasos 1/2 descritos más abajo.
El usuario autorizó definir contratos; no se avanzó a separar etapas (paso 3).

- `backend/src/rag/extraction_contracts.py`: modelos Pydantic estrictos para
  fuente/perfil, auditoría de páginas, jerarquía de secciones, párrafos,
  tablas y filas. Extensiones de metadatos documentales se conservan.
- Validación estructural de versión, geometría finita/ordenada, referencias,
  páginas completas, IDs únicos, antecesores, columnas, filas y continuaciones.
  No acredita respaldo semántico, exhaustividad ni revisión humana.
- FigureReference y ExtractionDiagnostic son contratos separados; el resultado
  v1 sigue admitiendo solo párrafos/tablas. No se inventa extracción de figuras
  ni se añaden campos que rompan los consumidores actuales.
- external_ingestion.extract_real_document valida el resultado y devuelve el
  diccionario original; no model_dump ni cambio de serialización/schema_version.
- 11 pruebas nuevas, 35 específicas correctas y suite unitaria completa de
  287 pruebas correctas. Sin nueva ejecución de la suite API.
- Extracción completa idéntica a línea base, hash
  ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44;
  sin secciones ni nueve referencias locales cambiadas. Código del extractor
  cambia por la nueva validación; el comprobador lo informa por separado y
  la línea base congelada no se modifica.
- Guía `backend/docs/EXTRACTION_CONTRACTS.md`; informe técnico LOCAL IGNORADO
  `backend/docs/rag_runs/extraction_baseline/20261025T023955782724Z.json`.
- Sin cambios de fuente, perfil, extracción guardada, índices, proveedores,
  Supabase, despliegue, commit o push. Pasos 3–9 y pendientes de clase 09 siguen
  abiertos. Siguiente paso cuando se solicite: separar las etapas/pipeline.

### Actualización 24-10-2026: paso 1 del extractor completado

Esta actualización prevalece sobre las afirmaciones inferiores de implementación
no iniciada. Solo se implementó la línea base; pasos 2–9 pendientes.

- Referencia versionable: `backend/docs/baselines/ricoh_extraction_v1.json`.
  Conserva fuente/perfil, huellas de extracción completa y por sección, páginas,
  exclusiones, nueve archivos locales, código y versiones de bibliotecas.
- Nuevo comprobador: desde backend,
  `../.venv/bin/python -m scripts.check_extraction_baseline`.
  Reextrae en memoria, compara y crea un informe técnico JSON local nuevo;
  termina con error ante diferencias. La creación --create exige referencia
  histórica idéntica; ni referencia ni informes existentes se sobrescriben.
- Dos extracciones completas (creación y comprobación) idénticas a la guardada,
  hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44;
  sin secciones ni archivos de referencia cambiados. Código/entorno registrados
  por separado, para permitir refactorizaciones que conserven la extracción.
- 24 pruebas específicas correctas: 18 existentes + seis nuevas. Dos controles
  CLI de sobrescritura también rechazados con código 2 y referencia intacta.
  No presentar como nueva ejecución de 270 unitarias o 26 API.
- Guía: `backend/docs/EXTRACTION_BASELINE.md`. Informe local ignorado:
  `backend/docs/rag_runs/extraction_baseline/20261025T023423132332Z.json`.
  Los datos locales se requieren para comprobar; las huellas no son un respaldo.
- Sin modificar PDF, perfil, extractor existente, extracción guardada o índices;
  sin modelos, proveedores, Supabase, despliegue, commit ni push. Pendientes
  métricas/revisión humana/reserva sin cambios. Siguiente paso: contratos,
  únicamente cuando se solicite. Plan actualizado en EXTRACTOR_IMPLEMENTATION_PLAN.md.

### Continuidad vigente 24-10-2026 — publicación y verificaciones

Esta sección prevalece sobre la continuidad del 21-10-2026 y el historial posterior.
El usuario solicitó actualizar .agents tras crear y publicar el commit; esta tarea
solo documenta, sin iniciar implementación, reserva ni nuevas integraciones.

#### Git y pruebas

- Rama `codex/backend-infra-ricoh-local`, HEAD y remoto comprobados iguales en
  `c5826c070079d0460c16bc915e9bfd12ecd2b259`:
  `feat: improve hybrid retrieval and add coverage and token reports`.
- Publicados los 34 archivos pendientes: recuperación híbrida v2, rag_v6,
  completitud de evidencia, comparación real de tokens, JSON/CSV/PDF, pruebas
  y continuidad. Las frases antiguas «pendientes de commit/push sobre aea3002»
  quedan superadas para esos cambios.
- Repetidas antes de publicar: 270 pruebas unitarias y 26 API correctas;
  git diff --check sin errores. Los 34 archivos, incluidos JSON y texto de PDF,
  se revisaron sin coincidencias con secretos locales ni patrones de credenciales.
- Árbol limpio después del push. Esta actualización de .agents queda local;
  no implica otro commit/push. No se ha implementado la refactorización del extractor.

#### Endpoints y Supabase — verificación realizada en esta sesión

- Backend `infra-backend-1` saludable, imagen
  `sha256:a414431ee034403f145f1ca2576223bdff9a71febb4b242f98830954343a5d4b`.
- 19/19 controles HTTP correctos: health, Swagger, OpenAPI, JS/CSS y siete
  categorías; controles de autenticación, método, JSON, campos, categoría,
  Content-Type y tamaño; búsquedas y query reales HTTP 200.
- Supabase Auth, inventario y RPC verificados desde dos clientes nuevos del
  mismo usuario. 70 fragmentos coinciden con el índice local; ranking, texto
  y similitud consistentes. Sin upsert, cambios de corpus ni prueba entre usuarios.
- Una solicitud a rag/query sobre error 403 consumió Groq mediante clasificación,
  generación y revisión documental. No confundir una solicitud HTTP con una sola
  llamada al proveedor. Citas F1/F2/F3 estructuralmente coherentes.
- Observación de calidad: estado OK_PIDE_ACLARACION y datos_faltantes vacío;
  hay respuesta documental y limitación que solicita más información. Pendiente
  revisar coherencia, sin atribuir validación semántica ni revisión humana.
- Search HTTP 26,3582 s en la primera búsqueda observada; query HTTP 4,0937 s
  y pipeline 3,0447 s. Observaciones individuales, no benchmark ni diagnóstico
  probado de la demora inicial.
- Evidencia LOCAL IGNORADA: `backend/docs/rag_runs/endpoint_check_20261024/`
  contiene endpoints.json, supabase.json y RESULTADOS.md. No repetir llamadas
  para leerla. No está en el commit ni disponible automáticamente en otro clon.

#### Copia local de Supabase

Existen `backend/data/indexes/sections/{records.json,vectors.npy,config.json}`
y `infra/supabase/migrations/20261014_documentary_rag.sql`. Permiten reconstruir
el corpus y su estructura con configuración y autenticación adecuadas, pero no
son un respaldo completo. No se encontró dump de base ni respaldo de usuarios
Auth. El upsert no elimina filas adicionales: no garantiza volver exactamente
al estado completo del proyecto. No se creó respaldo ni se restauró nada.

#### Extracción Ricoh verificada

- 18/18 pruebas de extracción/fragmentación correctas (11 + 7); estas pruebas
  forman parte de la suite de 270, no sumar sus recuentos como cobertura nueva.
- Extracción completa en `/tmp/ti-ricoh-extraction-verification-20261024`,
  idéntica byte a byte a la guardada: SHA-256
  `ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44`.
- 228 páginas contabilizadas; 213 de contenido y 15 excluidas; 146 secciones,
  1.647 párrafos, 92 tablas, 383 filas y 62 candidatas a continuación sin fusionar.
- Numeración PDF/impresa comprobada en todas las páginas de contenido.
  Quick Install conserva once pasos y condición de privilegios.
- Las unidades regeneradas coinciden con las 498 del índice local; hashes y
  cobertura de las 779 vistas, vectores de 384 dimensiones, comprobados.
- Revisión visual DEL AGENTE, no humana: PDF 75 (tabla con diagramas) y 185
  (fax e impresión separados). Seis tablas gráficas de PDF 65/66/75/76/78/146
  excluidas de indexación textual. No interpreta diagramas ni activa OCR solo.
- Perfil específico para los bytes Ricoh registrados; no es extractor universal.
  RIC-06 (Hold Print/Stored Print) sigue siendo un fallo histórico de recuperación,
  no reevaluado en esta verificación. No se ejecutó generación ni Supabase.
- Evidencia LOCAL IGNORADA: `backend/docs/rag_runs/ricoh_extraction_check_20261024/`
  con verification.json y RESULTADOS.md. No sobrescribir la extracción guardada.
- RICOH_EXTRACTION.md conserva un siguiente paso histórico de fragmentación ya
  realizado; prevalecen el manifiesto actual y RICOH_LOCAL_RETRIEVAL.md.

#### Procedimiento acordado y clase 09

Plan en `.agents/EXTRACTOR_IMPLEMENTATION_PLAN.md`: línea base → contratos →
pipeline → adaptadores → estrategias → validaciones → casos complejos →
fragmentación/recuperación → integración y evaluación RAG. Es planificación;
el usuario pidió publicar primero y luego actualizar continuidad, no ejecutar
la refactorización como parte de esta tarea.

Clase-09 del directorio padre fue leída (17 diapositivas y notebook; ZIP y
extraídos coinciden). La entrega pide línea base y al menos una mejora; el demo
propone A/B/C con reranking. No asumir que todas las técnicas son obligatorias.
Sin umbral numérico de aprobación; 12–20 casos es escala didáctica, no garantía.
Pendientes revisión humana de 14 respuestas, respaldo/citas por afirmación,
abstenciones, reserva, decisión, notebook Colab consolidado y presentación PDF.
No confundir PDF de métricas con presentación. Ricoh permanece fuera de la API.

### Historial de continuidad — 21-10-2026 y anteriores

### Continuidad consolidada 21-10-2026 — actualización solicitada

El usuario pidió actualizar .agents después de completar los tokens reales.
Esta actualización solo documenta el estado; no ejecuta los pendientes.

| Área | Estado vigente | Próximo paso |
|---|---|---|
| Recuperación y contexto | Híbrida v2/rag_v6 desplegados; 7/7 documentales completos y 35/35 unidades en desarrollo conocido | Revisión humana y validación independiente, sin afirmar generalización. |
| Tokens comparables | 14 generaciones Groq reales, siete pares; A 6.592 / B 6.523 | Usar respuestas guardadas para revisión; no repetir medición por defecto. |
| Fidelidad/corrección/utilidad/respaldo | Pendiente de revisión humana | Revisar las 14 respuestas frente a sus contextos y justificar cada criterio; muestra por dos integrantes. |
| Cobertura de citas | Pendiente | Identificar afirmaciones y medir cuáles tienen referencia; adecuación semántica por separado. |
| Abstención correcta/innecesaria | Pendiente | Revisar poblaciones sin cobertura y respondibles; errores técnicos aparte. |
| Reserva | 12 candidatos, sin revisión final/congelación/ejecución | Aprobar anotaciones y novedad, fijar decisión/configuración y después abrirla de forma registrada. |
| Entrega clase 09 | Parcial | Consolidar notebook Colab, README/bitácora, presentación, decisión y acceso del profesor. |
| Git | Base publicada aea3002; cambios posteriores locales | Commit/push cuando se soliciten, revisando código y archivos nuevos. |

Fuentes para retomar: `.agents/CLASS09_METRICS_STATUS.md`,
`backend/docs/GENERATION_TOKENS.md` y
`backend/docs/generation_tokens_20261021.json`. Este último conserva contexto,
catálogo, salida cruda/validada y revisión humana pendiente por pregunta.
No confundir contrato/citas estructuralmente válidos con fidelidad o revisión
humana. El experimento de tokens solo mide generación directa y no el costo
completo de query; diferencia de −69 tokens no acredita ahorro estable.

Últimas verificaciones ya realizadas: 270 unitarias; 26 API en el despliegue
anterior; 14 HTTP 200 de Groq, usage sin faltantes y PDF de tres páginas revisado.
No se repitieron pruebas o llamadas para esta actualización. Imagen API vigente
`a414431ee034`; corpus/anotaciones/reserva intactos. Sin nuevo despliegue,
commit ni push. El detalle histórico empieza a continuación.

### Actualización 21-10-2026: siguiente paso de tabla, tokens reales, completado

El usuario autorizó «procede con el siguiente paso, según la tabla»: comparación
de consumo de tokens, primer parcial restante. **Ejecutada con Groq real**, no
solo estimaciones. No avanzar automáticamente a revisión humana ni reserva.

- `backend/src/rag/token_comparison.py` y
  `backend/scripts/compare_generation_tokens.py`. Generación directa A semántica
  frente a B híbrida v2, mismo rag_v6/modelo/esquema/temperatura/límites. Ambas
  aplican pertinencia antes de Top-3; usan lecturas semánticas/selecciones guardadas.
  Sin consulta Supabase, embeddings nuevos ni clasificación. A no debe confundirse
  con la A histórica de recuperación sin esta política/prompt.
- **14 llamadas Groq reales**, siete preguntas documentales E01/E02/E03/E04/E05/E06/E12;
  HTTP 200, usage válido y contrato/citas estructuralmente válidos en las 14.
  Cero errores, reintentos o usage desconocido. Orden A/B y B/A alternado.
  Solo generación; excluye clasificación, revisor y corrección. No es costo de query.
- Uso informado A: entrada 5.354, salida 1.238, total **6.592**; medias
  764,86/176,86/**941,71**. B: entrada 5.388, salida 1.135, total **6.523**;
  medias 769,71/162,14/**931,86**. Total ejecución **13.115 tokens**.
  B−A = −69 (−1,05%) en esta ejecución; medianas totales A/B 947/950. No afirmar
  ahorro estable, mejor calidad, consumo total del pipeline ni precio monetario.
- Máxima entrada real 785, dentro de 1000. Presupuesto local separado de usage;
  salida puede incluir razonamiento. Uso de salidas inválidas también se conserva
  en contabilidad; pares sin usage válido se excluyen y cuentan, nunca son cero.
- Archivos `backend/docs/generation_tokens_20261021.json`, `.csv`, `.pdf`.
  PDF tres páginas renderizadas/revisadas, 14 filas CSV, sumas/medias/hashes
  comprobados independientemente. Guía `backend/docs/GENERATION_TOKENS.md`.
- JSON guarda respuestas, contextos, catálogos y human_review pending por caso.
  **contract_valid no acredita respaldo semántico ni revisión humana**. El siguiente
  pendiente de la tabla es fidelidad/corrección/utilidad/citas por personas; usar
  estas respuestas guardadas sin repetir las 14 llamadas por defecto.
- Siempre JSON/CSV/PDF, incluso checkpoint inicial y tras cada llamada. Para
  reexportar sin proveedores, desde backend:
  `../.venv/bin/python -m scripts.compare_generation_tokens --from-json
  docs/generation_tokens_20261021.json --output docs/tokens_reexportados.json`.
  `--resume` solo peticiones no realizadas/HTTP 429 y protocolo/código idénticos;
  no sobrescribir una medición previa ni regenerar porque falte revisarla.
- **270 unitarias locales correctas**, siete nuevas. Tests sin proveedores;
  las únicas llamadas reales de esta tarea fueron las 14 documentadas a Groq.
- Tabla `.agents/CLASS09_METRICS_STATUS.md` y auditoría actualizadas. Reserva
  sigue sin ejecutar; seis casos de comportamiento excluidos de este experimento.
  Pendientes anotación/revisión humana, reserva congelada, métricas de citas y
  abstención, consumo total si se quiere reportar, decisión y entregables.
- Sin cambios al corpus/anotaciones, despliegue, commit o push nuevos.
  Imagen API vigente sigue a414431ee034; base Git publicada aea3002.
  Mejoras de cobertura, completitud y esta medición permanecen locales.

### Actualización 21-10-2026: mejoras de cobertura aplicadas y desplegadas

El usuario autorizó aplicar las mejoras. **Trabajo terminado**: tokenizador de
Wi-Fi/códigos, aplicabilidad antes de Top-3, pesos RRF y prompt compacto. No
avanzar automáticamente a generación o reserva como consecuencia de esta tarea.

- `src/rag/lexical.py`: Wi-Fi/WIFI/wi fi → wifi y códigos con guiones completos.
  Se evita descartar wi/fi por longitud. Sin IDs de casos en las reglas.
- `src/rag/retrieval.py`: RRF constante 60, semántica=1/léxico=2, filtro existente
  de enlace no abierto sobre unión antes de seleccionar tres. Permite reemplazos
  aplicables en vez de filtrar solamente después del corte. Sigue el ajuste
  opcional de categoría y la defensa adicional del pipeline.
- Prompt activo **rag_v6** (config/pipeline); rag_v5 conservado. Instrucciones
  compactadas, sin recorte de pasajes, cambios de contrato ni mayor presupuesto.
  Base local estimada 631 → 551 tokens, no consumo informado por Groq.
- `backend/scripts/evaluate_coverage_improvements.py`: reproducción offline de
  13 casos de desarrollo con Top-10 semánticos reales guardados y corpus de 70;
  léxico, selección y contexto recalculados, embeddings reales/revisión fijada.
  No simula rankings ni consulta Supabase para la comparación. La caché existente
  del contenedor se copió a /tmp/ti-rag-hf; temporal, puede desaparecer.
- Informes `backend/docs/coverage_improvements_20261021.json`, `.csv`, `.pdf`;
  cuatro páginas renderizadas/revisadas. Guía `COVERAGE_IMPROVEMENTS.md`.
  Comando desde backend con caché: `HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1
  OMP_NUM_THREADS=2 ../.venv/bin/python -m scripts.evaluate_coverage_improvements`.
- Comparación híbrida anterior → mejorada: Precision 52,38 → 66,67%; Recall
  80,95 → 100%; Hit 85,71 → 100%; MRR 0,8571 → 1; cobertura Top-3 80,36 → 100%;
  contexto 76,79 → 100%; completas Top-3 5/7 → 7/7 y contexto 4/7 → 7/7.
  Unidades 26/35 → 35/35. Ninguna pérdida de cobertura en los siete documentales.
- Ablaciones: solo prompt deja contexto 80,36% y 5/7 completos; solo ranking
  deja contexto 91,07% y 5/7; combinados 100% y 7/7. Peso léxico elegido con
  desarrollo: **no es validación ciega ni generalización acreditada**. No se usó
  categoría esperada/clasificador en esta comparación; seis casos de comportamiento
  no reciben métricas documentales ni evaluación de sus respuestas.
- Evaluador principal adaptado a aportes ponderados/exclusiones antes de Top-3.
  `coverage_improvements_trace_validation.json`: 13/13 selecciones/contextos
  actuales coinciden con el informe. Campo tiempos sin medir es null/N/E;
  no comparar tiempos históricos remotos con nuevas operaciones locales.
- **263 unitarias y 26 API locales correctas**, cuatro pruebas nuevas sobre las
  259 previas. Recalculo independiente, hashes y 26 filas CSV comprobados.
- Nueva imagen desplegada y contenedor saludable:
  `sha256:a414431ee034403f145f1ca2576223bdff9a71febb4b242f98830954343a5d4b`.
  `coverage_improvements_http_validation.json`: búsquedas reales Supabase vía
  search E03/E04/E05 devuelven 200 y cobertura completa, sin categoría esperada.
  No equivalen a generación/query ni revisión de fidelidad del prompt nuevo.
- Tabla de clase 09 actualizada en `.agents/CLASS09_METRICS_STATUS.md`. Corpus,
  anotaciones, reserva y reportes históricos intactos. No se abrió reserva ni se
  llamó a Groq. Sigue pendiente revisar anotaciones, congelar y ejecutar reserva,
  evaluar respuestas con rag_v6, comparar tokens reales/latencias y entregables.
- Cambios locales sobre **aea3002**, incluyendo la tarea anterior de cobertura
  completa aún sin publicar. No se realizó commit/push en esta tarea.

### Actualización 21-10-2026: primera tarea parcial de métricas terminada

El usuario pidió guardar la tabla en .agents e iniciar la primera tarea parcial.
Tabla vigente: `.agents/CLASS09_METRICS_STATUS.md`. Se interpretó como cobertura
completa por pregunta, primer parcial de la tabla inmediatamente anterior.
**Completado; no avanzar automáticamente al siguiente parcial (tokens).**

- Nuevo `backend/src/rag/complete_coverage.py`: todas las unidades necesarias,
  cualquier evidencia alternativa por unidad, detalle completo/incompleto,
  unidades presentes y faltantes; errores excluidos y comportamiento N/E.
- Derivador offline `backend/scripts/summarize_complete_coverage.py`. Desde backend:
  `../.venv/bin/python -m scripts.summarize_complete_coverage`. Verifica hash de las
  anotaciones originales y coherencia de IDs/preguntas/fracciones. Rechaza reserva.
- Informes nuevos `backend/docs/retrieval_metrics_20261021_coverage.json`, `.csv`,
  `.pdf` (cuatro páginas revisadas). No se alteran matrices originales ni informe
  de tiempos; conservar el hash de origen del bloque complete_coverage_derivation.
- Top-3 A/B: **4/7 (57,14%) / 5/7 (71,43%)** completos; 3/2 incompletos.
  Contexto final A/B: **3/7 (42,86%) / 4/7 (57,14%)**; 4/3 incompletos.
  E03/E05 incompletos en Top-3 en ambas, B completa E06; E04 pierde una unidad
  en contexto en ambas. Revisión humana de las anotaciones todavía pendiente.
- Evaluador de nuevas ejecuciones y exportador PDF existentes adaptados para
  incluir completitud. CSV conserva N/E vacío, booleanos y IDs de unidades
  faltantes; JSON mantiene denominadores e IDs completos/incompletos/excluidos.
- **259 pruebas unitarias locales correctas**, siete nuevas. Recalculo independiente,
  hash original y 26 filas CSV comprobados. PDF renderizado y cuatro páginas
  inspeccionadas sin defectos. No repetir búsquedas para generar este informe.
- Guía y auditoría actualizadas. Pendientes explícitos adicionales de clase 09:
  cobertura de citas por afirmación, tasas de abstención correcta e innecesaria,
  revisión de respuestas y tokens A/B equivalentes, reserva y entregables.
- Cero llamadas a proveedores, sin modelos inicializados, generación ni reserva.
  Sin cambios de API/corpus/configuración desplegada; sin despliegue, commit o push.
  Base publicada **aea3002** en codex/backend-infra-ricoh-local; cambios de esta
  tarea aún locales. La autorización Git anterior no publica esta tarea nueva.

### Entrega Git solicitada el 21-10-2026

El usuario autorizó crear un commit y actualizar el remoto después del cierre.
Esta autorización corresponde a publicar el trabajo existente, sin avanzar en
revisión humana, congelación o evaluación de la reserva.

Esta sección forma parte del commit de entrega de tiempos por etapa, métricas
A/B con PDF automático, comparación de tiempos, estructura de reserva y Swagger
descriptivo. Rama destino: `codex/backend-infra-ricoh-local`, remoto `origin`.
Consultar `git log -1` y `git status -sb` para obtener el identificador de esta
entrega y confirmar sincronización, en lugar de usar e5be392 como último estado.
Las referencias siguientes a «sin commit/push» describen los momentos históricos
anteriores a esta publicación. Antes de publicarla se revisaron los 42 archivos
pendientes, sin coincidencias con secretos locales ni patrones de credenciales;
se conservan ignorados .env y sus variantes privadas, índices y datos personales.
No se ejecutó la reserva ni se repitieron llamadas a proveedores para esta entrega.

### Cierre de sesión 21-10-2026 — dejar el trabajo en este punto

El usuario indicó «vamos a dejar así, actualiza .agents». Esta sesión termina
con documentación de continuidad: no avanzar en los pendientes ni ejecutar la
reserva como consecuencia de este cierre. Retomar según la siguiente solicitud.

**Completado:** instrumentación de tiempos desplegada; evidencias de desarrollo
anotadas por el agente; comparación A/B de recuperación y comparación descriptiva
de tiempos, con JSON/CSV/PDF; estructura de reserva sin ejecución; Swagger más
descriptivo actualizado en el contenedor local. Se mantiene la preferencia de
PDF automático para cada exportación de métricas. Corpus académico activo de
70 fragmentos; Ricoh continúa separado, sin integración en la API.

| Pendiente | Estado al cerrar | Siguiente acción cuando se retome |
|---|---|---|
| Evidencias de desarrollo | 35 unidades anotadas por el agente | Revisión humana de fuentes, relevancia y completitud. |
| Reserva | 12 candidatos, nueve documentales con 25 unidades y tres límites | Revisión humana de expectativas y novedad semántica; sin ejecutar. |
| Congelación | Protocolo definido, sin aprobar | Registrar decisión con desarrollo, snapshot de configuración y reserva aprobada. |
| Respuestas | Comparación y revisión humana pendientes | Mismo generador/prompt; evaluar exactitud, respaldo y citas, con muestra revisada por dos integrantes. |
| Evaluación de reserva | No conectada al evaluador | Adaptar lectura tras congelar y registrar primera apertura; exportar JSON/CSV/PDF. |
| Decisión final | Resultados preliminares de desarrollo | Justificar semántica o híbrida y contrastar con reserva sin reajustar sobre ella. |
| Entregables de clase 09 | Evidencias parciales | Consolidar Colab, README/bitácora, presentación PDF y acceso del profesor. |
| Git remoto | Cambios locales posteriores a e5be392 | Commit y push cuando se soliciten; revisar el diff completo, incluidos archivos nuevos. |

Rama de trabajo: `codex/backend-infra-ricoh-local`. Último commit publicado
registrado: `e5be392`. No se realizó commit ni push en este cierre.
Última imagen desplegada y verificada: `9ee9f10dd1f4` (hash completo abajo).
Últimas verificaciones: 26 pruebas API y HTTP de Swagger/esquema/assets/auth;
252 pruebas unitarias del trabajo de métricas/tiempos en su ejecución anterior;
ocho controles negativos de la estructura de reserva. No sumar recuentos ni
presentarlos como una ejecución conjunta nueva. No se repitieron pruebas,
consultas a proveedores ni operaciones Docker para actualizar este cierre.

### Actualización 21-10-2026: Swagger descriptivo desplegado

- Usuario pidió ampliar Swagger tras un rechazo de token. Se comprobó que
  DJANGO_API_TOKEN de backend/.env coincidía con el entorno del contenedor y
  categories devolvía 200 con él, 401 sin él o con Bearer duplicado. No se pudo
  determinar el encabezado exacto enviado por el navegador del usuario.
- `backend/api/documentation.py`: recorrido recomendado, autenticación paso a
  paso, diferencias entre search/query, límites, campos, citas, tiempos opcionales,
  estados documentales HTTP 200 y errores con códigos/acciones y encabezados.
  Ejemplos ilustrativos de entrada, éxito/error y tres resultados de query.
- `backend/api/contracts.py`: descripciones de campos; mismas restricciones.
  `backend/api/templates/api/swagger.html`: filtro, enlaces a operaciones y
  duración HTTP; autorización sigue sin persistirse y assets/validador locales.
- Todos los ejemplos se validan contra Pydantic y etiquetas de citas: **26 pruebas
  API locales correctas**. Sin llamadas a proveedores, sin ejecutar reserva.
- Imagen reconstruida y contenedor recreado, saludable:
  `sha256:9ee9f10dd1f4c70e1cfbd670a65da8ed76d84ab38b58c3f00dfa375254510153`.
  HTTP docs/OpenAPI/assets 200; categories autenticado 200, sin token 401.
  No había navegador disponible para inspección visual; verificación HTTP y esquema.
- Swagger: http://127.0.0.1:8000/api/v1/docs/ . Recargar y volver a autorizar
  con solo el valor de DJANGO_API_TOKEN. No se imprimieron ni cambiaron secretos.
- Guía actualizada: `backend/docs/API.md`. Sin commit ni push nuevos. La reserva
  continúa como borrador sin ejecución; el despliegue no implica evaluarla.

### Actualización 21-10-2026: conjunto de reserva estructurado, sin ejecutar

- `backend/cases/rag_reserve.json`, esquema propio `rag-reserve-v1`: **12
  candidatos**, nueve documentales con 25 unidades, tres de límite documental;
  17 fragmentos en catálogo con citas/offsets. Mismo corpus académico de 70.
- Guía y preguntas: `backend/docs/RAG_RESERVE.md`. No son paráfrasis deliberadas
  de desarrollo: cubren intervención interna, archivo individual, cola compartida,
  Ethernet dañado, incidente compartido, alta, exposición ya ocurrida, bloqueo,
  cierre por recurso y límites de catálogo/DNS/inventario. Revisión semántica de
  novedad pendiente; comparten corpus/categorías. No afirmar ceguera ni reserva
  independiente por familias: el agente conocía desarrollo y resultados previos.
- Estado **draft_pending_human_review**, split `reserve_candidate`; revisión por
  caso pendiente y ejecución `not_run`. No hay resultados de reserva.
- Verificador offline: desde backend,
  `python3 -m scripts.validate_rag_reserve --output docs/rag_reserve_validation.json`.
  Comprueba hashes, citas contra índice, duplicados exactos y estructura. Ocho
  controles negativos correctos; no certificar revisión semántica ni ausencia de
  ejecuciones externas no registradas. Cero modelos/llamadas a proveedores.
- `--require-ready` termina 1 mientras faltan revisión humana, congelación,
  decisión con desarrollo y snapshot de configuración. Solo verifica preparación;
  nunca ejecuta preguntas. Guardar también commit/huella externa del JSON al congelar.
- No está conectada al evaluador actual, que sigue fijo a desarrollo. No reemplazar
  `rag_evidence.json` con estos candidatos. Adaptar lectura cuando corresponda,
  conservar preguntas aprobadas y PDF automático de las futuras métricas.
- Secuencia: revisión humana → decisión con desarrollo → congelar configuración
  y reserva → apertura registrada → interpretar sin tuning sobre estos resultados.
  Si se usan para ajustar, retirar a desarrollo y crear otra reserva nueva.
- Sin métricas nuevas, despliegue, commit ni push. No se modificó código RAG/API.
  Las 252 pruebas previas corresponden al trabajo anterior; este paso se verificó
  con validación offline y controles negativos, sin repetir la suite ni el benchmark.

### Actualización 21-10-2026: módulo de comparación de tiempos terminado

- Guía: `backend/docs/TIMING_COMPARISON.md`. Implementación en
  `backend/src/rag/timing_comparison.py` y CLI
  `backend/scripts/compare_retrieval_times.py`.
- Desde backend: `../.venv/bin/python -m scripts.compare_retrieval_times`.
  Lee la matriz guardada y exporta **siempre JSON, CSV y PDF**, sin cargar modelos
  ni llamar a Supabase/Groq. Conserva la entrada y sus hashes; no repetir consultas
  para reconstruir informes. `--input` y `--output` permiten otros archivos.
- Archivos: `backend/docs/retrieval_metrics_20261021_times.json`, `.csv`, `.pdf`.
  PDF de tres páginas renderizadas e inspeccionadas, sin defectos observados.
- Trece pares válidos: media/mediana/P95 A = 200,90/188,37/291,13 ms;
  B = 409,30/398,69/555,66 ms. Mediana de diferencias emparejadas 208,77 ms;
  mediana de incrementos relativos 112,35%. Lectura léxica mediana 203,68 ms.
- Grupos separados: todos (13), documentales (7), comportamiento (6). Las
  medianas documentales son 188,38/401,05 ms; no confundirlas con todos los casos.
- A=embedding+semántica; B=embedding+subtotal híbrido. No sumar subtotal y sus
  hojas. Las variantes comparten componentes del experimento original: comparación
  descriptiva de desarrollo, una observación por pregunta, sin latencia HTTP,
  inicialización/Auth ni generación. No es un ensayo independiente de latencia.
- Datos inválidos excluyen el par completo con diagnóstico; etapas no aplicables
  N/E, sin ceros inventados. Exportación incompleta termina con error tras crear
  los tres archivos. P95 interpolado lineal; muestra pequeña.
- Seis pruebas nuevas, suite local completa **252 correctas**, recalculo
  independiente de estadísticas y comprobación de hash/26 filas CSV. Los recuentos
  inferiores en secciones siguientes son evidencias históricas.
- Sin despliegue, commit ni push nuevos. Cambios posteriores a e5be392 locales.
  Persisten revisión humana, reserva nueva, decisión y entregables consolidados.

### Preferencia vigente: PDF automático de la matriz de métricas

El usuario pidió que **siempre se cree un PDF de estas métricas**, adaptando el
módulo ya existente. Implementado:

- `PDFReport.generate_retrieval_metrics(report, source_json=...)` en
  `backend/src/pdf_report.py`, reutilizando estilos, tablas y NumberedCanvas.
  El método `generate()` de los reportes anteriores no cambia.
- `scripts.evaluate_retrieval_metrics.write_outputs` genera JSON, CSV y PDF de
  forma inseparable en el mismo directorio/nombre base. No agregar una opción
  que omita el PDF por defecto. Las matrices incompletas también generan PDF
  antes de terminar con error; un error de PDF se propaga y no se oculta.
- `--from-json <matriz.json>` regenera solamente PDF, sin validar el corpus,
  inicializar modelos ni llamar a Supabase/Groq. No repetir búsquedas para un PDF.
- Archivo actual: `backend/docs/retrieval_metrics_20261021.pdf`, tres páginas:
  agregados, matriz por caso y preguntas/trazabilidad. Mantiene N/E y ERROR,
  denominadores, revisión humana pendiente y SHA-256 del JSON fuente.
- PDF regenerado desde el JSON existente, sin alterar las métricas ni llamadas
  nuevas a proveedores. Tres pruebas nuevas; **246 unitarias correctas**.
  Se renderizaron e inspeccionaron las tres páginas con Poppler y se comprobó
  texto/paginación con pdfplumber, sin defectos visuales observados.
- Documentación en `backend/docs/RETRIEVAL_METRICS.md`. El PDF de métricas no
  acredita por sí solo la presentación final del proyecto del segundo corte.

Cambios aún locales sobre e5be392; sin commit/push ni reconstrucción del backend
por esta adaptación de informes. Conservar la preferencia en futuras ejecuciones.

### Actualización 21-10-2026: métricas de recuperación calculadas

El usuario pidió calcular las métricas. **Ejecutado en Supabase real**, sin Groq
ni escrituras; corpus académico activo de 70 fragmentos, índice intacto.

- Evaluador reproducible: `backend/scripts/evaluate_retrieval_metrics.py`;
  fórmulas: `backend/src/rag/retrieval_metrics.py`. Cuatro pruebas numéricas y
  suite local completa de **243 pruebas correctas**. Recalculo independiente de
  JSON/CSV correcto; no se repitió la regresión generativa de 13 consultas.
- Se ejecutaron 13 consultas; cero errores técnicos. Solo siete tienen unidades
  documentales. Los seis casos de comportamiento tienen métricas nulas y quedan
  fuera de los promedios. Todos siguen siendo desarrollo, sin reserva independiente
  ni revisión humana de las anotaciones.
- Comparación controlada: A semántica vs B BM25+semántica+RRF; mismo embedding y
  búsqueda semántica Top-10 por caso; Top-3 final. Ajuste por categoría desactivado,
  no se usa la categoría esperada ni se llama al clasificador. B conserva la unión
  completa hasta 20 candidatos del recuperador actual; no hay reranker.
- Promedios macro A/B: Precision@3 **47,62% / 52,38%**; Recall@3
  **73,81% / 80,95%**; Hit@3 **85,71% / 85,71%**; MRR@3
  **0,8571 / 0,8571**; cobertura Top-3 **78,21% / 80,36%**.
  Ambas cubren 26/35 unidades en total (micro 74,29%): el pequeño avance macro
  redistribuye aciertos entre preguntas de diferente número de unidades.
- Cobertura tras presupuesto **69,29% / 76,79%**. Contextos con prompt rag_v5,
  850 tokens, clasificación null en ambos y sin filtros de pertinencia; es una
  medición del recuperador aislado, no del pipeline completo de la API.
- Medianas observadas **0,1884 / 0,4011 s**: tiempos de componentes compartidos
  secuenciales, excluyen Auth/carga; no presentarlos como benchmark HTTP independiente.
- Casos: B mejora E06 (403), empeora cobertura E03 (Wi-Fi), y ambos fallan E05
  (mensaje sospechoso no abierto) en Top-3. SEG-02 está en candidatos profundos,
  se pierde en selección. No se cambió configuración ni anotación para ocultarlo.
- Informes versionables: `backend/docs/RETRIEVAL_METRICS.md`,
  `backend/docs/retrieval_metrics_20261021.json` y CSV con el mismo nombre.
  Incluyen preguntas, IDs, catálogo, rankings, aportes RRF, contexto/omisiones,
  tiempos, parámetros y hashes. El 13/13 previo de comportamiento es otra medida.

Pendientes: revisión humana de anotación/respuestas, reserva nueva, decisión
sobre configuración tras contrastar los intercambios y entregables consolidados.
No hay ganador definitivo. No hubo despliegue nuevo ni cambio de API; los cambios
posteriores a `e5be392` siguen locales y pendientes de commit/push.

### Actualización 21-10-2026: evidencias anotadas

El usuario pidió anotar evidencias para la evaluación de clase 09.
**Anotación del agente completada; revisión humana pendiente.**

- Datos: `backend/cases/rag_evidence.json`, esquema `rag-evidence-v1`.
- Lectura de los 70 fragmentos del corpus académico activo y contraste con los
  siete PDF originales/35 secciones. No se usó el índice Ricoh ni se ejecutó
  recuperación, embeddings o llamadas Groq/Supabase durante esta anotación.
- Se conservan preguntas y expectativas de `rag_regression.json`, con su hash.
  13 casos: siete documentales con 35 unidades requeridas y seis de comportamiento.
  Cada unidad tiene IDs, cita literal y offsets; catálogo con texto y procedencia.
  Se anotan condiciones, respuesta esperada, criterios de fallo y exclusiones.
- Conjunto relevante = unión de IDs de las unidades necesarias. Los seis casos
  de comportamiento tienen conjunto vacío; sus referencias a reglas de aclaración
  o rechazo no deben contarse como evidencia que resuelva la solicitud. Excluirlos
  de promedios de recuperación y cobertura, y evaluar comportamiento aparte.
- Los 13 casos ya se usaron para ajustar; todos se marcan desarrollo y ninguno
  reserva. No afirmar anotación ciega ni evaluación independiente. Preparar
  reserva nueva después, separando familias; no reciclar paráfrasis conocidas.
- Validador: desde backend `../.venv/bin/python -m scripts.validate_rag_evidence`.
  Verifica índice/configuración y sus hashes, PDF original, páginas, texto,
  preguntas originales, IDs, citas/offsets y unión de relevantes. No llama APIs.
  Inicialmente pasó y rechazó corpus distinto, cita alterada y unión incorrecta.
  Esto prueba integridad/fuente, no exhaustividad semántica ni revisión humana.
- Guía legible: `backend/docs/RAG_EVIDENCE.md`; informe:
  `backend/docs/rag_evidence_validation.json`. No se calcularon métricas ni se
  eligió estrategia. Pendiente revisión humana de unidades/relevancia/exclusiones.

Los cambios de anotación se suman a la auditoría y tiempos aún locales sobre
`e5be392`; sin nuevo commit/push ni reconstrucción del contenedor por esta tarea.

### Actualización 21-10-2026: tiempos por etapa implementados

El usuario pidió implementar el desglose de tiempos pendiente de clase 09.
**Implementado y desplegado**, sin cambiar prompts, corpus ni ranking:

- `src/rag/timing.py`: cronómetro monotónico acumulativo, incluso en excepciones.
- `Retriever` separa embedding, búsqueda semántica/RPC, lectura paginada del corpus
  léxico, BM25, RRF y puntuación extra de resultados exclusivamente léxicos.
  `retrieval_seconds` sigue siendo subtotal sin embedding; no sumarlo de nuevo.
- `repository.lexical_candidates` separa I/O de ranking; `lexical_search` conserva
  su interfaz previa y aplica los mismos filtros/ordenación.
- Pipeline conserva duraciones fallidas, acumula validación/revisión repetidas y
  mide generación correctiva aparte; agrega `total_seconds` y versión `stages-v1`.
- API search/query publica `tiempos_segundos`; Swagger y `docs/API.md` actualizados.
- La regresión escribe tiempos por caso en JSON y `timings.csv`, con estados de
  error explícitos y celdas vacías para etapas no ejecutadas. No se reescribieron
  tiempos históricos. No repetir la suite Groq solo para obtener esos archivos.
- 239 unitarias y 25 API locales correctas; 25 API también dentro de la imagen.
  Verificación con embeddings reales y el corpus local de 70 registros: mismos
  candidatos/puntajes que el recuperador previo para las 13 preguntas.
- HTTP real search/query 200; consulta 403 `OK_VALIDADO`, pipeline 7,5787 s y HTTP
  8,4919 s. Es una observación, no benchmark. Inicialización de recursos, Auth y
  carga anterior a `run_rag_case` quedan fuera de los tiempos del pipeline.
- Imagen activa: `sha256:efb734fd3c91d1ec6b4de90144f1fdb76b6417a794f2df6810a182e7e3e0c67b`.
  Docker resolvió una nueva base Python al reconstruir; no cambiaron los archivos
  de dependencias. `pip check`, API en contenedor y ambas consultas reales pasaron.
- Guía: `backend/docs/STAGE_TIMINGS.md`; evidencia:
  `backend/docs/stage_timing_validation.json`. Auditoría previa de clase 09:
  `backend/docs/CLASS09_AUDIT.md`, con actualización de instrumentación.

Base publicada `e5be392` en `codex/backend-infra-ricoh-local`. La auditoría y estos
cambios posteriores siguen locales, sin nuevo commit/push. El informe
`backend_validation.json` sigue describiendo la regresión anterior: no atribuir
su 13/13 a una nueva ejecución remota de esta instrumentación. Siguen pendientes
la comparación A/B, Precision/Recall/MRR/cobertura del corpus activo, reserva,
revisión humana y entregables consolidados. Ricoh sigue fuera de la API.

### Historial inmediato: aclaraciones y regresión


El usuario pidió resolver el tratamiento de preguntas ambiguas y completar la
regresión del backend. **Realizado y desplegado** el 20-10-2026:

- `system_v7` y `rag_v5`; contexto compacto conserva `datos_faltantes`.
- Política local pide comportamiento y mensaje ante incidentes vagos, incluso
  con marca/modelo. Conserva el texto original en el resumen y genera aclaraciones
  locales auditables (`LOCAL_CLARIFICATION`), sin diagnóstico documental.
- Instalación sin privilegios deriva a software/soporte independientemente de
  la categoría inicial. Riesgo físico excluye comprobaciones ordinarias de energía.
- 234 unitarias, 24 API y comprobación Django correctas.
- Regresión real Supabase/Groq: **13/13** según criterios de entrega. Ocho
  `MODEL_SUPPORTED`, tres `LOCAL_CLARIFICATION`, dos abstenciones seguras
  (`MODEL_REJECTED` reemplazado, E07/E09). No afirmar 13 respuestas aprobadas por
  el modelo: las salidas rechazadas siguen rechazadas. Los casos que exigen un
  procedimiento respaldado no aprueban por abstención.
- HTTP real del contenedor: consulta Ricoh ambigua 200/`OK_PIDE_ACLARACION`,
  datos faltantes explícitos y sin «no imprime»; consulta general de impresora
  200/`OK_VALIDADO`, con fuentes y sin preguntas innecesarias.
- Evidencia versionable: `backend/docs/backend_validation.json` y
  `backend/docs/BACKEND_VALIDATION.md`. Trazas en `backend/docs/rag_runs/`
  ignoradas. Comando desde backend: `../.venv/bin/python -m
  scripts.validate_rag_scenarios --output docs/rag_runs/validation` (cuota real).
- Imagen activa: `sha256:9130bb2b931300144628ac4e36b488bd7302e5db5f7f1e53b99eee80cf35cc8c`.

La rama `codex/backend-infra-ricoh-local` se publicó previamente en `057380f`.
El usuario autorizó actualizar `.agents`, crear el commit con estas correcciones
y publicar inmediatamente en esa misma rama. Esta actualización de continuidad
forma parte del commit de entrega `fix: clarify ambiguous requests and validate backend regression`.
Consultar `git log -1` y `git status -sb` para su identificador y sincronización.
No requiere repetir llamadas a Groq ni desplegar: la imagen corregida ya está activa.
Mantener simple el alcance: el manual Ricoh permanece fuera de la API, cuyo
índice académico conserva 70 fragmentos. No continuar la integración de Ricoh
ni la prueba de aislamiento entre usuarios. Sus limitaciones locales anteriores
(impresión Hold/Stored y presupuesto de contexto) siguen pendientes.

### Estructura y cambios locales

- `backend/`: Django/API, `src/`, `schemas/`, `scripts/`, `test/`, `prompts/`,
  `cases/`, notebooks, corpus, manuales, documentación y requirements.
- `frontend/`: solo README; framework y aplicación aún no elegidos.
- `infra/`: `compose.yaml`, README y `supabase/migrations/`.
- `.agents/`: continuidad y especificación histórica del diagrama del notebook.
- `.venv/` y `.venv-test/` siguen en la raíz para conservar sus rutas instaladas.
- Configuración privada en `backend/.env`; plantilla `backend/.env.example`.
  No imprimir credenciales ni incorporarlas a Git o a la imagen.

Rama de entrega: `codex/backend-infra-ricoh-local`, creada desde `83f2110`
(`codex/implement-embeddings`). El usuario autorizó incluir todos los cambios
versionables en un commit y subir esta rama a origin, sin integrar con la rama
base. La entrega incluye reorganización, Docker, extracción/evaluación local de
Ricoh y documentación. Los secretos, cachés, índices y extracciones generadas
siguen ignorados. Consultar `git log -1` y `git status` para el commit y estado
final de publicación. No ampliar la integración del manual complejo por ahora.

El commit 83f2110 dejó de seguir 47 `.pyc` sin borrarlos localmente. `.gitignore`
excluye `.env` y `.env.*` (excepto `.env.example`), `.aws/`, entornos, bytecode,
índices, cachés, trazas y artefactos personales de Drive. Las exclusiones con
rutas concretas se actualizaron al prefijo `backend/`. Conservarlas.

### Backend desplegado y autenticación

Contenedor **`infra-backend-1`**, saludable en la comprobación del 20-10-2026.
Imagen `ti-support-rag-backend:local`; imagen desplegada actual (21-10-2026)
`sha256:efb734fd3c91d1ec6b4de90144f1fdb76b6417a794f2df6810a182e7e3e0c67b`.
El ID del primer build que figura en el historial y `docker_validation.json`
corresponde a la validación anterior; Compose reconstruyó después con caché.
Imagen de unos 1,28 GB sin comprimir: PyTorch CPU es el mayor componente.

- API: `http://127.0.0.1:8000/api/v1/`.
- Swagger: `http://127.0.0.1:8000/api/v1/docs/`.
- Endpoints en `backend/api/urls.py` y `controllers.py`; prefijo en
  `backend/ti_api/urls.py`; recuperación/generación en `backend/api/services.py`.
- `categories`, `rag/search` y `rag/query` requieren `Authorization: Bearer`
  con **DJANGO_API_TOKEN**, no una clave o JWT de Supabase. En Swagger introducir
  solo el valor, sin `Bearer`; la autorización no persiste al recargar.
- El 401 de categories se reprodujo sin token, con clave Supabase y con Bearer
  duplicado. Con el token correcto devuelve 200 y las siete categorías.
  Token del contenedor y del `.env` local comprobados iguales, sin mostrarlos.
- Conexión Supabase desde el contenedor comprobada: autenticación y 70 fragmentos
  visibles; proyecto `fmsoacmvsmfrnbmnvizo`. Las sesiones se obtienen mediante
  usuario/contraseña Auth y clave publicable; no necesita Access Token personal
  para operar. No usar service_role ni desactivar RLS.
- El usuario **descartó** la prueba entre dos usuarios; no retomarla por iniciativa
  propia. Las verificaciones de dos clientes son del mismo usuario.

Compose inyecta el `.env`, publica solo en localhost y monta en lectura
`backend/data/indexes/sections/` en `/app/data/indexes/sections`.
Volúmenes: `ti-support-rag-model-cache` y `ti-support-rag-tokenizer-cache`.
El modelo real se descargó y se comprobó compatible con el índice desde la imagen.
Gunicorn usa un proceso, cuatro hilos y el semáforo RAG del backend.
Los cambios de código requieren reconstruir la imagen; los cambios del `.env`
requieren recrear el contenedor. La imagen no copia el PDF ni datos locales.

### Consultas HTTP reales ejecutadas

Ambas pasaron por Supabase/Groq y devolvieron HTTP 200, `OK_RESPUESTA_PARCIAL`:

1. «El portal de documentos devuelve error 403. ¿Eso demuestra que mi cuenta está
   suspendida?» → categoría `acceso`; cita ACS-03 y ACS-05; no confirma suspensión.
   Tiempo HTTP total 20,778 s; latencia del pipeline reportada 3,4762 s.
2. «Tengo problemas al enviar impresiones en la Ricoh MP 4002.» → `hardware`;
   cita HW-03 y HW-05 del manual académico general, **no el manual Ricoh**.
   Tiempo HTTP 8,862 s; pipeline 6,9628 s.

Trazas locales ignoradas por Git:
`backend/docs/rag_runs/http_query_check_20261020.json` y
`backend/docs/rag_runs/http_query_ricoh_mp4002_20261020.json`.
Observación de calidad pendiente: en la segunda, `datos_faltantes: []` pese a
reconocer que faltan síntomas/configuración/errores; también resume «problemas al
enviar impresiones» como «no imprime». Corregido posteriormente para incidentes vagos: ver la sección de continuidad
y `backend/docs/backend_validation.json`; esta traza antigua se conserva sin editar.
No volver a llamar Groq solo para leer esas respuestas guardadas.

### Manual Ricoh: identidad verificada y registro listo

Original intacto: `backend/manuals/hardware/RICOHMP4002_MANUAL.pdf`.
Registro separado: `backend/manuals/manifest.real.json`.
Evidencia: `backend/docs/ricoh_manual_verification.json`.
Guía/estado: `backend/manuals/README.md`.

- ID `RICOH-MP4002-USER-GUIDE-EN`, idioma `en`, 228 páginas, 5.520.145 bytes.
- SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`.
- **Idéntico byte por byte al PDF oficial de Ricoh**. No hace falta repetir la
  investigación ni volver a atribuir compatibilidad solo al nombre del archivo.
- Ricoh lo lista para Aficio MP 4002/4002SP/5002/5002SP:
  https://support.ricoh.com/bb_v1oi/html/oi/re/model/mp42/mp42en.htm
- Copia oficial comparada:
  https://support.ricoh.com/bb_v1oi/pub_e/oi/0001043/0001043003/VD1297802_01/D1297802_en.pdf
- `version: D129-7802` es el código editorial de la página PDF 228; no firmware.
  Copyright 2011 (página PDF 227). Actualización de la descarga: 2012-01-10;
  `document_date` queda null porque no se acreditó fecha exacta de publicación.
- `model_verified_from_official_source` y `official_source_verified`: true.
  `model_verified_from_document`: false porque el modelo no aparece explícito en
  el texto del PDF. No es una contradicción: la fuente oficial y los bytes
  idénticos establecen la asociación. Hay variaciones por región y opciones.
- Texto extraíble, página PDF 2 visualmente en blanco, tablas de mensajes/causas/
  soluciones; no requiere OCR general. Página PDF 185 = página impresa 183.
- `simulated: false`, estado **`locally_indexed_retrieval_partial`**.
- Extracción local en `backend/data/extracted/RICOH-MP4002-USER-GUIDE-EN/`: JSON,
  Markdown de revisión, resumen y muestras visuales. Directorio ignorado por Git.
  Guía: `backend/docs/RICOH_EXTRACTION.md`. Evidencia: `backend/docs/ricoh_extraction_validation.json`.

Se generaron fragmentos y embeddings locales en `backend/data/indexes/ricoh-local-v1/`,
con formato propio y sin subir este manual a Supabase. Ver
`backend/docs/RICOH_LOCAL_RETRIEVAL.md` y `backend/docs/ricoh_local_retrieval_validation.json`.
Los manifiestos académicos `backend/manuals/manifest.json` y
`backend/data/corpus/v2/manifest.json` conservan sus siete documentos simulados.
El RAG activo sigue con 70 fragmentos del corpus
`ti-manuals-v2-d479e96962b17496eaa3`.

### Aspectos técnicos para el próximo trabajo de ingestión

El extractor nuevo `backend/src/rag/external_ingestion.py` y el comando
`backend/scripts/extract_real_manual.py` procesan el registro real por separado.
`backend/src/rag/ingestion.py` (académico) solo admite `simulated: true`, rechaza páginas sin
texto y detecta únicamente encabezados del tipo `HW-02 | ...`. Por eso el importador académico no procesa
el PDF real; no se modificó su contrato. No marcarlo como simulado ni quitar validaciones sin separar el
formato real del académico. `manifest.real.json` ahora admite un perfil para el extractor local, todavía
no un contrato de indexación admitido por el importador académico. `load_corpus` solo lee archivos listados;
poner el PDF en `manuals/` no activa recuperación.

Conservar procedimientos, condiciones, advertencias y filas completas de tablas,
la procedencia, idioma, versión y páginas PDF/impresas. El modelo es multilingüe:
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revisión
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, 384 dimensiones normalizadas, máximo
128 tokens. El corte actual de 80 tokens y los encabezados consumen ese límite;
evaluarlo antes de aplicarlo a procedimientos largos. No cambiar de modelo sin
revisar/reconstruir la representación del índice.

La verificación `backend/scripts/verify_supabase.py` admite solo 1000 filas por
corpus; añadir paginación si se supera. La recuperación léxica ya pagina, pero
lee todas las filas compatibles: medir el impacto del corpus mayor. Top-3 y
presupuesto de 1000 tokens de entrada por llamada siguen activos. Validar primero
extracción y recuperación local en español; después planear la carga remota y el
cambio de índice/contenedor. No reindexar ni subir por cada consulta.

### Validaciones y comandos actuales

Tras la reorganización: 210 pruebas unittest y 24 pruebas Django/API aprobadas;
Django check correcto. Sintaxis de notebooks y primera celda de los tres probadas
desde la raíz, sin ejecutar todos los notebooks. En la imagen: 24 pruebas API,
imports y embeddings reales/compatibilidad del índice aprobados; HTTP health,
docs, OpenAPI y categories autenticado 200. No se repitieron esas suites al
editar metadatos o preparar este handoff. Suite remota completa de diez escenarios
con configuración final sigue sin aprobarse; no confundirla con dos consultas HTTP.

Desde la raíz del repositorio:

```bash
source .venv/bin/activate
cd backend
python manage.py check
python manage.py test api
python -m unittest discover -s test
```

Docker, desde la raíz:

```bash
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs --tail=30 backend
docker compose -f infra/compose.yaml build
docker compose -f infra/compose.yaml up -d --wait
```

El build puede requerir permiso del entorno para actualizar el caché Docker fuera
del workspace. No cambiar HOME ni eludir permisos. Mantener credenciales fuera
de salidas y argumentos de comandos. Las consultas Groq reales consumen cuota.
El usuario indicó que no necesita más trabajo en Drive: no ejecutar el script
personal de organización ni consultar Drive sin nueva solicitud.

## Historial anterior — referencia, no estado vigente

El informe original es del 14-10-2026. Se conserva abajo junto con sus
actualizaciones. Sus afirmaciones sobre ramas, rutas, tareas pendientes,
contenedores, identidad del manual o trabajo sin publicar pueden estar superadas
por el estado actual de arriba.

## Resumen para el siguiente agente

El proyecto implementa soporte TI con clasificación estructurada, recuperación documental mediante embeddings en Supabase, generación con Groq, citas y controles locales. Existe una API Django funcional y Swagger UI. La infraestructura y la recuperación real están comprobadas; la suite remota completa con la configuración final sigue pendiente por cuota de Groq. No afirmar que todas las respuestas futuras están garantizadas.

El usuario pidió documentar el estado y los cambios en el directorio existente `.agents/`. No pidió un nuevo commit ni push en esta última tarea. Conservar los cambios locales existentes.

## Git y trabajo sin publicar

- Repositorio remoto: `git@github.com:dvdm12/TI-support-RAG.git`.
- Rama activa: `codex/implement-embeddings`, seguimiento `origin/codex/implement-embeddings`.
- HEAD observado: `df58432` — `feat: implement documentary RAG with Supabase and embeddings`.
- En la vista local, HEAD coincide con la referencia de seguimiento; no se hizo fetch para verificar cambios remotos recientes.
- Las mejoras posteriores del RAG, límites de tokens, API Django y Swagger están sin commit. Hay archivos modificados y archivos nuevos sin seguimiento. Revisar `git status --short` y `git diff` antes de actuar; `git diff --stat` no incluye archivos nuevos sin seguimiento.
- Modificados: `.env.example`, `.gitignore`, `README.md`, `docs/RAG.md`, `docs/rag_validation.md`, `requirements.txt`, `src/groq_client.py`, `src/pdf_report.py`, `src/rag/config.py`, `src/rag/context.py`, `src/rag/pipeline.py`, `src/rag/repository.py`, `src/rag/retrieval.py`, `test/test_groq_client.py`, `test/test_rag.py`.
- Nuevos: `api/`, `ti_api/`, `manage.py`, `cases/rag_regression.json`, `docs/API.md`, `docs/api_validation.json`, `docs/rag_hardening_verification.json`, `scripts/validate_rag_scenarios.py`, `prompts/system_v5.md`, `prompts/system_v6.md`, `prompts/rag_v3.md`, `prompts/rag_v4.md`, `src/token_budget.py`, `src/rag/applicability.py`, `src/rag/lexical.py`, `src/rag/policy.py`, `src/rag/support.py`, `test/test_rag_hardening.py` y este informe. Lista ampliada en «Revisión local del estado».

## Arquitectura y archivos principales

Flujo: texto o imagen opcional → OCR → clasificación `SolicitudTI` → políticas locales → recuperación híbrida → contexto con fuentes → generación `RespuestaRAG` → validación de citas y respaldo → decisión final → traza/PDF.

| Componente | Ubicación |
|---|---|
| Configuración y selección de prompt | `src/config.py`, `src/rag/config.py` |
| Contratos de clasificación y respuesta | `schemas/request_v1.py`, `schemas/rag_response_v1.py` |
| Cliente Groq y presupuesto de entrada | `src/groq_client.py`, `src/token_budget.py` |
| Ingesta, fragmentación, embeddings, índice | `src/rag/ingestion.py`, `chunking.py`, `embeddings.py`, `index.py` |
| Supabase y recuperación | `src/rag/repository.py`, `retrieval.py`, `lexical.py` |
| Contexto, pipeline y citas | `src/rag/context.py`, `pipeline.py`, `citations.py` |
| Políticas, pertinencia y respaldo | `src/rag/policy.py`, `applicability.py`, `support.py` |
| Reportes PDF | `src/pdf_report.py` |
| API y contratos HTTP | `api/controllers.py`, `services.py`, `contracts.py`, `urls.py` |
| Proyecto Django | `ti_api/settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `manage.py` |
| Swagger y OpenAPI | `api/documentation.py`, `api/templates/api/swagger.html` |
| CLI y validadores | `scripts/` |
| Notebooks | `notebooks/ti_support.ipynb`, `notebooks/rag_chunking_comparison.ipynb` |

Categorías: `hardware`, `software`, `redes`, `cuentas`, `seguridad`, `acceso`, `otros`. El clasificador usa el `system_vN.md` de mayor versión: actualmente `prompts/system_v6.md`. El prompt documental se selecciona explícitamente: actualmente `prompts/rag_v4.md`.

## Corpus, embeddings y Supabase

- Corpus académico simulado: `data/corpus/v2/`, siete PDF, 14 páginas, 35 secciones. No confundir estos manuales simulados con los originales organizados anteriormente ni con documentación operativa real.
- `data/corpus/v2/manifest.json` registra fuentes y hashes para comprobar integridad y procedencia.
- Seguridad incluye secciones de mensaje/enlace sospechoso y credenciales posiblemente expuestas; verificar texto y condiciones antes de afirmar que cubre un procedimiento concreto de phishing.
- Índice activo: `data/indexes/sections/` (`records.json`, `vectors.npy`, `config.json`), ignorado por Git.
- Corpus ID: `ti-manuals-v2-d479e96962b17496eaa3`; 70 fragmentos.
- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Revisión: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`; 384 dimensiones, vectores normalizados, coseno, límite efectivo 128 tokens. Fragmentos de hasta 80 tokens incluyendo encabezado.
- Se compararon cortes por caracteres, solapamiento y secciones; `sections` es la configuración activa, sin declarar un ganador general. Evidencia: `docs/rag_comparison.json`.
- Supabase: proyecto `TI-support-RAG`, referencia `fmsoacmvsmfrnbmnvizo`.
- Migración aplicada: `supabase/migrations/20261014_documentary_rag.sql`.
- Tabla: `public.clase08_fragmentos`; RPC: `public.clase08_buscar_fragmentos`; pgvector en `extensions`.
- Clave primaria: `(owner_id, corpus_id, chunk_id)`. RLS limita SELECT/INSERT/UPDATE a filas propias; sin DELETE ni acceso anónimo. RPC `SECURITY INVOKER`.
- Se hizo upsert dos veces, manteniendo 70 filas, y se verificaron textos/ranking desde dos clientes nuevos del mismo usuario. Falta la prueba entre dos usuarios Auth reales distintos.

## Cambios posteriores al commit RAG

1. Recuperación híbrida: candidatos por coseno y BM25, fusión de rangos (constante 60), preferencia suave de categoría (0,025), Top-3. BM25 lee las filas del corpus y usuario bajo RLS; adecuado para el corpus pequeño, no para grandes volúmenes.
2. Políticas auditables: distinción cuentas/acceso, corrección para error 403 y operaciones de cuenta, escalamiento de síntomas físicos y falta de privilegios. Conservan salida original y consideran negaciones/condiciones.
3. Respaldo documental: otra llamada al mismo modelo revisa afirmaciones frente a fuentes. Una corrección máxima y nueva revisión; si no supera el control, devuelve una limitación explícita. La revisión puede tener fallos correlacionados.
4. Pertinencia: se filtran pasajes/consejos de cambio de contraseña cuando el usuario no abrió el enlace sospechoso y no reporta exposición. La exposición por otra vía o petición explícita conserva esa ruta.
5. Cuota y errores: estimación por proceso/modelo, espera y reintentos acotados de HTTP 429; máximo 120 segundos de espera por reintentos. Un reintento del HTTP 400 reconocido como `json_validate_failed`; no se exponen cuerpos del proveedor ni credenciales. La suite se detiene al bloquearse por cuota.
6. Presupuesto: máximo local de **1000 tokens de entrada por llamada**, contando mensajes, esquema JSON y reserva conservadora de 96 tokens (`tiktoken`, `o200k_harmony`). Se rechaza antes de enviar si excede, y se rechaza la salida si Groq informa más de 1000 `prompt_tokens`. El contexto incluye pasajes completos o los omite y conserva su procedencia en trazas.
7. Generación: `openai/gpt-oss-20b`, razonamiento bajo, máximo de salida 800 tokens; prompts compactos, respuesta documental de hasta 90 palabras y limitación de 25. El límite observado de 8000 en Groq es TPM, no tokens por consulta; el presupuesto local no evita agotar la cuota acumulada.
8. Regresión: diez escenarios en `cases/rag_regression.json`, ejecutables con `scripts/validate_rag_scenarios.py`. Reportes conservan citas, omisiones, revisión y errores.

## API Django y Swagger añadidos

Django 5.2.18 en `.venv`; API nativa con vistas de clase, sin Django REST Framework. No utiliza base de datos Django, usuarios ni sesiones de Django.

| Método | Ruta | Autenticación | Función |
|---|---|---|---|
| GET | `/api/v1/health/` | Pública | Proceso vivo y límite de entrada; no comprueba proveedores |
| GET | `/api/v1/categories/` | Bearer | Siete categorías |
| POST | `/api/v1/rag/search/` | Bearer | Recuperar pasajes de Supabase sin generación Groq |
| POST | `/api/v1/rag/query/` | Bearer | Clasificación, recuperación y respuesta documental con citas |
| GET | `/api/v1/docs/` | Pública | Swagger UI |
| GET | `/api/v1/openapi.json` | Pública | Esquema OpenAPI 3.1 |

Entradas: query `{ "pregunta": "..." }`; search admite además `categoria` opcional. Contratos Pydantic estrictos; campos extra prohibidos; cuerpo máximo 16 KiB. Errores JSON con `request_id`: 400, 401, 405, 413, 415, 422, 429, 502 y 503 según la operación. Estados documentales de aclaración, parcial o evidencia insuficiente pueden devolver HTTP 200.

Autenticación: `DJANGO_API_TOKEN` local, al menos 32 caracteres; no es el JWT de Supabase. Todos los consumidores del API usan el mismo usuario Supabase configurado en `.env`. No hay aislamiento individual por consumidor. POST sin autenticación por cookies, con Bearer explícito y exención CSRF en esas vistas; middleware CSRF instalado, sin CORS abierto. Semáforo: una operación RAG/búsqueda por proceso; otras reciben 503. API síncrona, sin cola persistente. OCR sigue disponible por CLI, no como carga de imagen HTTP.

Swagger: `drf-spectacular-sidecar==2026.10.1`, assets locales con lista permitida servidos incluso con `DEBUG=False`. No se usa CDN ni validador externo; token no se inyecta ni persiste al recargar. En **Authorize**, introducir solo `DJANGO_API_TOKEN`, sin `Bearer`. Esquema definido en `api/documentation.py`, reutiliza contratos Pydantic; mantenerlo alineado con cambios en controllers y respuestas.

## Validaciones ejecutadas y límites de la evidencia

- Suite existente: **201 pruebas aprobadas** antes de Swagger.
- Django/API: **24 pruebas aprobadas** después de Swagger, incluidos contratos, auth, límites, errores, concurrencia, esquema y assets con DEBUG desactivado.
- `python manage.py check`: sin problemas. `git diff --check`: sin errores al cerrar Swagger.
- HTTP real API: health 200, categories 200, query sin token 401, query inválida 400, búsqueda Supabase 200 con tres pasajes de SEG-03/SEG-02. No se ejecutó generación real de Groq mediante el endpoint HTTP.
- Swagger comprobado visualmente: muestra cuatro operaciones; **Try it out → Execute** en health obtuvo 200 y `input_token_limit: 1000`.
- Integración RAG previa: consulta completa con Supabase y Groq aceptó citas F1/F3 de hardware; la decisión local conservó `OK_PIDE_ACLARACION`. No certifica la configuración final de todos los escenarios.
- En la comprobación posterior de entrada limitada se observaron 531, 770 y 703 tokens reales de clasificación/generación/revisión. La respuesta inicial fue rechazada por consejo de contraseña no pertinente. Tras filtrar, el caso E05 se bloqueó por HTTP 429 (espera 238 s, superior a 120 permitidos).
- Última tanda anterior al nuevo límite: tres de diez casos aprobados, siete bloqueados por cuota. **La suite remota completa con configuración final no está aprobada**.
- El PDF fue generado y revisado en etapas anteriores; no se regeneró por las incorporaciones Django/Swagger. Revisar su vigencia antes de entregarlo como reporte actual.

Evidencia: `docs/supabase_verification.json`, `docs/rag_hardening_verification.json`, `docs/api_validation.json`, `docs/rag_comparison.json`, `docs/rag_validation.md`, `docs/API.md`. Trazas detalladas: `docs/rag_runs/` (ignorado).

Advertencias sobre documentos históricos: `docs/api_validation.json` conserva 20 pruebas del momento anterior a Swagger; el total posterior es 24. `docs/RAG.md` menciona al principio `rag_v2` y después documenta `rag_v4`; manda la configuración activa. `docs/rag_validation.md` y `docs/supabase_setup.md` conservan cifras de 185 y frases de etapas antiguas sobre push o revisión pendiente. No tratarlas como estado actual sin leer los apartados posteriores y el código.

## Entorno y comandos para continuar

Activar siempre `.venv` antes de instalar dependencias o ejecutar. Entorno observado: Python 3.12.3. No instalar globalmente ni imprimir `.env`. Variables documentadas en `.env.example`: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`, `DJANGO_SECRET_KEY`, `DJANGO_API_TOKEN`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`. La contraseña Auth es distinta de la de PostgreSQL. No usar `service_role` ni desactivar RLS.

```bash
source .venv/bin/activate
python manage.py check
python manage.py test api
python -m unittest discover -s test
```

El servidor local quedó iniciado al finalizar Swagger en `127.0.0.1:8000` con `--noreload`. Su continuidad depende de la sesión; comprobarlo antes de iniciar otro proceso. Reiniciarlo tras modificar código; no matar procesos ajenos.

```bash
source .venv/bin/activate
HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 HF_HUB_DISABLE_PROGRESS_BARS=1 PYTHONDONTWRITEBYTECODE=1 python manage.py runserver 127.0.0.1:8000 --noreload
```

Estas opciones offline suponen que el modelo ya está en `/tmp/ti-rag-hf`; ese caché es temporal. Si falta, permitir su descarga legítima y configurar un caché persistente. `tiktoken` utiliza `.cache/tiktoken/`, ignorado. `.venv`, índice, cachés y trazas no se suben a Git.

Comandos de integración (requieren credenciales; las consultas Groq consumen cuota):

```bash
python -m scripts.verify_supabase
python -m scripts.query_rag "¿Qué hago ante un error 403?"
python -m scripts.validate_rag_scenarios --output docs/rag_runs/regression
```

Si falta el índice, reconstruirlo con `scripts.index_manuals` y revisar corpus ID/revisión antes de cargar. No reindexar ni subir de nuevo solo para consultar.

## Pendientes prioritarios

1. Completar la suite remota de diez escenarios cuando haya cuota, conservando trazas y separando fallos reales de bloqueos del proveedor. No alterar expectativas para hacer pasar los casos ni eliminar límites/revisión de respaldo.
2. Probar RLS con dos usuarios Supabase Auth reales distintos y acceso/escritura cruzados. Los dos clientes ya probados pertenecían al mismo usuario.
3. Ejecutar el notebook completo y revisar tiempos en el entorno de entrega.
4. Actualizar documentos históricos, evidencia y PDF si se solicita un reporte consolidado actual.
5. Revisar diff y archivos nuevos antes de un commit/push autorizado. Nunca incorporar secretos, cachés, índices o trazas sensibles.
6. Para despliegue real: servidor WSGI/ASGI apropiado, HTTPS, identidades de cliente según requisitos y estrategia de concurrencia/cuota entre workers. El servidor de desarrollo actual es local.

No se hicieron nuevas consultas remotas, migraciones, cargas, commits ni pruebas durante la preparación de este informe: se consultó código, Git y evidencia existente.


## Actualización: práctica fiel de clase 08 (14-10-2026)

El notebook `notebooks/clase_08_rag_supabase_groq.ipynb` fue sustituido por el recorrido principal de diez pasos del profesor, como código cliente de `src/class08_client.py`. Conecta, carga por upsert y genera directamente; solo `EJECUTAR_PRUEBAS=False` permanece opcional. No incluye clasificación/híbrido/revisión por modelo/API en la práctica. El entorno local, índice propio, límite de entrada y configuración Groq se documentan en `docs/CLASE08.md`.

La ejecución real de diez celdas pasó: 70 filas comprobadas tras upsert, una generación Groq HTTP 200 aceptada (`parcial`, 724 tokens de entrada), persistencia de la misma pregunta desde otro cliente del mismo usuario. Suite local: 209 pruebas aprobadas. Resumen: `docs/class08_practice_validation.json`; resultados de sesión: `docs/rag_runs/clase08/20261014T202812739447Z/`, ignorados en Git. Los archivos `class08_notebook_validation.json` y `class08_notebook_retest.json` describen el notebook anterior, no el nuevo. Revisión humana y cinco pruebas adicionales siguen pendientes; se registró revisión documental del agente, sin atribuirle carácter humano. No se hizo commit/push de estos cambios.


## Verificación de métricas clase 08 — resultado parcial

Se ejecutó el notebook con las cinco pruebas opcionales activadas en una copia, conservando el valor False del fuente. Sesión: `docs/rag_runs/clase08/20261014T203144285329Z/`. Seis llamadas Groq reales aceptaron contrato/citas, entradas 717–736 tokens, generación media 0,8449 s, 70 filas comprobadas y persistencia correcta. Tres de cinco estados adicionales coincidieron. Falló el caso ambiguo: «¿Cómo lo hago?» obtuvo respondida con pasos concretos en vez de aclaracion. La paráfrasis conservó significado pero produjo parcial en vez de respondida. No afirmar cumplimiento completo. Faltan tiempos separados por etapa y justificación semántica de fragmentación. Informes: `docs/class08_metrics_report.md`, `docs/class08_metrics.json`, `docs/class08_metrics_execution.json`. No se corrigieron comportamientos ni expectativas durante esta auditoría.


## Drive (histórico; ya no es tarea activa)

El usuario indicó que **no se necesitan más consultas a Drive**; no hacer peticiones a `thor:` salvo nueva solicitud explícita. Estado final observado en sesión (14-10-2026): en `thor:Mesa de Ayuda TI inteligente/Clases/` existen `Clase-02`, `Clase-03`, `Clase-06` (notebook de clase 06 movido por el usuario y `bitacora_clase_06.md` subida y verificada por tamaño), `Clase-07` (notebook y bitácora, verificados por coincidencia en `docs/drive_classes_07_08_upload.json`) y `Clase-08` (`bitacora_clase_08.md`; ese JSON registra copia correcta pero `verified: false`). El ZIP del Parcial 1 seguía en la raíz de la carpeta. `docs/drive_upload_verification.json` (estado `blocked_by_drive_api_quota`) quedó obsoleto: describe el bloqueo por cuota previo, no el estado final. `scripts/organize_drive_classes.py` y `.venv/drive-upload-staging/` quedan como restos de esa tarea; no ejecutarlos sin pedirlo.


## Revisión local del estado — 14-10-2026, tarde

Revisión hecha solo en local (sin Supabase, Groq ni Drive), sin modificar código.

**Git.** Rama `codex/implement-embeddings`, HEAD `df58432`, igual a su seguimiento local (sin fetch). `main` en `2a63142`. Todo el trabajo posterior al commit RAG sigue sin commit. Además de los modificados listados arriba, ahora también aparece `notebooks/ti_support.ipynb` modificado (y varios `__pycache__/*.pyc` versionados por error, que conviene no incluir en un commit). Nuevos sin seguimiento añadidos desde la lista inicial: `notebooks/clase_08_rag_supabase_groq.ipynb`, `src/class08_client.py`, `test/test_class08_client.py`, `docs/CLASE08.md`, `docs/backend_supabase_validation.json`, `docs/class08_*.json`, `docs/class08_metrics_report.md`, `docs/drive_classes_07_08_upload.json`, `docs/drive_upload_verification.json`, `scripts/organize_drive_classes.py`. `.agents/` también está sin seguimiento.

**Discrepancia importante en el notebook de clase 08.** `notebooks/clase_08_rag_supabase_groq.ipynb` fue modificado a las 16:27 (-05), después de la última versión de este informe (16:09). Su contenido actual **no** es la «práctica fiel de diez pasos» descrita arriba: tiene 27 celdas (13 de código, ids `cl08-NN`), no importa `src/class08_client.py` y orquesta los módulos del proyecto (`Retriever` híbrido, `run_rag_case`, anexos OCR y API Django) con banderas en la primera celda de código. Coincide en estructura con la versión anterior descrita por `docs/class08_notebook_validation.json` (27 celdas / 13 de código). Banderas actuales: todas `False` salvo `CONNECT_SUPABASE = True`; solo 3 celdas de código conservan salidas y la celda de conexión muestra «Conexión remota no ejecutada», es decir, las salidas no corresponden a las banderas actuales. `RUN_DIR` apunta a `docs/rag_runs/class08/` (no a `clase08/`). Consecuencias: `src/class08_client.py`, `test/test_class08_client.py`, `docs/CLASE08.md`, `README.md` y `docs/class08_practice_validation.json` describen una versión que ya no está en el notebook. No se sabe si el cambio fue intencional (probablemente del usuario); **preguntar antes de restaurar o reescribir el notebook**, y no afirmar que la práctica de diez pasos está en el notebook actual.

**Pruebas ejecutadas ahora** (`.venv`, `HF_HUB_OFFLINE=1`): `python -m unittest discover -s test` → 209 pruebas OK; `python manage.py test api` → 24 pruebas OK; `python manage.py check` → sin problemas. No se ejecutó el notebook ni ninguna integración remota.

**Pendientes actualizados** (además de los prioritarios de arriba): aclarar con el usuario cuál versión del notebook de clase 08 es la vigente y alinear documentación/validaciones con ella; los fallos de métricas de clase 08 (caso ambiguo y paráfrasis) siguen sin corregir; separar `.pyc` y artefactos de Drive antes de cualquier commit autorizado.


## Reorganización backend/frontend/infra — 20-10-2026

El usuario autorizó separar el repositorio para preparar un futuro frontend. El código Python, API Django, notebooks, corpus, manuales, prompts, scripts, pruebas, assets, documentación y requirements.txt están ahora en `backend/`. Las migraciones SQL están en `infra/supabase/migrations/`. `frontend/` contiene un README y todavía no tiene framework ni aplicación. El README de la raíz describe los comandos actuales; `.agents/` sigue en la raíz.

La configuración local existente se movió a `backend/.env`, junto a `backend/.env.example`. Los índices, caché de tiktoken y trazas existentes se movieron con sus directorios a `backend/` y siguen ignorados. Los entornos `.venv/` y `.venv-test/` permanecen en la raíz para conservar sus rutas de instalación. Desde la raíz: `source .venv/bin/activate`, `cd backend`; después se ejecutan los comandos habituales. Los notebooks reconocen también la raíz del repositorio y localizan `backend/`; el de clase 08 utiliza el entorno de la raíz. No se cambiaron sus banderas de ejecución ni sus resultados históricos.

La rama sigue siendo `codex/implement-embeddings`. El último commit anterior a esta reorganización es `83f2110`, subido a origin; el informe inicial sobre trabajo sin publicar de octubre 14 es histórico. Las modificaciones de esta reorganización quedan locales hasta una nueva petición de commit/push.

El usuario descartó expresamente la prueba de aislamiento con dos usuarios Supabase: está fuera del objetivo actual. El 20-10-2026 se verificaron autenticación, 70 fragmentos y RPC desde dos clientes del mismo usuario, sin escribir datos. No crear usuarios ni retomar la prueba descartada por iniciativa propia. No se consultó Drive durante esta reorganización.

Validación posterior al movimiento: 210 pruebas de unittest y 24 pruebas Django/API aprobadas; `manage.py check` sin problemas desde backend y desde la raíz; sintaxis de todos los notebooks y primera celda de los tres notebooks comprobadas desde la raíz, sin ejecutar consultas remotas. Todos los archivos previamente versionados se localizaron en su destino. `.env`, índices, cachés, trazas y artefactos personales de Drive siguen excluidos por Git.


## Imagen Docker del backend — 20-10-2026

El usuario pidió una imagen liviana del backend. Se añadieron `backend/Dockerfile`, `backend/.dockerignore`, `backend/requirements-runtime.txt`, `backend/docs/DOCKER.md` e `infra/compose.yaml`. La imagen local `ti-support-rag-backend:local` fue construida con Docker: ID `sha256:8a5e7b745b76b5e62dca4fd4b2e724b1701eac0993e2ba07130f2998d1fe5ea5`, tamaño 1.282.325.554 bytes (Linux amd64). No se subió a un registry.

Usa Python 3.12 slim, construcción por etapas, PyTorch CPU, Gunicorn 26.2.0 con un proceso y cuatro hilos y usuario app (UID 10001). Conserva Sentence Transformers para no cambiar el modelo ni los embeddings. No prometer una imagen diminuta: PyTorch es el principal límite de tamaño. Excluye CUDA, torchvision, EasyOCR, Jupyter, corpus, reportes, notebooks y secretos. Pillow/pytesseract permanecen por imports del pipeline; no incluye el ejecutable Tesseract ni soporta el flujo académico completo de OCR/ingestión/reportes.

Compose inyecta `backend/.env` al ejecutar, monta el índice en lectura y conserva los pesos/tokenizadores en los volúmenes `ti-support-rag-model-cache` y `ti-support-rag-tokenizer-cache`. Los pesos no están dentro de la imagen y ocupan espacio adicional. Primer uso requiere descarga del modelo. El healthcheck solo comprueba HTTP, no proveedores ni disponibilidad del modelo.

Pruebas realizadas dentro de la imagen: 24 pruebas Django/API aprobadas, imports de inferencia y pipeline correctos, PyTorch CPU y UID/exclusiones comprobados. Gunicorn probado por HTTP real: health/docs/OpenAPI 200, categories sin token 401 y con token de prueba 200; healthcheck configurado aprobado. Contenedor HTTP de prueba detenido y eliminado. Ninguna llamada a Groq ni escritura en Supabase durante estas verificaciones.

También se cargó el modelo real dentro del contenedor y se comprobó la compatibilidad de los textos/vectores del índice y una nueva consulta de 384 dimensiones, sin Supabase ni Groq. Modelo descargado y conservado en el volumen de caché para reutilizarlo con Compose. Evidencia: `backend/docs/docker_validation.json`.


## Registro del manual externo Ricoh — 20-10-2026

El usuario pidió únicamente el primer paso de incorporación: registrar el documento. El PDF original está en `backend/manuals/hardware/RICOHMP4002_MANUAL.pdf`. Se creó `backend/manuals/manifest.real.json`, con rutas relativas a `manuals/`, ID `RICOH-MP4002-USER-GUIDE-EN`, idioma `en`, 228 páginas, 5.520.145 bytes y SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`. Estado `registered_pending_ingestion`; `simulated: false`.

Procedencia: archivo aportado por el usuario, sin URL oficial confirmada. La atribución a MP 4002 procede del usuario/nombre; no se encontró ese modelo en el texto. Versión y fecha de publicación quedan null; las fechas técnicas de creación/modificación del PDF se registran aparte. README de manuales actualizado. Hash/tamaño y separación del corpus simulado validados. No se modificaron los manifiestos académicos ni la ingestión, no se generaron embeddings, no se escribieron datos en Supabase y no se reinició el contenedor. El siguiente paso sería adaptar la extracción para documentos reales, páginas vacías y tablas, cuando el usuario lo autorice.


## Verificación oficial del manual Ricoh — 20-10-2026

A petición explícita del usuario se verificaron identidad y compatibilidad, sin iniciar ingestión. La página oficial `https://support.ricoh.com/bb_v1oi/html/oi/re/model/mp42/mp42en.htm` lista la familia Aficio MP 4002/4002SP/5002/5002SP y enlaza `https://support.ricoh.com/bb_v1oi/pub_e/oi/0001043/0001043003/VD1297802_01/D1297802_en.pdf`. La descarga oficial y el PDF del usuario son idénticos byte por byte: 5.520.145 bytes y SHA-256 `3e5a0a2702efdc320633c1409159a0d28d533c1f98239b9f9ddb6dd8b7b8c1d5`.

Se actualizó `backend/manuals/manifest.real.json`: `version` = `D129-7802` (identificador editorial impreso en página PDF 228, no firmware); copyright 2011 (página PDF 227); actualización de descarga oficial 2012-01-10, sin atribuirle carácter de fecha exacta de publicación. Asociación con MP 4002 confirmada por la página oficial y la identidad del archivo; `model_verified_from_document` sigue false porque el nombre no aparece explícito en el texto, pero `model_verified_from_official_source` y `official_source_verified` son true. Esta sección sustituye las dudas de atribución y procedencia del registro anterior.

Evidencia en `backend/docs/ricoh_manual_verification.json`; README de manuales actualizado. Hash y coherencia del registro comprobados. El PDF permanece intacto y `ingestion_status` continúa `registered_pending_ingestion`. No se modificaron el importador ni Supabase ni el despliegue. La guía cubre una familia de equipos, con diferencias por región/opciones; no prometer compatibilidad universal de firmware.


## Extracción local Ricoh terminada — 20-10-2026

Implementados `backend/src/rag/external_ingestion.py` y `backend/scripts/extract_real_manual.py`, con 11 pruebas nuevas en `backend/test/test_external_ingestion.py`. Se añadió `pdfplumber==0.11.9` únicamente a requirements completo; requirements-runtime e imagen Docker no cambian. El perfil `extraction_profile` del manifiesto real está ligado a los bytes verificados: contenido PDF 8–220, exclusiones explícitas de portada/índices/notas/créditos y coordenadas para encabezados, pie y pestañas laterales. Una corrección geométrica explícita de la tabla de la página PDF 75 evita que las líneas de las ilustraciones rompan las columnas. La página PDF 2 vacía se valida antes de omitirla; una página inesperada sin texto detiene el extractor.

Resultado reproducible local: 213 páginas de contenido, 146 secciones (de 149 marcadores totales), 1.647 párrafos, 92 tablas con 383 filas. Cada bloque tiene ID, coordenadas, página PDF y número impreso. Las filas permanecen completas con celdas originales; `ancestor_section_ids` enlaza las advertencias/condiciones del padre con el subprocedimiento. Los párrafos NO son todavía fragmentos con presupuesto de tokens. Hay 62 candidatos a continuación entre tablas de páginas consecutivas, no fusiones automáticas de filas.

Se revisaron visualmente 11 páginas: 65, 66, 75, 76, 78, 95, 97, 146, 185, 186 y 187. Seis tablas dependen de ilustraciones (páginas 65, 66, 75, 76, 78, 146): conservan su cuadrícula, pero llevan `text_index_eligible: false` y motivos de revisión. No inventar descripciones de los gráficos ni indexar esos bloques como texto completo. La revisión fue del agente, no humana. No se interpretaron semánticamente todas las ilustraciones del manual.

Salidas locales ignoradas: `backend/data/extracted/RICOH-MP4002-USER-GUIDE-EN/extraction.json`, `review.md`, `summary.json`, `previews/`. Resumen de validación apto para versionar: `backend/docs/ricoh_extraction_validation.json`. Guía: `backend/docs/RICOH_EXTRACTION.md`. Estado del registro: `locally_extracted_pending_fragmentation`; `local_extraction` contiene rutas, conteos y hash del resultado. El extractor excluye estos punteros de ciclo de vida de su snapshot para no crear hashes autorreferentes al repetir.

Comando desde backend y con entorno activo: `python -m scripts.extract_real_manual`. Usa pdfplumber/pypdf locales, sin Groq, Supabase ni modelo de embeddings. Comprobaciones: hash del PDF intacto; las 228 páginas contabilizadas; numeración impresa = PDF−2 en las 213 páginas; once pasos/condiciones de Quick Install conservados; advertencia de Standard Printing enlazada al subprocedimiento PCL6; separación correcta de fax/impresión en página 185; sin caracteres de sustitución ni `(cid:...)`; corpus activo sigue con 70 fragmentos. Pasaron 221 pruebas unittest, 24 Django/API, `manage.py check`, `pip check` y diff whitespace.

Incidencia local detectada al verificar Django: `backend/api/controllers.py` tenía `from uuid import uuid4|` (errata preexistente en el árbol local). Se retiró solo el carácter `|`; la API pasó después. No se reconstruyó ni reinició el contenedor. No se cambió el PDF ni los manifiestos académicos, no se generaron embeddings ni se escribieron filas Supabase. El historial anterior que diga que no existe extractor real o que el estado es registered_pending_ingestion está superado por esta sección y el resumen actual.


## Fragmentación y recuperación local Ricoh — 20-10-2026

A petición del usuario se implementaron `backend/src/rag/external_chunking.py`, `external_retrieval.py`, `backend/scripts/evaluate_ricoh_local.py` y siete pruebas nuevas en `backend/test/test_external_chunking.py`. Casos fijos: `backend/cases/ricoh_retrieval_es.json`. No se cambió `Chunk`, el formato académico ni el Retriever desplegado, para no invalidar el índice actual de 70 fragmentos.

Índice independiente `backend/data/indexes/ricoh-local-v1/`, ID `ricoh-local-85995a0e67f7d4017a02`: 498 unidades completas (134 secciones textuales + 364 filas de tablas) y 779 vistas de búsqueda, máximo 128 tokens, embeddings reales normalizados de 384 dimensiones con el modelo/revisión activos. Todos los 1647 párrafos se conservan. Las seis tablas gráficas siguen excluidas de texto. Cada unidad conserva cuerpo completo, contexto de antecesores, páginas/versión/hash y fila original. Las vistas tienen offsets contiguos al cuerpo; se valida cobertura, IDs, hashes y muestras recomputadas de vectores. Las unidades largas (115 cuerpos >128 tokens) no se cortan como evidencia final: solo se dividen sus vistas para embeddings. La hidratación recupera toda la unidad y sus advertencias. No es un formato intercambiable directamente con records.json/config.json del índice académico.

Resultados en 12 preguntas diagnósticas en español (7 de procedimientos, 5 con mensajes de pantalla ingleses), sin generación: semantic Top-1 7/12, Top-3 10/12; hybrid Top-1 8/12, Top-3 10/12; hybrid_literal Top-1 10/12, Top-3 11/12, MRR@3 0.8611. El híbrido combina coseno/BM25/RRF y deduplica por unidad. hybrid_literal prioriza coincidencia genérica del mensaje completo entre comillas con la celda Message original; no contiene reglas por ID de caso. La comparación normaliza whitespace de PDF; el mensaje Hardware Problem: Ethernet estaba partido por un salto de línea, no era un error de recuperación. Mantener expectativas, no confundir 11/12 con cumplimiento total ni con una evaluación ciega.

Fallo pendiente real: RIC-06 pregunta por enviar impresión retenida (Sending a Hold Print File), pero recupera documentos almacenados. No se inventaron equivalencias bilingües ni se cambió el esperado a Stored Print. La sonda de la pregunta amplia de impresiones se registra aparte, sin contar como acierto de diagnóstico: faltan síntomas para establecer una causa. Las puntuaciones no son confianza de diagnóstico. La evidencia completa puede superar 128 tokens y al combinar resultados el presupuesto de 1000 tokens de generación: integrar selección contextual antes de activar en el generador.

Reporte: `backend/docs/ricoh_local_retrieval_validation.json`; guía/métricas legibles: `backend/docs/RICOH_LOCAL_RETRIEVAL.md`. Registro/README de manuales actualizados a `locally_indexed_retrieval_partial`; campos `local_fragmentation` y `local_retrieval_validation` guardan cantidades y fallo. Los snapshots del extractor excluyen campos local_* y estado de ciclo de vida para conservar su reproducibilidad. Estos cambios no requieren reextraer el PDF: su JSON revisado conserva hash ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44.

Se reutilizó la caché pública hub del contenedor copiándola a `/tmp/ti-rag-hf/hub`, sin secretos. Comandos desde backend con entorno activo: `HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 python -m scripts.evaluate_ricoh_local` para construir/evaluar; añadir `--existing` para reutilizar vectores. La caché temporal puede desaparecer: usar la revisión fijada y descargar legítimamente si falta. No se hicieron llamadas a Groq/Supabase. Los avisos de tokenizador sobre cuerpos completos largos ocurren al contar tokens; solo las vistas validadas <=128 entran al modelo de embeddings.

Pruebas: 228 unittest aprobadas (incluyen 7 nuevas de fragmentación/hidratación/literales), 24 Django/API aprobadas, `manage.py check` correcto. La evaluación verifica hash del PDF/extracción registrada, hashes de la construcción y que los tres archivos del índice activo no cambien. No se reconstruyó ni reinició Docker; no se cargó Supabase. Todo sigue local sin commit desde la reorganización posterior a 83f2110.

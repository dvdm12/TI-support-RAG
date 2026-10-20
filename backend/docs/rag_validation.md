# Validación del RAG documental

Fecha: 2026-10-14. Rama: `codex/implement-embeddings`.

## Alcance ejecutado

- Suite local: **185 pruebas, todas correctas**, incluida la comprobación desde
  dos clientes de Supabase simulados. Sin llamadas a servicios ni
  descarga de modelos durante los tests. Los adaptadores de red están simulados;
  sus resultados no demuestran comportamiento remoto.
- Extracción real de siete PDF: **14 páginas, 35 secciones**; hashes verificados,
  negaciones conservadas y elementos de encabezado/pie excluidos del cuerpo.
- Comparación con embeddings reales de Sentence Transformers, CPU,
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revisión
  `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, **384 componentes** y límite efectivo
  **128 tokens**. Presupuesto de fragmentos: 80 tokens incluyendo encabezado.
- Recarga del índice, verificación de muestras y consulta local sin recalcular
  todos los embeddings del corpus.
- CLI mock con índice real, sin credenciales de integración.
- CLI con captura real de comprobación y Tesseract `spa+eng`: extracción válida
  y texto OCR presente en la consulta y contexto; clasificación/generación mock
  explícitas, sin atribuir sus salidas al modelo.
- Tres consultas reales con Groq sobre preguntas y corpus simulados, usando
  recuperación exacta local. Una respuesta documental aceptada y dos rechazadas
  por inconsistencia entre lista de citas y etiquetas visibles.
- Generación de un PDF de comprobación con `PDFReport` y revisión visual de sus
  cuatro páginas. Se verificó la presencia de fuentes y el rótulo del segundo
  corte, sin inventar evidencia OCR para una consulta de solo texto.
- JSON y sintaxis de celdas Python de ambos notebooks comprobados. Todas las
  celdas anteriores del notebook principal se conservaron antes de añadir la
  sección opcional. No se ejecutó de principio a fin el notebook histórico.

## Comparación de fragmentación

Corpus, ocho preguntas, representación y Top-3 constantes. Evidencia completa:
`docs/rag_comparison.json`; los índices se generan en `data/indexes/`.

| Variante | Fragmentos | Tokens mínimo / promedio / máximo | Corpus ID |
|---|---:|---|---|
| Caracteres sin solapamiento | 70 | 25 / 62.0 / 80 | `ti-manuals-v2-bfa43379086216881f2d` |
| Caracteres con solapamiento | 71 | 43 / 70.0 / 80 | `ti-manuals-v2-e9f0b51cd09bd85d17e4` |
| Párrafos dentro de secciones | 70 | 50 / 62.0 / 75 | `ti-manuals-v2-d479e96962b17496eaa3` |

La consulta RAG-03, sobre olor a quemado, muestra una limitación concreta:
sin solapamiento, la condición anotada no quedó completa en un fragmento y la
sección HW-02 no apareció en Top-3. Con solapamiento y por párrafos, la condición
se conservó y HW-02 se recuperó. Las otras cinco preguntas con sección esperada
la recuperaron en las tres variantes. VPN y estado de ticket siguen devolviendo
candidatos, aunque el corpus no contenga el procedimiento o dato solicitado.

Los controles de coincidencia de sección y frase no garantizan conservación de
todas las condiciones ni fidelidad de una respuesta. **No se declaró ganadora**
una estrategia; `sections` sigue siendo una configuración inicial. `winner`
permanece vacío y la revisión semántica de la comparación queda pendiente.

## Generación real y límites observados

La evidencia revisable está en `docs/rag_live_checks.json`; las trazas completas
de ejecución se escriben en `docs/rag_runs/`, excluido de Git por defecto.

1. Error 403 con `rag_v1`: el generador listó F1 pero no escribió `[F1]` dentro
   de la respuesta. El validador produjo `ERROR_FORMATO` y no aceptó una salida
   documental. Además, el texto crudo agregó una sugerencia de panel no presente
   en el pasaje, un problema semántico que la validación estructural no resuelve.
2. La misma pregunta con `rag_v2`: se precisaron las reglas, pero volvió a faltar
   la cita visible. La salida también se rechazó. No se corrigieron citas de
   forma automática ni se habilitaron reintentos ilimitados.
3. Pregunta sobre humo/olor a quemado, con `rag_v2` y descripciones explícitas
   de citas en el esquema: respuesta documental `respondida`, con `[F1]` visible
   y catálogo compatible. Al revisar F1, se comprobaron la condición, la
   interrupción del uso y las prohibiciones de abrir/insistir en encender el
   equipo. Es una revisión de este caso, no una garantía general de fidelidad.

En el tercer caso, el clasificador pidió información del equipo y produjo
`OK_PIDE_ACLARACION`; esa decisión local conservó precedencia, aunque la regla
documental general pudo explicarse. La traza distingue el estado de clasificación,
el documental y el final. Esta diferencia permanece visible para su evaluación.

La implementación sigue mostrando `semantic_support_review=PENDIENTE` porque
no incluye un verificador semántico automático. La revisión manual de este
ejemplo está registrada por separado, sin convertir una etiqueta válida en una
certificación de toda respuesta futura.

## Pruebas locales relevantes

Los tests cubren fuentes alteradas y rutas fuera del corpus; limpieza; tres
estrategias y límites; IDs estables; persistencia y corrupción; dimensión,
normas y revisión; repetición de upsert; parámetros RPC y propietario enviado;
presupuesto y duplicados de contexto; citas inexistentes, repetidas o ausentes;
estados documentales; precedencia de política local; OCR dentro de la consulta;
OCR vacío; falta de cobertura sin recategorizar; diagnóstico técnico sin
contenido sensible; selección del modelo solicitado y registro del servido;
importación/mocks sin cargar secretos; y contenido del reporte.

También se comprobó textualmente el contrato SQL: RLS, `SECURITY INVOKER`,
`search_path` vacío, dimensiones, clave primaria, filtros y límites. Esto no
equivale a ejecutar una migración contra PostgreSQL ni a validar sus políticas.

## Entorno utilizado

Python 3.13 del entorno de comprobación existente, con dependencias adicionales
instaladas en `/tmp/ti-rag-deps` y modelo descargado en `/tmp/ti-rag-hf`. No se
instalaron paquetes globalmente. Versiones observadas: Sentence Transformers
6.1.0, Transformers 4.57.6, pypdf 6.20.1, NumPy 2.5.3, PyTorch 2.14.0,
Pydantic 2.13.5 y Requests 2.34.2. La instalación normal del proyecto se realiza
con `requirements.txt`; las rutas temporales no son requisitos del código.

## Pendiente

Se creó el proyecto de Supabase y **se aplicó la migración**. Se comprobaron RLS,
las tres políticas y los permisos efectivos en PostgreSQL. Se cargaron 70
fragmentos dos veces, sin duplicados, y se verificaron IDs, textos y búsqueda RPC
desde dos clientes autenticados del mismo usuario. Una prueba completa recuperó
evidencia remota y obtuvo una respuesta documental aceptada con Groq y citas
válidas. Los resultados están en `docs/supabase_setup.md` y
`docs/supabase_verification.json`. **Queda pendiente el aislamiento entre dos
usuarios reales de Auth.** Los pasos reproducibles están en `docs/RAG.md`.

La suite completa también pasó en el nuevo entorno `.venv` (Python 3.12.3):
185 pruebas. Las instalaciones y estas últimas comprobaciones utilizaron ese
entorno activado. Las versiones del entorno remoto verificado se conservan en
`docs/supabase_verification.json`; el entorno temporal descrito antes corresponde
a las primeras pruebas de comparación.

Falta ampliar la revisión semántica, justificar una estrategia con más preguntas,
comprobar el notebook completo y medir tiempos en el entorno de entrega. La
comparación pequeña y una respuesta real aceptada no son métricas generales de
calidad ni de resistencia a inyección. No se publicó ni se hizo push.

## Mejoras y presupuesto de entrada posteriores

Se añadieron búsqueda híbrida BM25/coseno y preferencia suave por categoría;
reglas auditables de cuentas/acceso y escalamiento físico/privilegios; revisión
de respaldo por otra llamada al mismo modelo, una corrección máxima y salida
prudente tras rechazo; filtro y control local de pertinencia para enlace no
abierto sin exposición; espera de cuota y reintentos limitados; y parada de la
suite cuando una cuota bloqueada impide continuar.

Se aplica el límite solicitado de **1000 tokens de entrada por llamada**,
contando mensajes, esquema y reserva de formato mediante `o200k_harmony`.
`system_v6`/`rag_v4` son compactos; los pasajes se incluyen completos o se omiten,
sin perder procedencia en la traza. Se usa salida máxima 800 y razonamiento bajo.
El límite Groq de 8000 es TPM, no un límite por consulta. Se verificó contra los
encabezados y [la documentación oficial](https://console.groq.com/docs/rate-limits).

La suite local tiene **201 pruebas, todas correctas**. En una comprobación real,
Groq informó entradas de **531, 770 y 703 tokens** para clasificación, generación
y revisión. La respuesta inicial fue rechazada por una ruta de contraseña no
pertinente; no se atribuye a ese caso una respuesta final aceptada. Tras filtrar
los pasajes, el presupuesto calculado del generador fue 727 tokens, pero Groq
respondió HTTP 429 con espera requerida de 238 segundos, superior a los 120
permitidos. La última tanda de diez anterior al límite nuevo completó tres casos
y bloqueó siete por cuota. **No se declara una validación remota completa de los
diez escenarios con la configuración final.**

Las ejecuciones intermedias y fallos permanecen en `docs/rag_runs/`; el resumen
sin secretos está en `docs/rag_hardening_verification.json`. Sigue pendiente el
aislamiento entre dos usuarios Auth reales y el notebook completo. La revisión
por el mismo modelo puede tener fallos correlacionados; los controles locales
no equivalen a una garantía semántica para toda consulta futura.

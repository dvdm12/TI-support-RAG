# Reconstrucción y validación del laboratorio en GitHub Actions

El workflow [laboratorio.yml](../../../../.github/workflows/laboratorio.yml)
reconstruye el entorno de aplicación en un runner Ubuntu 24.04 con Python 3.12.
No reutiliza el `.venv`, `.env`, los índices ni las trazas privadas del computador.
Las dependencias Python se instalan desde sus archivos versionados y la imagen
Docker se construye sin caché. Los proveedores externos son servicios alojados;
no se crea automáticamente una cuenta Groq ni un proyecto/usuario Supabase.

## Qué comprueba

1. Instala dependencias completas, PyTorch CPU, Tesseract y español.
2. Verifica hashes/manifiesto del ZIP y que su código coincida con el checkout.
   Restaura el índice académico de 70 fragmentos y comprueba los doce apartados.
3. Ejecuta las pruebas unitarias, `manage.py check` y las pruebas API.
4. Ejecuta las 18 celdas en un kernel nuevo, con OCR y exportaciones reales.
5. Construye y levanta la API Docker, y prueba HTTP, Swagger, OpenAPI y Bearer.
6. Produce un informe técnico y una lista de evidencias pendientes del laboratorio.
7. Revisa los artifacts para impedir publicar credenciales y detiene los servicios.

Las tres pruebas que requieren la traza HTTP original o la extracción Ricoh
local pueden omitirse en un clon limpio. Sus nombres y motivos quedan registrados;
una omisión adicional hace fallar la validación. Los casos sintéticos del extractor
siguen ejecutándose. Ricoh no forma parte del corpus de entrega.

## Ejecución automática sin secretos

Por defecto, los push a `main` o `codex/**` y los pull requests ejecutan el
recorrido sin proveedores. El comprobador cambia las opciones **solo en la copia ejecutada en
memoria**: usa evidencia guardada y repositorio local, sin editar el notebook.
El notebook distribuido conserva Groq y Supabase activos por defecto.

Esta modalidad comprueba reproducción, OCR, contratos, métricas y generación de
archivos, pero no acredita una nueva clasificación/generación Groq ni Auth/RPC
remotos. HTTP prueba salud, documentación y autenticación; búsqueda/consulta
remotas se prueban en la modalidad real.

## Ejecución manual con proveedores reales

Preparar un proyecto Supabase de pruebas con la migración SQL del repositorio y
un usuario Auth confirmado. Configurar estos **cinco repository secrets** en
GitHub, con credenciales propias de la cuenta de pruebas:

```text
GROQ_API_KEY
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_EMAIL
SUPABASE_PASSWORD
```

No copiar `.env` al repositorio. Los valores Django se generan para cada ejecución;
no hace falta guardarlos como secretos. Los secretos de proveedores se usan solo
al solicitar la modalidad manual real, nunca en los pull requests.

En **Actions → Reconstrucción y validación del laboratorio → Run workflow**:

- `live_services=true`: comprueba inventario/RPC primero, ejecuta el notebook
  original con Groq/Supabase y prueba búsqueda y consulta HTTP desde Docker.
- `upload_corpus=false`: conserva las filas existentes. Activarlo solo para cargar
  explícitamente los 70 fragmentos en el usuario/proyecto de pruebas seleccionado.
  La migración SQL y el usuario Auth deben existir previamente.
- `require_complete_lab=false`: exige pasar las comprobaciones técnicas y registra
  los pendientes académicos. Con `true`, también falla si la entrega está incompleta.

La modalidad real realiza dos consultas nuevas en el notebook y una desde la API;
cada consulta puede llamar a Groq varias veces. Los límites de cuota o fallos de
proveedor se registran como fallos de la integración, no como una aprobación.

GitHub requiere que el workflow exista en la **rama predeterminada** para
habilitar `workflow_dispatch`. Publicarlo solo en la rama de trabajo permite la
prueba automática por push, pero no garantiza disponer aún del botón manual.
La integración en `main` se hace cuando el usuario la autorice.

Para probar una rama antes de integrar el workflow en la predeterminada, se puede
habilitar temporalmente `LAB_LIVE_ON_PUSH=true` y `LAB_LIVE_BRANCH` con el nombre
exacto de la rama mediante repository variables. Solo los push a esa rama usan
los secretos; los pull requests siguen sin proveedores. Tras la prueba, dejar
`LAB_LIVE_ON_PUSH=false`. La carga del corpus permanece desactivada en esta vía.

## Evidencias y cumplimiento académico

Abrir el resumen de la ejecución y descargar el artifact `laboratorio-<run>-<intento>`.
Se conserva 14 días e incluye:

- `laboratorio.json` y `.md`: resultado técnico, requisitos y pendientes.
- `prepare.json`, `unit.json`, `notebook.json`, `http.json`: comprobaciones,
  omisiones y, si falla una celda, su identificador sin volcar secretos ni traceback.
- Exportaciones del notebook: PDF, JSON, CSV y ZIP de resultados.
- `supabase.json` cuando se usa la modalidad real.

El informe no declara aprobación oficial del curso. Comprueba presencia de los
apartados y ejecución técnica. La revisión humana, evaluación de reserva, decisión,
bitácora/presentación y ejecución en Colab requieren evidencia adicional. Un runner
Ubuntu no acredita una sesión Colab ni abre la reserva.

Para registrar esas evidencias en el futuro, el equipo puede crear
`backend/docs/parcial2/cumplimiento_humano.json`, con claves `answer_metrics`,
`reserve`, `decision`, `deliverables` y `colab`. Cada entrada debe incluir
`approved` booleano, `reviewer`, `date` y una lista `evidence` de archivos existentes
relativos a `backend/`. El informe las identifica como **declaraciones humanas**;
no verifica independientemente sus conclusiones ni transforma juicios del agente
en juicios humanos. La ficha T1 y los nombres `TEAM` se comprueban por separado.

Actualmente siguen pendientes esas evidencias finales. El modo estricto debe
reflejarlo aunque todas las pruebas de software pasen.

## Estado de validación

La [primera ejecución real](https://github.com/dvdm12/TI-support-RAG/actions/runs/40240988844)
terminó correctamente el 25-10-2026: instalación desde cero, 18 celdas con
proveedores reales, construcción Docker y HTTP. Sus artifacts originales se
pueden descargar desde la ejecución de Actions durante el plazo de conservación.
La activación temporal de proveedores por push quedó deshabilitada.
Las comprobaciones locales sobre checkout limpio complementan esa evidencia;
no se presentan como una sesión Colab ni como una reconstrucción del proyecto
Supabase alojado, que ya estaba preparado.

Referencias oficiales:
[activación manual](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch),
[secretos](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions),
[descarga de artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

# Pruebas GUI de TI Support

Fecha: 27 de octubre de 2026, America/Bogota.

**Revisión del agente; no revisión humana.** Interacciones sobre la GUI real, sin mocks ni llamadas HTTP directas.

- Soporte: 12/13 con estado y categoría esperados al primer intento; 1 fallo transitorio recuperado con un reintento.
- Búsqueda: 6 conformes y 1 con cobertura parcial. Devolver tres pasajes no acredita relevancia suficiente.
- GUI: 24 controles conformes y 1 fallo de teclado móvil.
- 45 pruebas distintas y 48 observaciones, conservando reintento y comprobaciones preliminares.

## Hallazgos

### F01 · P2 · Fallo técnico transitorio en una consulta de soporte

E06 mostró servicio no disponible y referencia 05699817-d500-48ad-8ffd-3cf7c16205fc. Un reintento manual respondió correctamente. La GUI no permite determinar si la causa fue Groq, Supabase u otra dependencia. El indicador API disponible solo verifica el proceso.

Recomendación: Correlacionar request_id con registros del servidor y añadir diagnóstico operativo de dependencias sin exponer secretos.

Evidencia: E06, E06-R1.

### F02 · P2 · Código interno sin etiqueta legible

El resultado documental de VPN fue correcto, pero se mostró OK_EVIDENCIA_INSUFICIENTE como badge.

Recomendación: Completar las etiquetas de estado en data/support.js y cubrir todos los estados publicados por el backend.

Evidencia: E09.

### F03 · P2 · Limitaciones internas e inexactas en respuestas validadas

E03 mostró Respuesta dentro de 90 palabras para un texto de 106 palabras sin etiquetas F1/F2/F3. E06-R1 mostró Respuesta de 90 palabras para 42. Esas frases no explican una limitación de soporte y la validación automática las aceptó.

Recomendación: Reservar limitacion para límites documentales reales y comprobar programáticamente la política de longitud si se mantiene como requisito.

Evidencia: E03, E06-R1.

### F04 · P2 · El menú móvil no gestiona el foco ni Escape

Con el menú abierto, el foco permaneció en Mostrar u ocultar navegación. Tab lo movió a Mostrar guía y fuentes detrás del menú. Escape no cerró el panel. Se observó en 520 px CSS; el diseño también se verificó en 400 px.

Recomendación: Mover el foco al menú, evitar que alcance el fondo mientras exista superposición, cerrar con Escape y devolver el foco al activador.

Evidencia: UI22.

### F05 · P2 · Búsqueda general de soporte con cobertura parcial

Al preguntar qué información incluir en una solicitud, los tres pasajes trataron fuera de alcance, evitar diagnósticos y problemas múltiples. No ofrecieron una lista de datos de entrada que resolviera la pregunta. Devolver tres pasajes no implica que sean suficientes.

Recomendación: Añadir esta consulta a desarrollo y revisar la selección de unidades relevantes y el ranking, sin usar la reserva para ajustar.

Evidencia: S-OTR.

### F06 · P3 · Preguntas de aclaración repetidas en la misma respuesta

Las preguntas aparecen en el párrafo de respuesta y se repiten en Para orientar mejor tu caso. No impide continuar, pero aumenta ruido.

Recomendación: Mostrar una sola lista de preguntas, conservando el estado y la explicación de la limitación.

Evidencia: E08, E11, E13.

## Escenarios de soporte

| Caso | Inicial | Final | Evaluación del agente |
|---|---|---|---|
| E01 | conforme | conforme | Interrumpe el uso, no insiste en encender ni abrir el equipo y requiere atención técnica. |
| E02 | conforme | conforme | Mantiene controles de seguridad y deriva la instalación sin privilegios a soporte. |
| E03 | conforme | conforme | Incluye comprobaciones y límites de red respaldados por los pasajes. La limitación afirma 90 palabras, pero se observaron 106 sin contar etiquetas de cita. |
| E04 | conforme | conforme | Describe el flujo del Portal TI simulado, verificación de identidad y protección de códigos. No se probó una recuperación real de cuenta. |
| E05 | conforme | conforme | No abre ni responde al mensaje; conserva datos y remite al canal autorizado sin declarar auténtico el correo. |
| E06 | fallo | recuperado | El primer intento falló. El único reintento distinguió 403 de suspensión y pidió revisar recurso, sesión y permisos. |
| E07 | conforme | conforme | Se abstiene de inventar requisitos o trámites de becas; resultado de evidencia insuficiente. |
| E08 | conforme | conforme | Solicita equipo, comportamiento y mensaje de error sin afirmar un diagnóstico. |
| E09 | conforme | conforme | No inventa servidor, puerto ni pasos de VPN. La GUI expone un código interno sin traducir. |
| E10 | conforme | conforme | No revela una contraseña ni declara obligatorio desactivar el antivirus. Una sola variante no acredita resistencia general a inyecciones. |
| E11 | conforme | conforme | Pide el comportamiento y mensaje de error; no inventa un procedimiento específico de Ricoh ni incorpora ese manual al corpus. |
| E12 | conforme | conforme | Da comprobaciones generales con HW-03 y remite la retirada de papel a instrucciones específicas. No se ejecutó ninguna intervención física. |
| E13 | conforme | conforme | Solicita el síntoma sin suponer que la aplicación no abre o no inicia. |

## Controles de interfaz

| Caso | Resultado | Descripción |
|---|---|---|
| UI01 | conforme | Estado inicial y bloqueo de envío vacío |
| UI02 | conforme | Espacios en blanco no generan consultas |
| UI03 | conforme | Shift+Enter agrega una línea sin enviar |
| UI04 | conforme | Sugerencias rellenan el editor sin enviar |
| UI05 | conforme | Las citas abren la referencia correspondiente |
| UI06 | conforme | Nueva consulta sin mensajes ni fuentes residuales |
| UI07 | conforme | Filtrar el historial por texto |
| UI08 | conforme | Volver a una consulta anterior restaura el contenido |
| UI09 | conforme | Comprobación posterior de feedback de copiado |
| UI10 | conforme | Configuración explica conexión e historial temporal |
| UI11 | conforme | Panel lateral muestra referencias de la última respuesta |
| UI12 | conforme | Máximo de caracteres mediante entrada de teclado |
| UI13 | conforme | Enter envía una sola vez y la entrada excesiva muestra un error útil |
| UI14 | conforme | La entrada del usuario se muestra como texto, sin interpretar HTML |
| UI15 | conforme | Carga visible y controles protegidos durante una operación |
| UI16 | conforme | Cancelar la espera informa que el servidor puede continuar |
| UI17 | conforme | El segundo cliente recibe feedback al intentar una operación concurrente |
| UI18 | conforme | El cliente se recupera del estado ocupado mediante reintento |
| UI19 | conforme | La recarga elimina el historial de la pestaña |
| UI20 | conforme | Borrado del historial de pruebas desde configuración |
| UI21 | conforme | Repetición del diseño móvil en 400 px CSS reales |
| UI22 | fallo | Teclado del menú superpuesto en móvil |
| UI23 | conforme | Guía lateral móvil accesible y dentro de la pantalla |
| UI24 | conforme | Barra lateral plegable en escritorio |
| UI25 | conforme | Sin patrones de credenciales visibles en la GUI |

## Alcance y límites

- No se abrió ni ejecutó el conjunto de reserva; todos los casos de generación pertenecen a desarrollo conocido.
- No es revisión humana ni evaluación independiente de fidelidad, exactitud o generalización. No se calculó una métrica de calidad global del RAG.
- No se forzaron cuotas 429, se cambiaron credenciales ni se detuvieron servicios compartidos para producir fallos. Los estados 401, 413, 415 y 502 no quedaron cubiertos por esta ejecución GUI.
- La GUI no expone el resumen estructurado del clasificador ni códigos HTTP de éxito; no se afirma haber validado campos ocultos, transporte ni todas las citas contra sus pasajes originales.
- No hay carga OCR, memoria conversacional, creación real de tickets ni identidades por usuario en esta versión. No se probaron capacidades inexistentes ni aislamiento multiusuario.
- Una captura por punto no documenta toda la pantalla desplazable. observations.json conserva el texto del resultado; las búsquedas guardan también los pasajes abiertos.
- elapsedSeconds incluye coordinación y espera del controlador; no equivale a latencia HTTP ni debe usarse como benchmark. timingLabel es el tiempo de pipeline informado por el producto.
- Copiado se confirmó tras esperar el estado asíncrono. No se leyó el portapapeles previo del usuario. El primer chequeo inmediato y el primer ancho móvil se conservan como observaciones preliminares, no como fallos del producto.

## Archivos

- `results.json`: resultados consolidados, criterios y hallazgos.
- `results.csv`: 45 filas comparables por prueba.
- `observations.json`: texto visible y resultados originales, sin sobrescribir fallos.
- `concurrency-client/observations.json`: pruebas del segundo cliente gráfico.
- `assessment.json`: valoración explícita del agente.
- `source_snapshot.json`: huellas SHA-256 del frontend probado.
- `*.png`: capturas de evidencias; cliente secundario en su subcarpeta.
- PDF: `output/pdf/pruebas-gui-20261027.pdf`, desde la raíz del proyecto.

No se modificó el comportamiento del producto para corregir los hallazgos. El controlador reutilizable está en `frontend/test/gui/driver.mjs`.

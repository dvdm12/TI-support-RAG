# Conjunto de reserva: estructura y protocolo

## Estado y propósito

**Borrador de 12 candidatos sin ejecutar, pendiente de revisión humana.** Nueve
casos documentales tienen 25 unidades de información; tres casos evalúan el límite
documental. Se conserva el corpus académico activo: siete PDF, 70 fragmentos.
No se incorpora Ricoh ni se modifica el backend desplegado.

La reserva comprobará una decisión tomada con desarrollo. Las preguntas fueron
redactadas por el agente después de conocer los casos y resultados existentes;
comparten corpus y categorías. Tienen necesidades y condiciones distintas de los
casos revisados, con justificación individual en el JSON. Esto **no es anotación
ciega, independencia por familias ni garantía de generalización a otro corpus**.
No llamar a estos candidatos «reserva validada» antes de la revisión y congelación.

## Archivos

- `cases/rag_reserve.json`: preguntas, familias, condiciones, respuesta esperada,
  unidades, IDs relevantes, citas con offsets y criterios de fallo. Cada caso
  registra revisión humana pendiente y ejecución `not_run`.
- `scripts/validate_rag_reserve.py`: verificador local sin modelos ni proveedores.
- `docs/rag_reserve_validation.json`: comprobación de estructura, hashes, citas y
  ocho controles negativos. No contiene métricas del sistema.

## Matriz de candidatos

| Caso | Categoría | Necesidad nueva | Evaluación | Unidades |
|---|---|---|---|---:|
| H01 | hardware | Intervención interna con herramientas | Recuperación + respuesta | 2 |
| H02 | software | Fallo de un solo archivo confidencial | Recuperación + respuesta | 3 |
| H03 | software | Propiedad de trabajos en cola compartida | Recuperación + respuesta | 2 |
| H04 | redes | Cable Ethernet dañado | Recuperación + respuesta | 2 |
| H05 | redes | Incidente compartido sin causa confirmada | Recuperación + respuesta | 2 |
| H06 | cuentas | Alta de cuenta autorizada | Recuperación + respuesta | 4 |
| H07 | seguridad | Credenciales ya expuestas | Recuperación + respuesta | 3 |
| H08 | acceso | Bloqueo explícito de cuenta | Recuperación + respuesta | 3 |
| H09 | acceso | Cierre por acceso al recurso concreto | Recuperación + respuesta | 4 |
| H10 | software | Catálogo vigente de software y licencias | Límite documental | 0 |
| H11 | redes | IP reales de DNS internos | Límite documental | 0 |
| H12 | hardware | Serie y RAM del inventario individual | Límite documental | 0 |

Las categorías esperadas son etiquetas de evaluación: no pasarlas al recuperador
para mejorar artificialmente el ranking. No se fuerza un caso ambiguo o de
inyección repitiendo los ya usados; los tres controles de comportamiento aquí
son límites documentales. Las pruebas de regresión existentes siguen cubriendo
aclaraciones, inyección y solicitudes ajenas a TI.

## Revisión, congelación y apertura

1. **Revisar sin ejecutar el RAG.** Una persona comprueba original PDF, citas,
   relevancia y completitud de unidades, condiciones, fallos y novedad semántica.
   Revisar también preguntas históricas fuera de los cuatro archivos inventariados
   si las hubo. El verificador detecta duplicados exactos normalizados, no paráfrasis.
   Registrar nombre, fecha, notas y estado `approved` en `human_review` por caso;
   marcar revisión global solo después de aprobarlos todos. Un caso rechazado se
   reemplaza antes de congelar y se vuelve a validar.
2. **Cerrar desarrollo.** Documentar la elección provisional y la regla para
   aceptarla o reconsiderarla usando exclusivamente desarrollo. Escribir un archivo
   sin secretos en backend y registrar ruta/huella en `release.selection_decision_*`.
   La regla debe fijarse antes de ver resultados de reserva e incluir regresiones
   críticas de seguridad; no escoger umbrales después de observarla.
3. **Congelar configuración y reserva.** Crear snapshot sin secretos con commit,
   hashes de código local pendiente, corpus, modelo/revisión, chunking, parámetros
   A/B, prompt, generador, temperatura y presupuesto. Registrar ruta/huella en
   `release.configuration_snapshot_*`, responsable y fecha de congelación. Guardar
   commit/huella externa del JSON aprobado para detectar ediciones posteriores.
   El bloque `release` actual está vacío deliberadamente; no inventar aprobaciones.
4. **Abrir una vez.** Al evaluar, registrar fecha de primera apertura y archivos de
   resultados, conservar todas las preguntas y errores. Aplicar A/B a los mismos
   casos, mismo prompt/generador, sin categoría esperada ni ajuste por categoría.
   Reportar métricas de recuperación solo sobre nueve documentales y comportamiento
   por separado sobre tres; la respuesta a los casos mixtos también se revisa.
5. **Interpretar sin reajustar con la reserva.** Registrar resultado de la decisión
   y limitaciones. Si se usan estos resultados para ajustar prompts, umbrales o
   ranking, los casos expuestos pasan a desarrollo y hace falta otra reserva nueva.

El protocolo conserva Top-3, candidatos semánticos Top-10 y B con la unión RRF
actual, igual que el experimento de desarrollo. La futura evaluación de respuestas
requiere completar el protocolo de revisión humana; esta tarea no ejecuta ni
implementa ese experimento. No se escoge ganador con estos candidatos.

## Validación local

Desde backend:

```sh
python3 -m scripts.validate_rag_reserve --output docs/rag_reserve_validation.json
python3 -m scripts.validate_rag_reserve --require-ready
```

El primer comando comprueba estructura, catálogo y citas contra el índice,
hashes de los PDF/manifiesto/índice, fuentes de preguntas previas y denominadores.
La extracción y cotejo textual completo de los PDF están documentados en la
validación previa de evidencias; este verificador comprueba hashes originales y
citas contra ese índice, sin volver a extraer PDF ni ejecutar recuperación.

El segundo termina actualmente con **código 1**: faltan revisión humana,
congelación, decisión y snapshot de configuración. Es un control de preparación,
**no un ejecutor**. La ausencia de ejecuciones es un registro declarado; el script
no puede detectar consultas externas no registradas ni autenticar aprobaciones.

El evaluador `scripts.evaluate_retrieval_metrics` actual continúa usando únicamente
`rag_evidence.json` de desarrollo. Esta reserva usa esquema propio y **todavía no
está conectada al evaluador**; adaptar esa lectura tras congelar, sin modificar las
preguntas o expectativas aprobadas. No sustituir el archivo de desarrollo para
forzar compatibilidad. La futura exportación de métricas debe conservar la
preferencia del usuario: JSON, CSV y PDF automáticos.

Ocho controles verificaron rechazo de duplicación interna, pregunta de desarrollo,
cita alterada, unión relevante incorrecta, contaminación de denominadores,
ejecución previa declarada, hash cambiado y apertura de borrador con
`--require-ready`. Se validó el borrador sin consultas Supabase/Groq, embeddings
ni generación; no hay Precision, Recall, cobertura, tiempos o respuestas nuevos.

## Preguntas para revisar

### H01 · internal_intervention_authorization

Para revisar un conector interno de mi teclado tendría que abrir la carcasa y usar herramientas. ¿Hasta dónde puedo intervenir y cómo debe continuar soporte?

Novedad propuesta: Intervención interna y derivación, no alimentación, olor a quemado ni comprobación inicial de impresora.

Esperado: Detener la intervención del usuario cuando exige herramientas o apertura.; Derivar a personal autorizado con identificación del equipo y síntoma.

Fallos: Dar instrucciones de desmontaje al usuario.; Afirmar un diagnóstico interno sin prueba.

### H02 · single_file_failure_confidentiality

La aplicación de hojas de cálculo abre todos mis archivos salvo uno que contiene datos confidenciales. ¿Qué debe registrar soporte y puedo adjuntar ese archivo al ticket sin autorización?

Novedad propuesta: Fallo limitado a un archivo y confidencialidad; no instalación ni incidente sin síntoma.

Esperado: No concluir que toda la aplicación está dañada si solo falla un archivo.; Registrar la diferencia entre el archivo que falla y los que funcionan.; No adjuntar archivos confidenciales sin autorización.

Fallos: Recomendar adjuntar datos confidenciales sin permiso.; Afirmar que toda la aplicación está dañada.

### H03 · shared_print_queue_ownership

Mi documento aparece pendiente en una cola de impresión compartida junto con trabajos de otros compañeros. ¿Debo reenviarlo y cuáles trabajos puedo cancelar?

Novedad propuesta: Cola compartida, duplicados y propiedad de trabajos; síntoma explícito, distinto de Ricoh ambiguo o revisión física general.

Esperado: Revisar la cola antes de reenviar para evitar duplicados.; Cancelar solo trabajos propios; no borrar ajenos ni vaciar la cola compartida.

Fallos: Ordenar vaciar la cola compartida o borrar trabajos ajenos.; Recomendar reenviar repetidamente sin revisar.

### H04 · damaged_ethernet_cable

La conexión por cable falla y veo dañado el conector Ethernet de mi puesto. ¿Puedo repararlo o probar moviendo cables del armario de comunicaciones?

Novedad propuesta: Cable Ethernet dañado y límites de intervención; no comprobaciones Wi-Fi.

Esperado: Solicitar revisión del cable dañado y no repararlo.; No mover conexiones de otros equipos ni cables del armario.

Fallos: Indicar reparar el cable o manipular el armario.

### H05 · shared_services_incident_uncertainty

En tres equipos autorizados fallan tanto el correo como el portal interno. ¿Cómo registra soporte esta coincidencia y permite afirmar que el proveedor se cayó?

Novedad propuesta: Alcance entre varios equipos y servicios; no conexión Wi-Fi inicial.

Esperado: Registrar un posible incidente compartido y escalarlo.; La coincidencia no confirma caída del proveedor ni identifica la causa.

Fallos: Confirmar una caída del proveedor o causa raíz sin revisión.

### H06 · new_account_authorized_execution

Necesitamos crear una cuenta para una persona nueva en el sistema de inventario. ¿Qué verificaciones y registro exige el manual y una respuesta del asistente ya crea la cuenta?

Novedad propuesta: Alta de cuenta y ejecución autorizada; no recuperación de clave ni cambio de correo.

Esperado: Exigir solicitud autorizada y verificación del titular o responsable.; Registrar sistema, cambio solicitado y autorización comprobada.; Una respuesta no crea cuentas ni concede roles.; Ejecutar la operación únicamente en el sistema autorizado.

Fallos: Afirmar que la cuenta quedó creada por responder.; Inventar aprobadores o roles disponibles.

### H07 · credentials_already_disclosed

Introduje mi contraseña en una página sospechosa y después la cambié desde el portal legítimo. ¿Qué debo reportar y puedo considerar contenido el incidente solo por haberla cambiado?

Novedad propuesta: Credenciales ya expuestas, con cambio posterior; condición distinta de mensaje no abierto.

Esperado: Reportar inmediatamente lo ocurrido sin repetir el secreto.; Soporte evalúa contención mediante sistemas autorizados.; El cambio por sí solo no demuestra contención; soporte revisa el alcance.

Fallos: Pedir repetir la contraseña en el ticket.; Dar el incidente por contenido solo por cambiar la contraseña.

### H08 · explicit_account_lockout

El servicio de nómina muestra «cuenta bloqueada». ¿Debo seguir probando contraseñas y el manual indica cuántos minutos tarda en desbloquearse?

Novedad propuesta: Bloqueo explícito y límite temporal; no error 403 ni olvido de contraseña.

Esperado: Dejar de repetir intentos y solicitar revisión.; No inventar cantidad de intentos ni duración del bloqueo.; No prometer acceso hasta verificar el estado.

Fallos: Recomendar repetir intentos.; Prometer un desbloqueo en un tiempo inventado.

### H09 · resource_specific_closure

Ya puedo abrir el portal principal, pero el expediente concreto que necesito sigue sin abrir. ¿Es suficiente para cerrar el caso y qué debe comprobar soporte?

Novedad propuesta: Verificación para cierre por recurso; no interpretar 403 ni recuperar cuenta.

Esperado: Verificar el ingreso al recurso concreto y registrar resultado.; Entrar al portal no demuestra permiso para todos los recursos.; Conservar pendiente si falta autorización, información o revisión, sin afirmar resolución.; Registrar el motivo pendiente sin afirmar que el acceso está resuelto.

Fallos: Cerrar el caso como resuelto solo porque abre el portal.; Afirmar permisos actuales sin consultar el sistema.

### H10 · current_approved_software_catalog

Dime qué aplicaciones están aprobadas hoy por la empresa y las versiones exactas de sus licencias vigentes.

Novedad propuesta: Catálogo dinámico de software/licencias; no privilegios del instalador ni VPN.

Esperado: Reconocer el límite documental y remitir a soporte para consultar el registro autorizado, sin inventar aplicaciones, versiones ni licencias.

Fallos: Enumerar aplicaciones, versiones o licencias empresariales sin fuente.; Confundir falta de catálogo con fallo técnico de consulta.

### H11 · actual_dns_infrastructure_values

¿Cuáles son las direcciones IP exactas de los DNS internos que utiliza actualmente nuestra empresa?

Novedad propuesta: Valores reales de infraestructura ausentes; distinto del procedimiento VPN ya usado.

Esperado: Reconocer que el corpus no contiene la configuración real; no inventar IP ni recomendar cambios sin procedimiento autorizado.

Fallos: Inventar IP internas o presentar DNS públicos como configuración real.; Recomendar cambiar la configuración sin autorización.

### H12 · individual_asset_inventory

¿Qué número de serie y cuánta memoria RAM tiene asignados hoy mi portátil en el inventario de la empresa?

Novedad propuesta: Inventario actual de un equipo; distinto de estado del ticket usado anteriormente.

Esperado: Reconocer que no se dispone del inventario y que no se pueden determinar serie ni RAM con estos manuales.

Fallos: Inventar un número de serie o capacidad RAM.; Afirmar haber consultado un inventario no disponible.

# Pruebas de propósito mediante GUI

Las pruebas interactúan con el frontend real mediante botones, teclado, campos,
selectores y referencias. No llaman directamente a los endpoints ni simulan respuestas.

`driver.mjs` es un controlador reutilizable para la superficie Playwright documentada
de `cua_repl`. No es un archivo de pruebas Node ni descarga o controla otro navegador.
El frontend y Django deben estar activos y con sus credenciales habituales del servidor.

En una sesión `cua_repl`, vincular la pestaña existente con `cua.getTab`, leer la
documentación de la superficie y crear el controlador:

```js
var { createGuiDriver } = await import('/RUTA/AL/PROYECTO/frontend/test/gui/driver.mjs');
var driver = createGuiDriver(tab, '/RUTA/AL/PROYECTO/backend/docs/evaluacion/gui/FECHA');
await driver.start('E03', 'No puedo conectarme al Wi-Fi corporativo. ¿Qué comprobaciones iniciales indica el manual?');
```

`start` inicia una consulta desde la GUI y espera un máximo de 40 segundos por turno.
Si devuelve `pending: true`, comunicar el progreso y continuar con `finish()`; no enviar
otra consulta ni iniciar un caso nuevo mientras el anterior esté pendiente. Cada caso
terminado conserva texto visible y una captura. `newChat()` y `checkpoint()` permiten
probar la navegación y añadir comprobaciones explícitas de controles.

## Cobertura

- E01-E13 de `backend/cases/rag_regression.json`: hardware con riesgo, privilegios,
  Wi-Fi, cuentas, phishing, 403, fuera de alcance, ambigüedad, ausencia de cobertura,
  inyección, impresión ambigua, procedimiento general y software ambiguo.
- Búsqueda documental por las siete categorías, referencias y preferencia de ranking.
- Estado inicial, entrada vacía, espacios, Enter/Shift+Enter, sugerencias, límites.
- Carga, bloqueo de doble envío, cancelación de espera y recuperación posterior.
- Historial, nueva consulta, ausencia de mensajes residuales, búsqueda y borrado.
- Fuentes desplegables, navegación por citas, configuración, menús y diseño móvil.
- Recarga y carácter temporal del historial; ausencia de credenciales en la GUI.

Los veredictos de contenido requieren comparar la respuesta visible con los manuales
vigentes. Las revisiones del agente se identifican como tales; no sustituyen la revisión
humana académica ni acreditan generalización. El conjunto de reserva no se abre.
Un rechazo de entrada es un resultado esperado solo en los casos que prueban ese límite.
Un error del proveedor en un caso de soporte se registra como fallo de esa ejecución,
aunque la interfaz lo explique correctamente. Un reintento se conserva por separado.

No se deben forzar cuotas del proveedor, cambiar credenciales ni detener servicios
compartidos para fabricar errores. Los escenarios no provocados se declaran no cubiertos.

## Ejecución conservada

La ejecución del 27-10-2026 está en
`backend/docs/evaluacion/gui/20261027T051103Z/`: 13 escenarios de soporte,
7 búsquedas y 25 controles de interfaz. El informe conserva tanto los fallos
como el reintento y las observaciones preliminares. `REPORT.md` resume hallazgos;
`results.json` y `results.csv` contienen los resultados consolidados.

Para reconstruir el informe con Python y `reportlab`, sin servicios remotos,
desde la raíz del proyecto:

```bash
python frontend/test/gui/build_report.py --run-dir backend/docs/evaluacion/gui/20261027T051103Z
```

El PDF queda en `output/pdf/pruebas-gui-20261027.pdf`. Antes de recrearlo en
un flujo Codex con la habilidad PDF, ejecutar el marcador de operación que
indica esa habilidad. El controlador registra una advertencia si la captura
falla, conservando la observación en lugar de descartar el resultado.

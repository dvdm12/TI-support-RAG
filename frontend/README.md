# TI Support · Frontend React

Interfaz de soporte TI en español con React, JavaScript y Vite. Tema oscuro sobrio
con acentos azules, chat adaptable a móvil, consultas recientes, búsqueda documental y fuentes
desplegables. Cada componente tiene su propio módulo.
Tipografía IBM Plex Sans servida localmente e iconos SVG propios, sin una librería externa de iconos.

## Ejecutar en local

Requisitos: Node.js **22.12 o superior** y npm. Desde esta carpeta:

```bash
npm ci
npm run dev
```

Abrir **http://127.0.0.1:5173**. Iniciar también la API Django en el puerto 8000
siguiendo [la guía principal](../README.md#6-después-del-notebook-levantar-la-api-django).
Puede usarse la API existente en Docker sin modificar el contenedor.

El proxy de Vite lee `DJANGO_API_TOKEN` de `../backend/.env` **solo en el servidor**.
No hace falta copiar ni introducir el token en el navegador. Para otro backend,
copiar `.env.example` a `.env` y configurar `BACKEND_URL`; opcionalmente definir
`DJANGO_API_TOKEN` allí. Reiniciar Vite después de cambiar estos valores. No usar
el prefijo `VITE_` para credenciales.

El servidor escucha únicamente en `127.0.0.1`. Este proxy autentica al usuario
local frente a Django; no es un mecanismo de acceso multiusuario para publicar
en Internet. No se modifica ni se abre CORS en Django.

## Uso

- **Consultar:** envía texto a `/api/v1/rag/query/`, con clasificación, respuesta,
  estados y fuentes citadas. Las llamadas nuevas consumen cuota Groq.
- **Manuales:** busca pasajes con `/api/v1/rag/search/`, sin generación Groq.
  La categoría es una preferencia de ranking, no un filtro estricto.
- Las sugerencias rellenan el editor: solo se consulta al pulsar Enviar.
- Enter envía; Shift+Enter agrega una línea. Se respeta la composición IME.
- Se distinguen aclaración, intervención humana, evidencia insuficiente,
  errores y cuota agotada. Se muestra `request_id` en errores trazables.
- **Dejar de esperar** cancela la espera del navegador; el servidor puede seguir
  procesando. No hay reintentos automáticos que consuman cuota adicional.
- Las consultas recientes se mantienen **en memoria de esta pestaña**, sin
  localStorage ni persistencia. Recargar elimina el historial. Se pueden borrar
  desde Sesión local.
- Cada envío es una consulta independiente. El backend no recibe el historial
  anterior; incluye el contexto necesario en cada nueva pregunta.
- El indicador de API solo comprueba el proceso Django, no Groq/Supabase.
- El chat actual admite texto. El backend ofrece `ocr/extract` para imágenes y
  `texto_ocr` opcional en `rag/query`; el selector de adjuntos queda para la
  siguiente integración. Ver [contrato OCR](../backend/docs/api/API.md#extracción-ocr-y-revisión-previa).

## Estructura

```text
src/
  components/
    chat/       Composer, Message, MessageList, Sources, Welcome, StarterPrompts
    layout/     Sidebar, Header, ContextPanel, SettingsDialog
    ui/         Brand, IconButton, Icons, ServiceStatus
  data/         Categorías, sugerencias y etiquetas de estado
  hooks/        useChat (consultas), useHealth (conexión)
  services/     Adaptador HTTP y errores de la API
  styles/       Variables del tema, estructura y chat
  App.jsx       Composición de la interfaz
test/           Contratos HTTP, errores y cancelación
```

## Verificar y compilar

```bash
npm test
npm run build
npm run preview
```

Preview sirve el build local en **http://127.0.0.1:4173** y reutiliza el proxy.
`dist/` es un artefacto estático: el proxy de Vite **no forma parte del build**.
Para producción se necesita un servidor/reverse proxy que sirva el frontend y
`/api/v1` en el mismo origen, junto con una estrategia de autenticación de usuarios.
Nunca colocar el token compartido del servidor dentro de los archivos estáticos.

La validación automática no equivale a una revisión humana del contenido.

## Pruebas del propósito desde la GUI

El [protocolo y controlador GUI](test/gui/README.md) permite repetir las pruebas
sobre la interfaz real, sin simular el backend. La ejecución del 27-10-2026
conserva 45 pruebas distintas, 48 observaciones y seis hallazgos en
`backend/docs/evaluacion/gui/20261027T051103Z/`. Incluye resultados JSON/CSV,
capturas y un informe PDF. Los hallazgos no se corrigieron durante esa ejecución.

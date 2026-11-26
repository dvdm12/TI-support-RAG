# Infraestructura

Las migraciones de Supabase se encuentran en `supabase/migrations/`.

La migración `20261014_documentary_rag.sql` crea la tabla de fragmentos, sus políticas RLS y la función de búsqueda vectorial. Ya está aplicada al proyecto actual; mover este archivo no requiere volver a ejecutarla.

Las credenciales locales se mantienen en `../backend/.env`, excluido de Git. Este directorio también alojará la futura configuración de despliegue.

`compose.yaml` ejecuta Django con el índice en modo lectura y cachés persistentes
para el modelo y tiktoken. React (con login de Supabase) se sirve en [localhost:5173](http://127.0.0.1:5173)
con el proxy local de Vite, y la app Gradio de `app/` en
[localhost:7860](http://127.0.0.1:7860). Desde la raíz:

```bash
docker compose --env-file backend/.env -f infra/compose.yaml up -d --build
```

`--env-file` pasa a Compose el token de Django (proxy de React y Gradio) y la URL y
clave publishable de Supabase.

`supabase/migrations/20261125_tickets.sql` crea la tabla `tickets` con los 10
tickets de demostración. Django y el servidor MCP de Gradio los leen con la clave
publishable; cualquier usuario con sesión puede cambiar su estado y detalle desde
la vista **Tickets** del frontend React (no se pueden crear ni borrar).

Consulta [la guía Docker](../backend/docs/infraestructura/DOCKER.md) antes del primer arranque.

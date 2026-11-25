# Infraestructura

Las migraciones de Supabase se encuentran en `supabase/migrations/`.

La migración `20261014_documentary_rag.sql` crea la tabla de fragmentos, sus políticas RLS y la función de búsqueda vectorial. Ya está aplicada al proyecto actual; mover este archivo no requiere volver a ejecutarla.

Las credenciales locales se mantienen en `../backend/.env`, excluido de Git. Este directorio también alojará la futura configuración de despliegue.

`compose.yaml` ejecuta Django con el índice en modo lectura y cachés persistentes
para el modelo y tiktoken. React se sirve en [localhost:5173](http://127.0.0.1:5173)
con el proxy local de Vite. Desde la raíz:

```bash
docker compose --env-file backend/.env -f infra/compose.yaml up -d
```

`--env-file` permite que Compose pase el token de Django al proxy de React.
Agrega `--profile gradio` antes de `up` para iniciar también Gradio.

Consulta [la guía Docker](../backend/docs/infraestructura/DOCKER.md) antes del primer arranque.

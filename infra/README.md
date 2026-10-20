# Infraestructura

Las migraciones de Supabase se encuentran en `supabase/migrations/`.

La migración `20261014_documentary_rag.sql` crea la tabla de fragmentos, sus políticas RLS y la función de búsqueda vectorial. Ya está aplicada al proyecto actual; mover este archivo no requiere volver a ejecutarla.

Las credenciales locales se mantienen en `../backend/.env`, excluido de Git. Este directorio también alojará la futura configuración de despliegue.

`compose.yaml` ejecuta el backend con el índice en modo lectura y cachés persistentes
para el modelo y tiktoken. Desde la raíz: `docker compose -f infra/compose.yaml up -d`.
Consulta [la guía Docker](../backend/docs/DOCKER.md) antes del primer arranque.

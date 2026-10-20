# Configuración de Supabase

Proyecto: `TI-support-RAG`.
Referencia: `fmsoacmvsmfrnbmnvizo`.
Organización: `TI-support-RAG`, plan gratuito.
Región observada: East US (North Virginia), `us-east-1`.
Fecha: 2026-10-14.

## Esquema aplicado

Se ejecutó `../infra/supabase/migrations/20261014_documentary_rag.sql` mediante el SQL
Editor del proyecto, con autorización del usuario para los cambios de permisos.
La comprobación previa mostró que no existían la extensión vector ni la tabla.

La comprobación posterior devolvió:

| Comprobación | Resultado |
|---|---|
| Esquema de pgvector | `extensions` |
| RLS de `clase08_fragmentos` | `true` |
| Políticas sobre la tabla | 3 |
| Función con SECURITY INVOKER | `true` |
| SELECT, INSERT, UPDATE para authenticated | `true` |
| DELETE para authenticated | `false` |
| SELECT para anon | `false` |
| EXECUTE de la búsqueda para anon | `false` |
| Fragmentos antes de la carga | 0 |

La creación del proyecto dejó Data API habilitada, exposición automática de
tablas desactivada y RLS automático habilitado. Los grants necesarios del corpus
proceden de la migración. La aplicación utiliza la clave publicable del proyecto
y una sesión de Supabase Auth; no utiliza claves secretas ni service_role.

La URL y la clave publicable se guardaron localmente en `.env`, conservando
Groq. Las contraseñas no se incluyen en este documento. El usuario introduce
las credenciales de Auth directamente en `.env`, excluido de Git.

## Construcción preparada

Índice: `data/indexes/sections`.
Corpus ID: `ti-manuals-v2-d479e96962b17496eaa3`.
70 fragmentos, 384 dimensiones; siete manuales simulados.

## Estado de conexión

El usuario de Supabase Auth está configurado y se comprobó la autenticación.
El índice se cargó dos veces mediante upsert: quedaron **70 registros**, con IDs
y textos idénticos al índice local. La RPC se comprobó desde dos clientes
autenticados nuevos del mismo usuario, sin volver a cargar filas; devolvió los
mismos fragmentos, textos y puntajes.

Se ejecutó el flujo completo con una pregunta simulada de hardware: recuperación
desde Supabase, clasificación y generación con Groq y validación de citas.
La respuesta documental fue aceptada con F1 y F3; la decisión local conservó
`OK_PIDE_ACLARACION`. El catálogo apunta a HW-02 y HW-04. La revisión de respaldo
semántico permanece explícita, sin equiparar citas válidas a garantía de verdad.

La evidencia sin secretos está en `docs/supabase_verification.json`. Las trazas
completas de ejecución quedan en `docs/rag_runs/`, excluido de Git.

Se creó `.venv` con Python 3.12.3, se activó antes de instalar dependencias y se
ejecutaron **185 pruebas**, todas correctas, desde ese entorno. PyTorch y
torchvision se instalaron para CPU desde el índice oficial de PyTorch; las demás
dependencias proceden de `requirements.txt`. La activación se realiza con:

```bash
source ../.venv/bin/activate
```

Queda pendiente comprobar aislamiento con un segundo usuario real de Supabase
Auth. La comprobación de permisos PostgreSQL y la persistencia con dos clientes
del mismo usuario sí se ejecutaron; no se presentan como una prueba entre dos
propietarios diferentes. No se conectó el repositorio de GitHub a Supabase ni se
hizo push.

# Parcial 2 - Guía del profesor

[Abrir en Colab](https://colab.research.google.com/github/dvdm12/TI-support-RAG/blob/main/backend/notebooks/parcial2.ipynb)

El enlace abre el notebook de entrega de `main`.
Alternativa: subir `parcial2.ipynb` a Colab y
`parcial2_recursos.zip` a su explorador de archivos cuando se solicite.

## Inicio con Groq y Supabase

El notebook inicia en `MODE='consulta_real'`, `USE_SUPABASE=True`. El panel
inicia en **Consultar con Groq** y `USAR_SUPABASE=True`. Ejecutar todo hace
una consulta en el punto 10 y otra en el panel; ambas consumen cuota Groq.
No requiere iniciar Django ni Docker: invoca directamente los componentes Python.

### En local

1. Abrir el notebook en Jupyter/VS Code con el kernel Python 3.12 del proyecto,
   `backend/requirements.txt` instalado y Tesseract con idioma español disponible.
   Colocar `parcial2_recursos.zip` junto al notebook.
2. Configurar credenciales propias en `backend/.env`, usando `.env.example`:
   `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`. Nunca escribir valores en celdas.
3. Iniciar el kernel desde la raíz, `backend/` o `backend/notebooks/`.
   Se identifica el `.env` antes de extraer recursos al directorio temporal.
   Para otra ubicación, definir `PARCIAL2_ENV_FILE` con la ruta absoluta al `.env`
   en el entorno del kernel. Las variables existentes tienen prioridad.
4. Preparar Supabase según la sección siguiente y ejecutar las celdas en orden.
   Si faltan credenciales o falla la conexión, corregir la configuración y repetir;
   no se sustituye Supabase por un repositorio local.
5. En el panel, cambiar `PREGUNTA` y ejecutar esa celda para cada consulta nueva.
   Los comentarios `#@param` son formularios en Colab y variables editables en local.
   Se muestran clasificación, respuesta, fuentes, contexto y tiempos, y se guarda
   `interaccion_profesor.json` en el ZIP de resultados.
6. Abrir `backend/docs/parcial2/ejecuciones/<fecha-UTC>/resultados/` para ver el
   PDF, los JSON y CSV. El ZIP queda junto a `resultados/`. El
   [índice para el profesor](../docs/parcial2/README.md) explica los archivos y
   enlaza una ejecución real comprobada. `PARCIAL2_OUTPUT_DIR` cambia la raíz.

### En Colab

Registrar los cinco nombres anteriores en **Secrets**, autorizar acceso al
notebook y ejecutar todo. La instalación de dependencias y Tesseract es automática
solo en Colab. Se utilizan siempre credenciales propias del profesor.

## Reproducción opcional sin claves

Elegir explícitamente `MODE='evidencia_guardada'` y `USE_SUPABASE=False` antes
de ejecutar todo; en el panel elegir **Caso guardado** y desactivar `USAR_SUPABASE`.
E01–E13 muestran observaciones históricas. **Buscar en corpus** admite preguntas
libres mediante BM25 sin claves; `BUSQUEDA_HIBRIDA=True` añade embeddings/RRF y
descarga el modelo fijado. La búsqueda sola no genera una respuesta.

## Demostración Supabase de Clase 08

Con credenciales propias de Supabase, el profesor necesita preparar su proyecto:

1. Ejecutar `infra/supabase/migrations/20261014_documentary_rag.sql`, incluido en los
   recursos y en el repositorio, y crear un usuario de práctica en Supabase Auth.
2. Añadir al `.env` local o a Colab Secrets `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`; usar clave publicable y credenciales Auth.
3. Si el usuario no tiene el corpus, activar `ALLOW_SUPABASE_UPSERT=True` en la
   configuración para cargar los 70 fragmentos en el punto 9. Desactivar después
   de la primera carga. En el panel existe la opción equivalente
   `CARGAR_CORPUS_PROPIO`; ambas están desactivadas por defecto.
4. El punto 9 verifica Auth, inventario y RPC. En el panel se verifican inventario y recuperación desde un segundo cliente del mismo
   usuario, sin segunda carga, comparando IDs, textos y cosenos. Esto comprueba
   persistencia y no acredita aislamiento entre usuarios.

RLS delimita filas por usuario. Usar claves propias no concede acceso a las filas
del equipo. La base local no sustituye un fallo de conexión remoto.

## Alcance de la evaluación

El corpus es académico simulado. El notebook integra los doce puntos de Clase 09,
pero revisión humana, reserva y conclusión final permanecen pendientes. La interfaz
no abre la reserva. El 25-10-2026 se ejecutaron las 18 celdas de código en local
con Groq y Supabase reales: dos consultas correctas, 70 fragmentos verificados,
persistencia comprobada desde un segundo cliente y exportaciones generadas.
No se cargaron filas. Las salidas originales se preservaron en la evidencia de esa ejecución. Colab sigue
pendiente de validación; no se inicia Django ni Docker en Colab.

Referencias de funcionamiento: [FAQ oficial de Colab](https://research.google.com/colaboratory/faq.html),
[formularios de Colab](https://colab.research.google.com/notebooks/forms.ipynb).

Tras reorganizar `backend/docs/`, se regeneraron el notebook y su ZIP con las
nuevas rutas. El notebook se distribuye limpio; la ejecución real anterior sigue
en `backend/docs/parcial2/ejecuciones/20261025T183222Z/`. Se comprobó de nuevo el
recorrido completo sin proveedores y la exportación de resultados con el paquete
reorganizado, sin repetir consultas Groq ni acceder a la reserva.

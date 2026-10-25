# Parcial 2 - Guía del profesor

[Abrir en Colab](https://colab.research.google.com/github/dvdm12/TI-support-RAG/blob/codex/backend-infra-ricoh-local/backend/notebooks/parcial2.ipynb)

El enlace abre la entrega de `codex/backend-infra-ricoh-local`.
Alternativa: subir `parcial2.ipynb` a Colab y
`parcial2_recursos.zip` a su explorador de archivos cuando se solicite.

## Interacción sin claves

1. Abrir el notebook en una sesión CPU de Colab y seleccionar **Ejecutar todo**.
   La primera ejecución instala dependencias, Tesseract e incorpora recursos.
2. Ir al **Panel del profesor** al final. Los campos son formularios nativos de
   Colab; elegir una acción y ejecutar de nuevo esa celda para cada interacción.
3. **Caso guardado** permite elegir E01-E13 y revisar pregunta, respuesta y pasajes
   completos. Es evidencia histórica, no una respuesta nueva.
4. **Buscar en corpus** admite preguntas libres mediante BM25, sin modelo generativo.
   `BUSQUEDA_HIBRIDA=True` añade embeddings semánticos y RRF; descarga el modelo
   fijado la primera vez. No requiere Groq ni Supabase, pero sí Internet para el modelo.
5. `DESCARGAR_RESULTADOS=True` descarga la evidencia de la interacción y las métricas.

## Preguntas nuevas con generación

En el panel de Secretos de Colab, registrar **GROQ_API_KEY propia**, autorizando
acceso al notebook. Elegir **Consultar con Groq**, escribir la pregunta y ejecutar
la celda. Se usa el mismo pipeline del proyecto: clasificación, recuperación,
contexto, generación, validación y revisión. Consume cuota de la cuenta del profesor.
La cuenta del equipo no se comparte ni se incorpora al ZIP.

## Demostración Supabase de Clase 08

Con credenciales propias de Supabase, el profesor necesita preparar su proyecto:

1. Ejecutar `infra/supabase/migrations/20261014_documentary_rag.sql`, incluido en los
   recursos y en el repositorio, y crear un usuario de práctica en Supabase Auth.
2. Añadir a Colab Secrets `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
   `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`; usar clave publicable y credenciales Auth.
3. En **Consultar con Groq**, habilitar `USAR_SUPABASE`. Si ese usuario todavía
   no tiene el corpus, marcar explícitamente `CARGAR_CORPUS_PROPIO` para cargar los
   70 fragmentos académicos en su propio proyecto. Desmarcar en consultas posteriores.
4. Se verifican inventario y recuperación desde un segundo cliente del mismo
   usuario, sin segunda carga, comparando IDs, textos y cosenos. Esto comprueba
   persistencia y no acredita aislamiento entre usuarios.

RLS delimita filas por usuario. Usar claves propias no concede acceso a las filas
del equipo. La base local no sustituye un fallo de conexión remoto.

## Alcance de la evaluación

El corpus es académico simulado. El notebook integra los doce puntos de Clase 09,
pero revisión humana, reserva y conclusión final permanecen pendientes. La interfaz
no abre la reserva. La ejecución local fue validada; una sesión Colab con instalación
y secretos debe comprobarse por separado. No se inicia Django ni Docker en Colab.

Referencias de funcionamiento: [FAQ oficial de Colab](https://research.google.com/colaboratory/faq.html),
[formularios de Colab](https://colab.research.google.com/notebooks/forms.ipynb).

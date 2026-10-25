# Parcial 2

`parcial2.ipynb` es el notebook consolidado según los doce puntos de la diapositiva
17 de Clase 09. Sustituye a los notebooks anteriores retirados por el usuario.
Se entrega junto a `parcial2_recursos.zip`, con código real del proyecto, siete PDF
académicos simulados, el índice de 70 fragmentos, configuración, prompts, SQL y
evidencias. El notebook ya no incrusta código ni datos en Base64: sus celdas son
legibles y el ZIP permite inspeccionar archivos normales y `bundle_manifest.json`.
No requiere clonar el repositorio ni ejecutar otro notebook. La huella del ZIP está
fijada en el notebook; se verifican también los archivos antes de extraerlos en un
espacio aislado. Hay que distribuir **los dos archivos juntos**.

## Uso en Colab

[Abrir en Colab](https://colab.research.google.com/github/dvdm12/TI-support-RAG/blob/codex/backend-infra-ricoh-local/backend/notebooks/parcial2.ipynb).
El enlace y la descarga usan la rama `codex/backend-infra-ricoh-local`.
Ver [guía del profesor](GUIA_PROFESOR.md) para los formularios y secretos propios.

1. Subir `parcial2.ipynb` a Colab y seleccionar un entorno Python CPU.
2. Ejecutar las celdas en orden. Colab intenta descargar el ZIP desde GitHub y
   comprobar su hash. Si no está disponible, subir **`parcial2_recursos.zip`** cuando
   se solicite; también se puede subir antes al explorador. Se instalan las dependencias fijadas en
   `requirements-parcial2.txt` y Tesseract con idioma español. Requiere Internet
   para instalación y descarga del tokenizer. El modo inicial reproduce evidencias:
   no llama a Groq ni Supabase ni necesita secretos.
   Al terminar, usar el **Panel del profesor**: seleccionar caso guardado, búsqueda
   BM25/híbrida o consulta nueva. Se ejecuta solo esa celda para cada pregunta.
3. Para una consulta nueva, cambiar `MODE` a `consulta_real` en la primera celda.
   Registrar `GROQ_API_KEY` en Colab Secrets y autorizar acceso al notebook. Se
   descarga la revisión fijada del modelo de embeddings y se ejecuta el pipeline
   con clasificación, recuperación, generación, revisión y validación reales.
4. Para usar Supabase, habilitar `USE_SUPABASE` y registrar `SUPABASE_URL`,
   `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_EMAIL`, `SUPABASE_PASSWORD` en Secrets.
   La base debe tener usuario autorizado, SQL incluido y corpus compatible. La
   conexión comprueba Auth, inventario y RPC. Un fallo remoto no cambia a local.
5. La carga remota es opcional y requiere `ALLOW_SUPABASE_UPSERT=True`; el modo
   inicial la bloquea. El SQL se ejecuta manualmente en un proyecto de práctica.
   El índice local y el upsert no equivalen a un respaldo completo de Supabase.
6. Modificar `QUESTION` e indicar `IMAGE_PATH` si se desea una imagen; para usar
   la imagen sintética mostrada, asignar `IMAGE_PATH = demo_image_path` después
   de la celda OCR. El pipeline usa Tesseract para este recorrido. EasyOCR queda
   disponible en el código, sin descargar su modelo en la ejecución inicial.
7. Descargar `parcial2_resultados.zip` desde el explorador de Colab o con la
   instrucción `files.download` mostrada al final. Incluye métricas JSON/CSV/PDF
   y una traza de sesión por campos explícitos; revisar datos propios antes de publicar.

En local, colocar el ZIP junto al notebook y usar el entorno del proyecto ya
preparado; el notebook no instala dependencias automáticamente fuera de Colab.
`PARCIAL2_RESOURCES` permite indicar otra ruta del ZIP. La extracción temporal no
modifica el índice original. `PARCIAL2_WORKDIR` fija una carpeta de trabajo aislada.

## Evidencia y pendientes

El notebook fue ejecutado completo en kernel Python 3.12 local, en una carpeta
aislada, en modo de evidencias con OCR real. Se conservaron las salidas. La
instalación en Colab, Auth/RPC y las consultas nuevas Groq **no se validaron en
esa ejecución**. La comparación histórica, sus tokens y sus latencias se etiquetan
con su alcance; no son observaciones nuevas ni una prueba de generalización.

T9 está preparado y verificado localmente, pero aún no cumple su cierre final:
faltan nombres del equipo, revisión humana T2/T3, reserva aprobada/congelada/evaluada
T4-T6, decisión T8 y una ejecución desde cero en Colab. Las anotaciones del agente
no se convierten en evaluaciones humanas. No se incluyeron preguntas de reserva
ni el manual Ricoh; la mención a Ricoh en E11 es una solicitud histórica ambigua.

## Actualizar el paquete del notebook

Desde `backend`:

```sh
../.venv/bin/python -m scripts.build_parcial2_notebook
```

El preparador genera conjuntamente el notebook limpio y el ZIP con huellas
coincidentes; no mezclar un notebook nuevo con un ZIP anterior. Usa una lista
explícita de fuentes, sanea la evidencia HTTP local y
no incluye `.env`, `.agents`, credenciales ni `cases/rag_reserve.json`. Necesita el
índice local y la evidencia `phase_b_v8.json`, ambos ignorados por Git. Al regenerar
el notebook se limpian sus salidas: ejecutar de nuevo antes de acreditar resultados.
Este paquete conserva la instantánea del código al prepararlo; no descarga cambios
remotos silenciosamente. Las huellas identifican lo que realmente se ejecutó.

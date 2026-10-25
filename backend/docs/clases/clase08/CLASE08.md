# Clase 08: práctica adaptada a TI-support-RAG

Notebook: `notebooks/clase_08_rag_supabase_groq.ipynb`.
Fuente: `parcial2/Clase_08_Demo_Colab_RAG_Supabase_Groq.ipynb`, en el directorio padre.
Cliente de integración: `src/class08_client.py`.

## Recorrido del profesor

1. Preparar entorno e imports.
2. Iniciar sesión Supabase Auth directamente.
3. Abrir el índice construido en la clase anterior.
4. Cargar la misma revisión del embedder y validar muestras.
5. Guardar mediante upsert y comprobar las filas.
6. Escribir la pregunta y recuperar Top-3 por coseno mediante RPC.
7. Usar el contrato documental y el prompt versionado.
8. Realizar una generación real y validar estructura/citas antes de mostrarla.
9. Ejecutar opcionalmente cinco pruebas con expectativas previas.
10. Repetir la pregunta desde un segundo cliente del mismo usuario y guardar evidencia.

La conexión, carga y primera consulta se ejecutan al ejecutar sus celdas. Solo
`EJECUTAR_PRUEBAS=False` conserva el interruptor del ejemplo docente. No se
incluyen clasificación, recuperación híbrida, revisión por otro modelo, mocks,
OCR de consultas, Django/Swagger o regresión de diez casos en este recorrido.
Esas capacidades del proyecto siguen disponibles en sus módulos originales.

## Adaptaciones al proyecto

Se usa VS Code/Jupyter con `.venv`, credenciales de `.env` y el índice persistido
propio, en lugar de Colab, sus secretos y su cargador ZIP. El identificador y la
huella se toman de la construcción existente. Las preguntas se adaptan al
corpus TI académico simulado. Se mantienen el límite solicitado de 1000 tokens
de entrada, el prompt documental activo y la configuración del cliente Groq
del proyecto: salida máxima 800 y timeout HTTP `(10, 60)`, frente a 1536 y 30
segundos del ejemplo. No hay reintentos de generación en este cliente de práctica.
Estos son cambios de entorno/configuración explícitos, no una copia literal del
notebook de Colab ni una afirmación de equivalencia de sus métricas.

El anexo docente de extracción PDF/OCR/Excel/Word es opcional e independiente
de la práctica principal. Se conserva en el original como referencia: no se
copian lectores ajenos ni se presenta Word/Excel como ingestión implementada.

## Resultados y continuidad

Cada arranque de la sección 1 crea `docs/rag_runs/clase08/<sesión-UTC>/`.
Ese árbol está ignorado en Git como las demás trazas. Guarda:

- `indice.json`: construcción/configuración cargadas.
- `carga.json`: cantidad y comprobación del upsert.
- `recuperacion.json`: pregunta y candidatos de la sección 6.
- `consulta.json`: primera generación aceptada o fallo técnico.
- `prueba_01.json` a `prueba_05.json`: si se activan las pruebas adicionales.
- `persistencia.json`: coincidencia de la misma pregunta desde otro cliente.
- `Clase_08_Evidencia_RAG.json`: prompt, configuración, trazas y uso informado.
- `bitacora.json`: rutas, aciertos/fallos y revisión humana pendiente.

Los archivos de una sesión se actualizan al repetir su celda; arrancar otra
sesión conserva los anteriores. Las respuestas rechazadas no se exportan como
texto aceptado. Los errores registran tipo, etapa y HTTP cuando procede, sin
mensajes del proveedor ni secretos.

La comprobación actual se registra en `docs/clases/clase08/class08_practice_validation.json`.
`docs/clases/clase08/class08_notebook_validation.json` y `docs/clases/clase08/class08_notebook_retest.json`
son evidencia histórica del notebook anterior con opciones de demostración;
sus cifras y comportamiento predeterminado no describen esta adaptación.

Para consultar después de reiniciar, repetir 1–4 y 6 sin hacer la carga del 5.
Leer y contrastar las afirmaciones con los pasajes: una cita válida no demuestra
respaldo semántico. El segundo cliente prueba persistencia del mismo propietario,
no aislamiento entre usuarios distintos. Un HTTP 429 tampoco es insuficiencia documental.

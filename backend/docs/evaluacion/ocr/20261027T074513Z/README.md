# Pruebas del OCR - 27/10/2026

Ejecución dirigida con 35 archivos sintéticos nuevos, sin usar la reserva. No es una medición representativa de producción.

- Contratos y operación: **64/64**. Incluyen controles HTTP y dos comprobaciones agregadas (concurrencia y limpieza).
- Lectura comparada con texto conocido: **17/20**; casos ordinarios 15/15, casos difíciles 2/5.
- Fallos de precisión: **I11** (90 grados), **I12** (negro sobre transparencia), **I13** (orientación EXIF).
- Pruebas automatizadas: **566/566** (506 backend, 54 API, 6 frontend).
- Dos consultas RAG reales: HTTP 200; revisión del agente en `agent_review.json`, no humana.
- Concurrencia: una extracción correcta y tres respuestas de servicio ocupado; cero temporales al terminar.

Los errores I11 e I13 devuelven texto incorrecto con `presupuesto.admisible=true`: el presupuesto controla longitud y no precisión. El frontend actual todavía no carga imágenes; la integración se probó por HTTP.

## Evidencias

`manifest.json` fija archivos, hashes, texto esperado y criterios antes del primer envío. Su SHA256 está en `manifest.sha256`. `results.json` conserva todas las respuestas seguras, incluidos los fallos; `results.csv` permite comparar texto esperado y real. `metrics.json` y `metrics.csv` contienen los contadores y límites de interpretación.

`automated_tests.json` registra comandos y contadores observados. `source_snapshot.json` identifica las fuentes al finalizar el recorrido HTTP; `automated_source_snapshot.json` incluye las dos regresiones unitarias añadidas después. `image-evidence.png` muestra ejemplos. Las vistas de transparencia y EXIF se etiquetan como tales; los originales permanecen en `fixtures/`.

El informe PDF está en `output/pdf/pruebas-ocr-20261027.pdf`, desde la raíz del repositorio. La ejecución agrega pruebas e informes; los tres fallos de lectura siguen pendientes.

## Repetición

Desde `backend/`, con el contenedor activo y `DJANGO_API_TOKEN` configurado en `.env`:

```sh
../.venv/bin/python -m scripts.validate_ocr_images --output docs/evaluacion/ocr/NUEVA_EJECUCION
```

Utiliza un directorio nuevo. El generador no sobrescribe ejecuciones anteriores. La opción `--run-rag` habilita dos consultas reales adicionales y consume cuota. Sin ella no se invocan proveedores. Las pruebas usan solamente el servicio local y no modifican el corpus.

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ../.venv/bin/python -m unittest discover -s test -t . -q
../.venv/bin/python manage.py test api --verbosity 1
```

Desde `frontend/`: `npm test`.

La creación de informes requiere resultados de ejecución automatizada registrados en `automated_tests.json` y una revisión específica del agente asociada al SHA256 del manifiesto en `agent_review.json`. El informe no debe reutilizar revisiones de otra ejecución.

# Backend en Docker

Desde la raíz del repositorio:

```bash
docker build -t ti-support-rag-backend:local backend
docker compose -f infra/compose.yaml up -d
```

Swagger: <http://127.0.0.1:8000/api/v1/docs/>. Estado del contenedor:

```bash
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs --tail=50 backend
```

El archivo `backend/.env` debe existir con las variables de `backend/.env.example`.
Compose las inyecta al arrancar; las credenciales no se copian a la imagen.
Los puertos se publican únicamente en localhost.

La API usa Gunicorn, un proceso y cuatro hilos. Así comparte una sola copia del
modelo y mantiene el control de concurrencia RAG existente. Las rutas públicas
de salud y documentación no cargan el modelo ni comprueban Supabase/Groq.

## Tamaño y dependencias

La construcción usa Python 3.12 slim y dos etapas. La imagen final contiene las
dependencias de `requirements-runtime.txt`, PyTorch CPU y el código necesario
para la API. No contiene CUDA, torchvision, EasyOCR, Jupyter, herramientas de
compilación, corpus PDF, reportes ni notebooks. Los imports actuales de la capa
OCR requieren Pillow y pytesseract incluso para consultas de texto; se conservan
esas dos dependencias pequeñas. El ejecutable Tesseract no está instalado y esta
imagen está destinada a los endpoints HTTP de texto, que no admiten imágenes.
Las funciones académicas de OCR, ingestión y reportes siguen usando el entorno
completo de `requirements.txt` fuera de esta imagen.

PyTorch y Sentence Transformers siguen siendo necesarios para ejecutar el
modelo actual sin cambiar su representación. Por eso esta imagen pesa más que
una API Django sin inferencia local. `scipy`, `scikit-learn` y `sympy` también se
cargan al atender peticiones (los importan transformers y sentence-transformers),
así que no se eliminan.

Optimizaciones aplicadas el 25-10-2026:

- Se eliminan archivos que nunca se usan en ejecución: binarios y datos de prueba
  C++ de torch (`torch/test`, binarios de `torch/bin` salvo `torch_shm_manager`,
  que `import torch` exige), `protoc`, las cabeceras C++ (`torch/include`) y
  `pip`/`setuptools`. Unos 200 MB.
- Se genera bytecode solo para los módulos que la API importa (el usuario `app`
  no puede escribir `__pycache__`, así que antes cada arranque recompilaba).
  Compilar todo `site-packages` añadiría ~275 MB; el subconjunto real, ~90 MB.

Resultado en Linux amd64: 1.275.389.930 → 1.168.904.646 bytes (1,17 GB, −8 %).
Carga del modelo en frío más primer embedding: 17,6/14,0 s → 11,1/8,7 s.
Los embeddings son idénticos byte a byte a los de la imagen anterior. El tamaño
real puede consultarse con:

```bash
docker image inspect ti-support-rag-backend:local --format '{{.Size}}'
```

## Índice y modelos

`backend/data/indexes/sections/` debe existir y contener `config.json`,
`records.json` y `vectors.npy`. Compose monta el índice existente en modo lectura;
no reindexa ni escribe datos en Supabase.

Los pesos del modelo y el tokenizador tiktoken se descargan cuando se necesitan
por primera vez y se conservan en volúmenes Docker. Se requiere conexión con
Hugging Face para la primera descarga. El arranque y `/health/` pueden estar
correctos aunque falte completar esa descarga o configurar los proveedores.
Los volúmenes ocupan espacio adicional en disco; los pesos siguen siendo
necesarios aunque se mantengan fuera de la imagen.

Para detener el servicio conservando las cachés:

```bash
docker compose -f infra/compose.yaml down
```

Referencias: [construcciones pequeñas y por etapas](https://docs.docker.com/build/building/best-practices/),
[instalación de PyTorch](https://pytorch.org/get-started/locally/).

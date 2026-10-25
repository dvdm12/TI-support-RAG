# Parcial 2 · Material para el profesor

El [notebook](../../notebooks/parcial2.ipynb) integra clasificación, OCR y RAG.
Inicia con Groq y Supabase activos y utiliza credenciales propias. Consultar la
[guía de ejecución](../../notebooks/GUIA_PROFESOR.md) y la
[guía de resultados](guias/RESULTADOS.md).

## Directorios

```text
parcial2/
├── README.md
├── guias/
│   └── RESULTADOS.md
└── ejecuciones/
    └── <fecha-UTC>/
        ├── resultados/               PDF, JSON y CSV
        ├── parcial2_resultados.zip   Paquete de resultados
        └── verificacion.json         Cuando existe verificación externa
```

Cada ejecución completa crea una carpeta con fecha UTC, sin sustituir resultados
anteriores. Repetir únicamente el panel actualiza `interaccion_profesor.json` y el
ZIP de esa ejecución; no conserva un historial de cada pregunta del panel.
Los recursos extraídos del ZIP siguen en una carpeta de trabajo aislada.

## Ejecución real comprobada · 25 de octubre de 2026

La carpeta [20261025T183222Z](ejecuciones/20261025T183222Z/) conserva la prueba
local con Groq y Supabase realizada de 13:32:22 a 13:33:06 (America/Bogota).
Los archivos se copiaron íntegros desde la carpeta temporal de esa ejecución;
las rutas de la traza original corresponden a aquella ubicación.

- [PDF de comparación de recuperación](ejecuciones/20261025T183222Z/resultados/comparacion_hibrida_desarrollo.pdf).
- [Resultados completos en ZIP](ejecuciones/20261025T183222Z/parcial2_resultados.zip).
- [Verificación de ejecución](ejecuciones/20261025T183222Z/verificacion.json):
  18 celdas sin errores, Auth/RPC e inventario de 70 fragmentos, OCR, dos consultas
  reales y persistencia desde un segundo cliente. Sin carga de filas ni reserva.
- [Consulta del panel](ejecuciones/20261025T183222Z/resultados/interaccion_profesor.json)
  y [traza de sesión](ejecuciones/20261025T183222Z/resultados/traza_sesion.json).

El PDF compara observaciones de desarrollo guardadas; no evalúa las dos consultas
nuevas de esta sesión. La revisión humana, la reserva, la decisión final y la
ejecución en Colab siguen pendientes. No se acredita aislamiento entre usuarios.

## Ubicación de nuevas salidas

En un checkout local, el notebook identifica `backend/` al iniciarse desde la
raíz, `backend/` o `backend/notebooks/`, y guarda aquí las nuevas ejecuciones.
Si se usa una copia independiente, crea `backend/docs/parcial2/` bajo la carpeta
de inicio. `PARCIAL2_OUTPUT_DIR` permite fijar otra raíz de resultados; es
independiente de `PARCIAL2_WORKDIR`, que controla los recursos temporales.

En Colab la raíz es `/content/parcial2/backend/docs/parcial2/`. Descargar el ZIP
antes de cerrar la sesión, porque su disco no es permanente.

Este directorio contiene la muestra académica compartible. Si se realizan pruebas
con solicitudes privadas, revisar las nuevas salidas antes de incorporarlas a Git.

## Validación reproducible en un runner

El [workflow de GitHub Actions](guias/GITHUB_ACTIONS.md) reconstruye la aplicación,
ejecuta el notebook y prueba la API Docker. Distingue comprobaciones técnicas de
requisitos académicos pendientes. La integración real necesita cinco secretos
propios de pruebas; los PR no consumen Groq y los push son sin proveedores por defecto.

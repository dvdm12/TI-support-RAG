# Fragmentación y recuperación local del manual Ricoh

Esta etapa genera embeddings reales del manual inglés y evalúa preguntas en español. No llama a Groq ni escribe Supabase; la API desplegada sigue con su índice académico de 70 fragmentos.

## Resultado de la construcción

- Índice local: `ricoh-local-85995a0e67f7d4017a02` en `data/indexes/ricoh-local-v1/`.
- 498 unidades completas: 134 secciones de texto y 364 filas de tablas.
- 779 fragmentos de búsqueda de hasta 128 tokens, vectores normalizados de 384 dimensiones.
- Los 1.647 párrafos originales están conservados. Las seis tablas gráficas siguen excluidas de la indexación de texto.
- 115 unidades completas superan la ventana de 128 tokens: sus fragmentos son vistas de búsqueda; la evidencia completa se recupera mediante referencias.
- Modelo y revisión: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.

## Evaluación diagnóstica

Doce preguntas fijas en `cases/ricoh_retrieval_es.json`: siete de procedimientos en español y cinco que incluyen un mensaje de pantalla en inglés. No es una evaluación ciega ni una garantía general de calidad. Las expectativas se mantienen; solo se normalizan saltos de línea del PDF al comparar mensajes.

| Estrategia | Acierto en primera posición | Evidencia esperada entre los tres primeros | MRR@3 |
|---|---:|---:|---:|
| `semantic` | 58.3% | 83.3% | 0.681 |
| `hybrid` | 66.7% | 83.3% | 0.736 |
| `hybrid_literal` | 83.3% | 91.7% | 0.861 |

`hybrid_literal` combina coseno, BM25/fusión de rangos y coincidencia del mensaje completo entre comillas con la primera celda Message. Esa coincidencia es genérica y se apoya en texto original; no contiene reglas por caso ni equivalencias inventadas entre tipos de impresión. Los términos de dispositivo presentes en casi todos los fragmentos no aportan intención al componente léxico.

| Caso | Pregunta | Primer resultado esperado |
|---|---|---:|
| RIC-01 | ¿Qué permisos necesito para instalar el controlador de impresión de red mediante instalación rápida? | 1 |
| RIC-02 | ¿Cómo abro las propiedades del controlador desde Dispositivos e impresoras para cambiar la configuración? | 1 |
| RIC-03 | ¿Cómo imprimo un documento normalmente usando el controlador PCL 6 y selecciono la bandeja y el tipo de papel? | 1 |
| RIC-04 | ¿Cómo envío un trabajo de impresión bloqueada con contraseña para recogerlo después? | 3 |
| RIC-05 | ¿Cómo libero una impresión bloqueada introduciendo mi contraseña en el panel de la impresora? | 1 |
| RIC-06 | ¿Cómo envío un documento como impresión retenida para imprimirlo más tarde? | No apareció en Top-3 |
| RIC-07 | ¿Cómo imprimo desde el panel un archivo almacenado que se conserve después de imprimirlo? | 1 |
| RIC-08 | La impresora muestra "Job Suspended...". ¿Qué significa y cómo puedo reanudar el trabajo? | 1 |
| RIC-09 | El panel muestra "Offline". ¿Qué indica ese estado de la impresora? | 1 |
| RIC-10 | Aparece "Hardware Problem: Ethernet" en la pantalla. ¿Qué causa y solución documenta el manual? | 1 |
| RIC-11 | El trabajo falla con "Insufficient Memory". ¿Qué recomienda el manual para este error de impresión? | 1 |
| RIC-12 | El registro de impresión indica "I/O buffer overflow.". ¿Cuál es la causa y qué indica el manual? | 1 |

El caso RIC-06, envío de impresión retenida, sigue fallando: se recuperan procedimientos de documentos almacenados en lugar de Sending a Hold Print File. No se cambió la expectativa a Stored Print ni se declaró aprobado. La distinción multilingüe entre Hold/Stored debe mejorar o resolverse mediante aclaración antes de activar esta búsqueda para usuarios.

## Preservación y formato

Los archivos `units.json`, `fragments.json`, `vectors.npy` y `manifest.json` forman un índice local separado, con hashes e identidad de construcción. No es directamente intercambiable con records.json/config.json del corpus académico.

Cada unidad conserva el cuerpo completo, bloques fuente, fila original cuando corresponde, páginas PDF/impresas, idioma, versión, hash y contexto de los antecesores. Las vistas de búsqueda almacenan offsets contiguos y el identificador de unidad; al recuperarlas se devuelve esa unidad completa y sus advertencias, no solo la vista corta. Los IDs evitan devolver tres trozos del mismo procedimiento como tres respuestas independientes.

Las continuaciones de tabla siguen siendo candidatos revisables: no se fusionan filas entre páginas por conjetura. Los diagramas no se interpretan. Las unidades con dependencias gráficas lo señalan.

La evidencia completa puede superar 128 tokens y también el presupuesto de generación al combinar varios resultados. El adaptador futuro deberá seleccionar contexto completo dentro del presupuesto de 1.000 tokens por llamada; no enviarlo íntegro ni truncar instrucciones arbitrariamente. No se integró aún con el generador o los repositorios de producción.

## Reproducir

Desde `backend/` y con el entorno virtual de la raíz activo:

```bash
HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 python -m scripts.evaluate_ricoh_local
# Reutilizar vectores ya construidos:
HF_HOME=/tmp/ti-rag-hf HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 python -m scripts.evaluate_ricoh_local --existing
```

Esta sesión reutilizó el modelo del volumen Docker copiando únicamente el directorio público hub a `/tmp/ti-rag-hf/hub`. La caché es temporal. En otro entorno hay que disponer de esa revisión en una caché local o permitir la descarga legítima; no se necesitan credenciales de Supabase ni Groq para construir y evaluar.

Reporte completo: [ricoh_local_retrieval_validation.json](ricoh_local_retrieval_validation.json). La sonda amplia sobre problemas al enviar impresiones se guarda aparte y no se cuenta como un acierto de diagnóstico: la recuperación no determina por sí sola la causa de una avería.

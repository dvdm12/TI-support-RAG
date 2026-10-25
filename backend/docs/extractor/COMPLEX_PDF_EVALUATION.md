# Paso 7: estrategias y muestras PDF complejas

Actualización posterior de la misma sesión: el usuario autorizó buscar PDF en
la web y evaluarlos. Esa evaluación ya se realizó y está en
[WEB_PDF_EVALUATION.md](WEB_PDF_EVALUATION.md): seis PDF públicos, resultados
por componente y límites del pipeline completo. La indicación de aplazamiento
que sigue se conserva como historial y ya no es el pendiente vigente.

Se implementaron y verificaron mecanismos para tablas sin bordes y lectura de
columnas mediante perfiles explícitos. Se probaron continuaciones ambiguas y
OCR local separado. El 24-10-2026 el usuario indicó dejar la evaluación con
otros PDF reales para el cierre: todavía no dispone de ellos y podrá buscarlos.
Las pruebas controladas están completas; esa evaluación documental queda
pendiente. No acredita generalización a manuales nuevos ni calidad del RAG.

## Capacidades y límites

| Caso | Implementación y comprobación | Límite actual |
|---|---|---|
| Tabla sin bordes | `borderless_tables` recupera una cuadrícula con límites explícitos de filas y columnas. Se compara cada celda contra texto conocido. | Requiere geometría revisada por documento; no detecta automáticamente filas ni columnas. No se validaron celdas de varias líneas ni combinadas en documentos nuevos. |
| Varias columnas | `column_text` conserva el orden declarado de regiones y separa párrafos entre columnas. Contraste con el flujo nativo que entremezcla ambas. | Requiere cubrir todo el texto útil sin regiones superpuestas. No admite cambios de sección dentro de las columnas con el contrato actual. |
| Continuación entre páginas | Mantiene dos tablas/filas independientes y registra un enlace candidato. Tabla con celda vacía queda excluida. | No une filas cortadas ni infiere celdas faltantes. La exclusión afecta toda la tabla ambigua. |
| PDF de imagen | OCR explícito mediante Poppler y Tesseract local; candidato con fuente, página, raster, texto, palabras y confianza. | Resultado separado `pdf-ocr-review-v1`, siempre `review` y no indexable. No interpreta tablas, figuras ni orden complejo. |

Ricoh conserva su perfil y salida nativa v1. No se activa OCR como sustitución
automática cuando falla una página nativa. No se registran las muestras de
control como documentos reales ni se añaden al corpus académico o a la reserva.

## Perfil explícito: tabla sin bordes

La tabla se selecciona exclusivamente mediante una región con motivo y límites
de celdas. Los valores siguientes corresponden a la muestra controlada; no son
parámetros universales para un manual real.

```python
profile['strategies'] = {'pages': [{
    'first': 1, 'last': 1, 'reason': 'Límites de celdas revisados contra la muestra.',
    'regions': [{
        'bbox': [40, 110, 570, 230], 'tables': 'borderless_tables',
        'reason': 'Tabla sin bordes de la muestra controlada.',
        'settings': {
            'vertical_strategy': 'explicit', 'horizontal_strategy': 'explicit',
            'explicit_vertical_lines': [40, 210, 390, 570],
            'explicit_horizontal_lines': [110, 150, 190, 230],
        },
    }],
}]}
```

Las líneas explícitas deben ser finitas, ordenadas, estar dentro de la región y
delimitar al menos dos columnas y una fila de datos además del encabezado. No se
admiten parámetros desconocidos ni detección automática mediante texto en este
modo. Se comprueba que los límites no atraviesen caracteres y que una única
cuadrícula conserve las dimensiones y caracteres esperados. Como en el modo
previo, una región no puede cortar una tabla existente y una redetección no
puede perder palabras ya recuperadas. La conservación de caracteres no prueba
por sí sola que se hayan asignado correctamente causas y soluciones.

El adaptador sigue usando las opciones geométricas de
[pdfplumber](https://github.com/jsvine/pdfplumber#extracting-tables); las reglas
de selección y validación pertenecen al proyecto.

## Perfil explícito: columnas

```python
profile['strategies'] = {'pages': [{
    'first': 1, 'last': 1, 'text': 'column_text',
    'reason': 'Orden de lectura revisado: columna izquierda y después derecha.',
    'columns': [[40, 80, 285, 700], [325, 80, 570, 700]],
}]}
```

El orden de la lista es el orden de lectura. Después de excluir encabezados,
pies, pestañas y tablas, cada carácter útil debe pertenecer por completo a una
única columna. Las tablas deben caber completas en una columna. Se rechaza
contenido fuera de las regiones o que atraviese sus límites; no se descarta
silenciosamente. Al cambiar de columna se cierra el párrafo, incluso si las
líneas comparten altura. La reconstrucción mantiene coordenadas originales.

Un marcador que inicia una sección dentro de estas columnas requiere un
contrato que represente también la posición horizontal: se rechaza en vez de
atribuir por conjetura contenido de ambas columnas a la misma sección. La
validación de documentos guardados también verifica geometría y orden de
bloques contra las columnas declaradas antes de construir unidades.

## OCR para revisión

`src/rag/pdf_ocr_review.py` reutiliza la estrategia Tesseract existente con
escala 1, sin descargar modelos. Requiere Poppler (`pdftoppm`), Tesseract y sus
idiomas instalados; esta máquina dispone de `spa` y `eng`. Verifica hash,
página, resolución y que sea una página de imagen sin texto nativo. No admite
OCR para sustituir texto nativo ni sobre una página vacía sin imagen.

```bash
# Desde backend; sustituir PDF y hash por una fuente comprobada.
../.venv/bin/python -m scripts.review_pdf_scan /ruta/escaneado.pdf \
  --page 1 --source-sha256 SHA256_COMPROBADO \
  --language spa+eng --dpi 200 --output /tmp/candidato-ocr.json
```

El archivo de salida debe ser nuevo. Se comprueban los límites de palabras en
el raster y se eliminan imágenes temporales. Los errores de renderizado o motor
se propagan sin fallback. Las coordenadas son píxeles de la página rasterizada,
no puntos PDF; la confianza del motor no es una medida de exactitud semántica.
El candidato no es `extraction.json` v1 y no puede pasarse directamente al
constructor de evidencia. Falta revisar su texto/estructura y definir una
adaptación de procedencia antes de cualquier incorporación futura.

## Reproducción y evidencia

```bash
HF_HUB_OFFLINE=1 ../.venv/bin/python -m scripts.evaluate_complex_pdfs \
  --output /tmp/otra-evaluacion-pdf --with-ricoh
```

El directorio debe ser nuevo. `--without-ocr` ejecuta los otros controles y
declara explícitamente la omisión de OCR; no equivale a haberlo probado. Las
fuentes sintéticas se generan reproduciblemente mediante ReportLab/Pillow en
`scripts/complex_pdf_samples.py`: cuatro PDF, cinco páginas, con textos y
celdas conocidos. Se ejercitan auditoría, layout y reconstrucción; las pruebas
del pipeline completo inyectan un índice documental de control, porque las
muestras no son manuales reales con marcadores revisados.

La ejecución real del 24-10-2026 quedó local, ignorada por Git, en
`docs/rag_runs/complex_pdfs/check_20261024_final/`:

- `report.json`, `checks.csv`, `report.pdf`: nueve controles técnicos correctos,
  con su alcance y límites. No son métricas de respuestas RAG.
- `samples/`: tabla sin bordes, dos columnas, continuación de dos páginas y
  escaneado de control. Cinco páginas contrastadas visualmente con los bloques.
- `borderless_trace.json`, `columns_trace.json`: selección y geometría explícitas.
- `ocr_candidate.json`: texto de control recuperado completo, 12 palabras,
  confianza media 95,58; siempre revisión y no indexable. No extrapolar a escaneados degradados.

Veintidós pruebas nuevas; suite completa de **348 unitarias correctas**.
Pruebas adicionales de rechazo: celdas que cortan palabras, regiones ambiguas,
texto sin cubrir, orden alterado, procedencia OCR incorrecta, dependencias
ausentes, errores del motor, coordenadas inválidas y sobrescritura de informes.
Las cuadrículas explícitas cortas se conservan como tablas; la heurística previa
de iconos pequeños sigue aplicándose únicamente a las cuadrículas detectadas.

Se reextrajo Ricoh completo y se comparó en memoria: mismo SHA-256
`ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44`,
498 unidades con el hash guardado y seis tablas gráficas excluidas. Las nueve
referencias locales permanecen intactas. Sin nueva suite API, proveedores,
embeddings, Supabase ni índices modificados. Sin commit o push.

El paso 8 corresponde a verificar unidades completas y recuperación en español.
La evaluación diferida con PDF reales debe incluir tablas de varias líneas,
columnas con cambios de sección, escaneados degradados/rotados y documentos
mixtos. Mantener separados sus resultados de los controles sintéticos y de la
regresión del único manual real registrado.

# Extracción local del manual Ricoh

El manual real se procesa por separado del corpus académico. Esta etapa no crea
embeddings, no cambia el índice activo, no llama a Groq y no carga Supabase.

Con el entorno de la raíz activo, desde `backend/`:

```bash
python -m pip install -r requirements.txt
python -m scripts.extract_real_manual
```

El comando lee `manuals/manifest.real.json`, comprueba el hash y ejecuta el perfil
`pdf-outline-tables-v1`. Los documentos externos nuevos necesitan su propio
perfil revisado; las coordenadas del Ricoh no se aplican indiscriminadamente.
Las dependencias de extracción están en el entorno completo, no en la imagen
ligera de la API. No es necesario reconstruir ni reiniciar el contenedor.

## Archivos de salida

En `data/extracted/RICOH-MP4002-USER-GUIDE-EN/`, ignorado por Git:

- `extraction.json`: metadatos de fuente, auditoría de páginas, textos excluidos
  del diseño, jerarquía de secciones y bloques con coordenadas PDF.
- `review.md`: lectura por sección, con páginas PDF e impresas y filas completas
  de las tablas. Las imágenes permanecen en el PDF original.
- `summary.json`: cantidades, hash del JSON y limitaciones.
- `previews/`: muestras renderizadas para la revisión visual de esta ejecución;
  no las genera el comando de extracción.

El resumen revisado está en `docs/ricoh_extraction_validation.json`, separado de
los datos derivados extensos.

## Reglas de preservación

Los marcadores del PDF delimitan secciones también cuando una misma página
mezcla fax e impresión. La extracción selecciona 146 de los 149 marcadores:
los restantes están fuera del intervalo de contenido. Cada bloque conserva
página PDF, número impreso y coordenadas. `ancestor_section_ids` enlaza el
contexto del padre: por ejemplo, las advertencias de impresión que preceden
al procedimiento del controlador PCL 6. La fragmentación futura debe conservar
ese contexto y las condiciones de los pasos; los párrafos no son todavía chunks.

Las columnas de cada fila se guardan juntas y sin mover causas o soluciones
entre filas. Las celdas originales con saltos de línea se conservan en JSON;
el Markdown solo normaliza espacios para lectura. Las continuaciones de tabla
entre páginas son candidatos explícitos, no fusiones de filas inferidas.

La configuración documenta las 15 páginas excluidas: portada, página 2 vacía,
índice de contenidos, índice alfabético, notas y créditos. Conserva el código
editorial y copyright en los metadatos. Retira encabezados pequeños, números de
página y pestañas de capítulo laterales; los títulos grandes se conservan en
la jerarquía. Una página de contenido sin texto o numeración impresa detiene el
proceso; no se omite ni se sustituye automáticamente por OCR.

## Límites comprobados y revisión visual

Se extrajeron 213 páginas de contenido, 146 secciones, 1.647 párrafos y 92 tablas
con 383 filas de datos. La revisión visual contrastó las páginas PDF
65, 66, 75, 76, 78, 95, 97, 146, 185, 186 y 187 con sus bloques.

Seis tablas de las páginas 65, 66, 75, 76, 78 y 146 dependen de diagramas de
orientación, grapado, perforado o dirección del papel. Se conservan sus celdas y
referencias, pero llevan `text_index_eligible: false` y motivos de revisión.
No deben indexarse como si el texto describiera esos dibujos. El perfil corrige
los bordes de la tabla de la página 75 porque las líneas de sus ilustraciones
distorsionaban la detección automática de columnas. No se inventaron etiquetas
ni descripciones de imágenes para rellenar celdas.

Los procedimientos de impresión y las tablas de mensajes/causas/soluciones
revisados conservan sus pasos, condiciones y filas. Esto no certifica una
interpretación semántica completa de todas las ilustraciones del manual.

El siguiente paso es diseñar fragmentos con presupuesto de tokens y evaluar
recuperación local en español. El importador académico `load_corpus` conserva su
contrato y el registro real no se puede pasar todavía al indexador existente.

Implementación geométrica: [documentación de pdfplumber](https://github.com/jsvine/pdfplumber).

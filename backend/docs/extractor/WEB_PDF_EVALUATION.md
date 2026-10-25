# Evaluación con PDF públicos - 24-10-2026

El usuario autorizó buscar PDF en la web y aplicar las pruebas, sustituyendo
su indicación anterior de diferirlas hasta conseguir documentos propios.
Se descargaron seis PDF sin modificarlos: cuatro contenidos independientes;
tres archivos son variantes del mismo escaneado. Se examinaron seis páginas
seleccionadas, no todas las páginas de los artículos. No constituye un benchmark
representativo de manuales técnicos ni una aprobación semántica humana.

## Fuentes y procedencia

El registro congelado `docs/extractor/fixtures/web_pdf_sources_v1.json` incluye URL de
descarga, página de origen, SHA-256, tamaño y páginas. Los recursos de GitHub
usan commits concretos; Attention usa arXiv v5. La referencia OCR también tiene
hash. Las copias descargadas y los resultados extensos permanecen locales,
ignorados por Git; no se incorporaron al registro activo de manuales.

| ID | Fuente pública | Uso concreto |
|---|---|---|
| health | [Documento de pruebas de Camelot](https://github.com/camelot-dev/camelot/tree/master/tests/files), informe de financiación sanitaria | Página 1: tabla con encabezados de varios niveles; muestra de tres filas de datos. |
| bert | [BERT, ACL Anthology](https://aclanthology.org/N19-1423/) | Página 2: dos columnas con cambios de sección; lectura y conservación de caracteres. |
| attention | [Attention Is All You Need, arXiv v5](https://arxiv.org/abs/1706.03762v5) | Página 8: encabezado jerárquico y celdas combinadas; prueba de rechazo de perfil plano. |
| scan | [OCRmyPDF, linn.pdf](https://github.com/ocrmypdf/OCRmyPDF/blob/f23020e9a97cb1d23c75eb9ce93f0c5f50e1fb63/tests/resources/linn.pdf) | Escaneado de folleto técnico con texto y dos columnas. |
| skew | [OCRmyPDF, skew.pdf](https://github.com/ocrmypdf/OCRmyPDF/blob/f23020e9a97cb1d23c75eb9ce93f0c5f50e1fb63/tests/resources/skew.pdf) | Variante deformada/inclinada del mismo contenido. |
| rotated | [OCRmyPDF, rotated_skew.pdf](https://github.com/ocrmypdf/OCRmyPDF/blob/f23020e9a97cb1d23c75eb9ce93f0c5f50e1fb63/tests/resources/rotated_skew.pdf) | Segunda variante del mismo contenido, sin inferir su orientación por el nombre. |

OCRmyPDF declara atribución a Forat Electronics (1985), GFDL-1.2-or-later o
CC-BY-SA-3.0 para esos recursos en su
[REUSE.toml](https://github.com/ocrmypdf/OCRmyPDF/blob/main/REUSE.toml).
La licencia de código de una biblioteca no se asume aplicable a todos sus PDF.
Se conservaron originales y procedencia para estas pruebas locales.

## Resultados por componente

Nueve comprobaciones técnicas correctas, con alcance específico:

- La detección predeterminada de `health` produce una cuadrícula de 24 columnas
  y 40 filas de datos con ambigüedades; se mantiene no indexable. No equivale
  a una extracción correcta de sus ocho columnas semánticas.
- Una sonda con geometría explícita recupera exactamente 24 celdas: tres filas
  por ocho columnas. El encabezado jerárquico está fuera de esta sonda y sigue
  sin resolver. No se utiliza la primera fila de datos como encabezado ni se
  construyen unidades con esta cuadrícula parcial.
- En la página 2 de BERT, `column_text` conserva el orden izquierda/derecha y
  48/50 líneas. Se verificaron anclas de comienzo/final de ambas columnas y
  3.868 caracteres normalizados sin pérdida ni duplicación. Esto no asigna los
  cambios de sección internos al contrato v1.
- El perfil simple de celdas para la tabla de Attention se rechaza cuando sus
  límites atraviesan un encabezado combinado; no se fuerza una interpretación.
- Los tres candidatos OCR tienen palabras y procedencia, y permanecen en
  `review`, no indexables. No se convierten en extracción nativa v1.

La primera comprobación literal de caracteres de BERT detectó ocho `ﬁ` y un
`ﬂ` frente a sus letras expandidas. Se corrigió el comprobador para comparar
equivalencia Unicode NFKC, conservando también el diferencial bruto. No se
modificó producción ni se ignoraron dígitos, mayúsculas o pérdidas reales.
Hay pruebas de regresión para distinguir equivalencias y cambios de contenido.

## OCR: confianza, palabras y orden

Comparación descriptiva contra `linn.txt` de OCRmyPDF: NFKC, minúsculas y tokens
de palabras Unicode, sin puntuación. La referencia contiene artefactos y no
es una anotación humana nueva; las cifras miden acuerdo con esa transcripción.
No se fijó un umbral de calidad ni se presentan como exactitud semántica.

| Variante | Confianza media del motor | WER respecto a referencia | Recuperación de tokens sin orden |
|---|---:|---:|---:|
| scan | 93,84 | 48,03 % (365/760) | 95,79 % |
| skew | 93,33 | 47,89 % (364/760) | 95,66 % |
| rotated | 92,54 | 48,68 % (370/760) | 94,74 % |

WER usa distancia de edición de palabras con coste unitario, dividida entre
las 760 palabras normalizadas de referencia; puede superar el 100 % por
inserciones. La recuperación sin orden cuenta la intersección de multiconjuntos,
por lo que no acredita que las palabras formen un procedimiento correcto.
Los candidatos OCR muestran mezcla horizontal de las columnas en el apartado
de instrucciones: este límite se contrastó con la página original. La confianza
alta no autoriza indexar estos resultados como procedimientos fiables.

## Compatibilidad del pipeline completo

**0/6 documentos completan el pipeline con el perfil genérico de prueba.**
Ese resultado no equivale a que ningún perfil específico pueda soportarlos.
La prueba usa originales sin inventar marcadores y conserva los requisitos del
extractor nativo actual:

- `health`, `bert` y los tres escaneados: rechazo durante análisis por ausencia
  de marcadores. Necesitan otra estrategia de secciones o un perfil revisado.
- `attention`: rechazo de auditoría porque la primera página no tiene un número
  impreso que satisfaga el perfil genérico. Necesita selección de páginas y
  procedencia revisadas; no se eliminó automáticamente esa página para pasar.

Los rechazos correctos son comprobaciones de protección, no éxitos de extracción
completa. No se aceptó una extracción parcial ni se generó un índice. Quedan
pendientes perfiles para documentos sin marcadores, secciones con coordenada
horizontal, encabezados multinivel y OCR con segmentación/orden de lectura.
Esta sesión evalúa esos límites; no los declara resueltos.

## Ejecución y reproducción

Evidencia LOCAL IGNORADA en `docs/rag_runs/web_pdfs/check_20261024/`:

- `sources/` y `download_inventory.json`: seis originales y transcripción.
- `results_final/report.json`, `checks.csv`, `report.pdf`: ejecución vigente.
- `results_final/*_probe.json`: sondas geométricas y lectura de columnas.
- `results_final/*_ocr_candidate.json`: tres candidatos OCR para revisión.
- `results_final/pipeline-*/`: manifiestos privados de prueba y copias intactas.
- `results/`: primera ejecución diagnóstica, anterior a corregir la comparación
  de ligaduras. No mezclar ese resultado con el informe final.

```bash
# Desde backend, con las fuentes descargadas disponibles y un directorio nuevo:
HF_HUB_OFFLINE=1 ../.venv/bin/python -m scripts.evaluate_web_pdfs \
  --sources docs/rag_runs/web_pdfs/check_20261024/sources \
  --output /tmp/otra-prueba-web --with-ricoh
```

El runner no descarga fuentes ni modelos: valida todos los hashes antes de
extraer y otra vez al terminar. Las URL congeladas permiten recuperar los
archivos si faltan; un hash diferente requiere revisar la fuente. No sustituir
la referencia para ocultar diferencias. Devuelve salida fallida ante errores
de componentes o regresión Ricoh, conservando el informe; la falta de soporte
documental se reporta por separado.

Nueve pruebas unitarias nuevas para métricas, equivalencia de caracteres,
alteraciones de archivos y confinamiento de rutas. Suite completa: **357
unitarias correctas**, sin nueva suite API. Ricoh se reextrajo completamente:
salida idéntica, 498 unidades con hash guardado y nueve referencias intactas.
PDF/perfil Ricoh, corpus académico, modelos y Supabase sin modificar. Sin
commit ni push. La evaluación no acredita una mejora de respuestas RAG.

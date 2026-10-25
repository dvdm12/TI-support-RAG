# Manuales de soporte TI

Manuales organizados según las siete categorías del contrato `SolicitudTI`. Los siete manuales académicos se clasificaron leyendo el contenido completo y la categoría declarada en cada PDF. Los documentos externos se registran aparte, como se describe al final.

Los siete documentos son **simulados para práctica académica**, de la organización ficticia AulaTI. Todos indican versión **2.0**, fecha **14 de octubre de 2026** y contienen dos páginas. No representan políticas institucionales reales.

| Categoría | Manual | Alcance principal |
|---|---|---|
| hardware | [manual_hardware.pdf](hardware/manual_hardware.pdf) | Equipos, componentes físicos, alimentación y periféricos |
| software | [manual_software.pdf](software/manual_software.pdf) | Aplicaciones, instalación, actualizaciones, colas y controladores de impresión |
| redes | [manual_redes.pdf](redes/manual_redes.pdf) | Wi-Fi, conexiones cableadas y acceso a servicios de red |
| cuentas | [manual_cuentas.pdf](cuentas/manual_cuentas.pdf) | Creación, modificación, recuperación y desactivación de cuentas |
| seguridad | [manual_seguridad.pdf](seguridad/manual_seguridad.pdf) | Phishing, credenciales expuestas y actividad sospechosa |
| acceso | [manual_acceso.pdf](acceso/manual_acceso.pdf) | Ingreso a recursos, credenciales rechazadas, permisos y error 403 |
| otros | [manual_otros.pdf](otros/manual_otros.pdf) | Aclaración, reclasificación, derivación y límites del soporte |

## Procedencia e integridad

Se conserva el paquete original `TI-support-RAG_Manuales_PDF.zip`. Los PDF organizados mantienen exactamente los bytes del ZIP; el manual de hardware que ya existía era idéntico y se conservó.

[manifest.json](manifest.json) registra identificador documental, categoría, título, versión, fecha, ruta, número de páginas y SHA-256 de cada manual, además de la huella del ZIP. Las rutas del manifiesto son relativas a este directorio.

## Límites entre categorías

- **Cuentas** aborda operaciones administrativas sobre la cuenta. **Acceso** aborda la dificultad inmediata para ingresar a un recurso. **Seguridad** aborda sospechas o evidencias de riesgo.
- En impresión, los mecanismos físicos corresponden a **hardware**, mientras que colas y controladores corresponden a **software**.
- **Otros** cubre clasificación y derivación; no habilita respuestas sobre cualquier tema. La falta de cobertura documental no obliga a cambiar a `otros` una solicitud que ya es clasificable.

Cada manual se conserva una sola vez en su categoría principal. Las referencias a otras categorías permanecen en el contenido original.

El corpus activo de ingestión está en [data/corpus/v2](../data/corpus/v2/README.md), con su propio manifiesto y copias idénticas de estos PDF. La implementación procesa únicamente ese corpus; no ingiere ambos directorios. El ZIP, este índice y los `.gitkeep` no son manuales adicionales. La comparación ejecutada se conserva en [docs/evaluacion/recuperacion/rag_comparison.json](../docs/evaluacion/recuperacion/rag_comparison.json).

## Documentos externos reales

[manifest.real.json](manifest.real.json) registra las fuentes externas por separado
del manifiesto académico y del corpus activo `data/corpus/v2/`. Sus rutas son
relativas a `manuals/`. `simulated: false` indica que no se trata de una fuente
sintética; no acredita por sí solo la autenticidad ni la vigencia del documento.

| Documento | Idioma | Páginas | Estado |
|---|---|---|---|
| [User Guide D129-7802, Ricoh MP 4002/4002SP/5002/5002SP](hardware/RICOHMP4002_MANUAL.pdf) | Inglés (`en`) | 228 | Identidad verificada; índice local y evaluación parcial; sin cargar en Supabase |

El PDF fue aportado por el usuario el 20-10-2026. Se verificó que es idéntico byte
por byte a la [copia oficial de Ricoh](https://support.ricoh.com/bb_v1oi/pub_e/oi/0001043/0001043003/VD1297802_01/D1297802_en.pdf)
enlazada desde [la página de la familia MP 4002/4002SP/5002/5002SP](https://support.ricoh.com/bb_v1oi/html/oi/re/model/mp42/mp42en.htm).
Ambas copias tienen 5.520.145 bytes y el mismo SHA-256. La asociación con MP 4002
queda confirmada por el fabricante; no depende del nombre del archivo.

El identificador editorial impreso en la última página es **D129-7802** y se
registra como `version`; no equivale a una versión de firmware. El PDF muestra
copyright de 2011 y la descarga oficial indica actualización del 10 de enero de
2012. No se interpreta esa actualización ni las fechas técnicas del PDF como
fecha exacta de publicación. La guía es compartida por la familia y conserva
diferencias por región y opciones instaladas. Evidencia de la comparación:
[ricoh_manual_verification.json](../docs/extractor/ricoh_manual_verification.json).

La inspección encontró texto extraíble, una página 2 en blanco y tablas que
relacionan mensajes, causas y soluciones. La futura extracción deberá conservar
esas relaciones y distinguir la página PDF de la numeración impresa.

El comando local `python -m scripts.extract_real_manual`, ejecutado desde
`backend/`, procesa este registro mediante `src/rag/external_ingestion.py`.
La [guía de extracción](../docs/extractor/RICOH_EXTRACTION.md) describe el perfil geométrico,
las salidas revisables, la preservación de contexto y las seis tablas gráficas
que no son elegibles para indexación de texto. Resultado:
[revisión por secciones](../data/extracted/RICOH-MP4002-USER-GUIDE-EN/review.md).

El registro tiene estado `locally_indexed_retrieval_partial`. Se construyó un
índice local separado con 498 unidades completas, 779 vistas de búsqueda y
embeddings reales de hasta 128 tokens por vista. La evaluación diagnóstica
recuperó evidencia esperada entre los tres primeros resultados en 11 de 12
preguntas en español; el caso de impresión retenida sigue fallando. Detalles:
[fragmentación y recuperación local](../docs/extractor/RICOH_LOCAL_RETRIEVAL.md).

No se cargaron filas en Supabase ni se cambió el índice de la API. El importador
e indexador académicos mantienen su contrato original; no añadir el PDF real al
manifiesto simulado ni marcarlo como simulado para eludir validaciones.

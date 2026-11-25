---
tipo: bitacora-parcial
curso: Electiva VI
periodo: EAM-2026II
proyecto: Mesa de Ayuda TI Inteligente
corte: 2
fecha_actualizacion: 2026-10-25
zona_horaria: America/Bogota
estado: borrador-local-en-consolidacion
revision_humana: pendiente
---

# Bitácora del Parcial 2 — Mesa de Ayuda TI Inteligente

> Borrador local del 25 de octubre de 2026. Documenta el desarrollo y la evaluación del RAG; requiere revisión del equipo antes de su entrega. La revisión de respuestas y la evaluación de reserva siguen pendientes.

## 1. Identificación y propósito

| Campo | Registro |
|---|---|
| Curso y periodo | Electiva VI · EAM-2026II |
| Proyecto | Mesa de Ayuda TI Inteligente |
| Corte | Parcial 2 |
| Entrada principal para el profesor | [Notebook Parcial 2](../../notebooks/parcial2.ipynb) |
| Instrucciones de ejecución | [Guía del profesor](../../notebooks/GUIA_PROFESOR.md) |
| Modelo generativo | `openai/gpt-oss-20b`, mediante Groq |
| Persistencia documental | Supabase como repositorio vectorial de fragmentos |
| Versiones de prompts | Clasificador `system_v8`; generador `rag_v6` |
| Estado del corte | Recorrido RAG comprobado; evaluación de respuestas y reserva pendientes |

El objetivo del segundo corte es extender la clasificación del primer parcial con recuperación documental y generación de respuestas sustentadas en fuentes. El notebook permite inspeccionar el recorrido, ejecutar consultas reales y exportar evidencias.

## 2. Integrantes y continuidad del primer corte

La [bitácora del Parcial 1](../parcial1/bitacora_parcial.md) identifica a **David Mantilla Aviles** y **Juan Camilo Velez**. Allí se registran, respectivamente, implementación e integración técnica, y adaptación al dominio y revisión de resultados.

Esta bitácora conserva esa identificación como antecedente. La distribución definitiva de responsabilidades del segundo corte debe confirmarse por el equipo. La participación descrita en el primer corte no acredita que la revisión humana del segundo ya se haya realizado. También falta completar los nombres en la variable `TEAM` del notebook.

## 3. Problema y evolución del alcance

Una mesa de ayuda necesita identificar la solicitud, detectar información faltante y orientar al usuario con procedimientos aplicables. Una clasificación correcta resulta insuficiente cuando se requiere una instrucción respaldada por documentación.

El primer parcial implementó clasificación estructurada, validación con Pydantic, decisiones programáticas y entrada de imágenes mediante OCR. El segundo añade corpus documental, embeddings, persistencia remota, recuperación híbrida, construcción de contexto, generación con citas y controles de respaldo.

Se conserva el principio: **el modelo propone; el programa valida; el sistema decide**. La aplicación no ejecuta reparaciones ni acciones administrativas sobre equipos del usuario.

## 4. Recorrido RAG implementado

```text
Texto o imagen → OCR cuando corresponde
    → clasificación SolicitudTI con Groq
    → validación y políticas locales
    → búsqueda semántica Supabase + búsqueda léxica BM25
    → fusión RRF y selección de pasajes
    → contexto con catálogo de fuentes
    → generación RespuestaRAG con Groq
    → validación de estructura, citas y respaldo; corrección cuando aplica
    → decisión local y registro de evidencia
```

El notebook permite observar la entrada, la clasificación, los fragmentos recuperados, el contexto entregado al generador, la respuesta y sus fuentes. El OCR transforma imágenes en texto antes de ingresar al recorrido de consulta.

La validación distingue el formato de la respuesta de su respaldo documental. Una respuesta puede cumplir el esquema y conservar citas válidas sin cubrir correctamente todos los pasos necesarios; por eso se mantiene una revisión humana separada.

## 5. Corpus, fragmentación y recuperación

El corpus académico contiene **7 PDF simulados, 14 páginas, 35 secciones y 70 fragmentos**. Sus procedimientos sirven al experimento académico; no representan una política institucional certificada.

| Componente | Configuración registrada |
|---|---|
| Corpus | `ti-manuals-v2-d479e96962b17496eaa3` |
| Fragmentación | Por secciones; máximo 420 caracteres y 80 tokens reales; sin solapamiento |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revisión fijada en el índice |
| Vectores | 384 dimensiones, normalizados; límite del modelo de 128 tokens |
| Recuperación | Hasta 10 candidatos por vía; selección final Top-3 |
| Fusión | RRF, constante 60; peso semántico 1 y léxico 2 |
| Tabla y función remotas | `clase08_fragmentos` y `clase08_buscar_fragmentos` |

Se conserva un índice local para reproducibilidad y consulta de evidencias. Cada fragmento mantiene su asociación con el documento y la sección de origen, lo que permite revisar el respaldo de las citas.

El documento Ricoh utilizado en regresiones del extractor queda fuera del corpus RAG y de la entrega del parcial.

## 6. Cronología de avances

| Fecha de 2026 | Avance documentado | Evidencia |
|---|---|---|
| 14 de octubre | Integración de recuperación documental y búsqueda vectorial en Supabase | [Guía RAG](../rag/RAG.md) |
| 21 de octubre | Comparación de recuperación y preparación de evaluación | [Métricas de recuperación](../evaluacion/recuperacion/RETRIEVAL_METRICS.md) |
| 21–24 de octubre | Mejora de cobertura, prompt `rag_v6` y medición real de tokens A/B | [Cobertura](../evaluacion/recuperacion/COVERAGE_IMPROVEMENTS.md) y [tokens](../evaluacion/generacion/GENERATION_TOKENS.md) |
| 25 de octubre | Validación estricta, corrección del clasificador `system_v8` y trazas RRF | [Auditoría del corte](guias/CLASS09_AUDIT.md) y [trazas](../evaluacion/recuperacion/RRF_TRACES.md) |
| 25 de octubre | Notebook integrado, panel del profesor y exportación organizada | [Guía de resultados](guias/RESULTADOS.md) |
| 25 de octubre | Comprobación del recorrido del notebook con Groq y Supabase reales | [Informe de ejecución](ejecuciones/20261025T225855Z-github-40241724176-intento2/notebook.json) |
| 25 de octubre | Consolidación de esta bitácora como borrador local | Este documento |

Los informes históricos conservan los resultados y las condiciones de su ejecución. Las comparaciones se interpretan según la versión de recuperación, el prompt y los casos utilizados en cada experimento.

## 7. Protocolo de evaluación

Se distinguen tres poblaciones:

1. **Desarrollo:** 13 casos conocidos, de los cuales 7 son documentales y 6 de comportamiento. Se utilizaron para ajustar el sistema.
2. **Revisión de respuestas:** ficha con 27 respuestas guardadas, correspondientes a 14 generaciones A/B y 13 observaciones del recorrido completo con el clasificador v8. La revisión debe usar esas salidas, sin regenerarlas.
3. **Reserva:** 12 candidatos pendientes de aprobación y congelación humana. No se abren ni ejecutan desde el notebook de demostración.

Las métricas de recuperación evalúan selección de pasajes y cobertura del contexto. Las métricas de tokens contabilizan consumo en un experimento de generación. Ninguna de las dos sustituye la evaluación de corrección, fidelidad, citas y utilidad de las respuestas.

## 8. Resultados de recuperación en desarrollo

La [comparación guardada](../evaluacion/recuperacion/COVERAGE_IMPROVEMENTS.md) utiliza las mismas siete preguntas documentales y 35 unidades anotadas por el agente. Reproduce candidatos semánticos guardados y recalcula selección y contexto; no representa siete consultas nuevas al proveedor en cada ejecución del notebook.

| Medida | Híbrida anterior | Híbrida mejorada |
|---|---:|---:|
| Precision@3 | 52,38 % | 66,67 % |
| Recall@3 | 80,95 % | 100,00 % |
| Hit@3 | 85,71 % | 100,00 % |
| MRR@3 | 0,8571 | 1,0000 |
| Cobertura macro de unidades en Top-3 | 80,36 % | 100,00 % |
| Cobertura macro del contexto final | 76,79 % | 100,00 % |
| Preguntas completas en Top-3 | 5/7 | 7/7 |
| Preguntas completas en contexto | 4/7 | 7/7 |
| Unidades presentes en Top-3 | 26/35 | 35/35 |

Los cambios normalizan términos como Wi-Fi y códigos técnicos, aplican la exclusión de pasajes no pertinentes antes de cortar Top-3 y compactan el prompt para conservar más evidencia dentro del presupuesto. Los pesos RRF permanecen en 1/2.

El 66,67 % de precisión es el máximo macro de esta anotación: varias preguntas tienen menos de tres fragmentos relevantes. El 100 % de cobertura corresponde a desarrollo conocido utilizado para ajustar. No prueba generalización ni que el generador incluya correctamente todas las unidades recuperadas. Las anotaciones requieren revisión humana.

## 9. Consumo medido de generación

El [experimento A/B del 21 de octubre](../evaluacion/generacion/GENERATION_TOKENS.md) realizó 14 llamadas reales a Groq: siete pares de generación semántica e híbrida. Ambas variantes usaron `rag_v6`, temperatura 0, razonamiento `low` y máximo 800 tokens de salida. La entrada al generador se limitó a 1000 tokens; el máximo real observado fue 785.

| Tokens informados por Groq, suma de siete casos | Semántica A | Híbrida B |
|---|---:|---:|
| Entrada | 5.354 | 5.388 |
| Salida | 1.238 | 1.135 |
| Total | 6.592 | 6.523 |

La diferencia total fue de 69 tokens a favor de B, un 1,05 % en esa ejecución. Una observación por combinación no demuestra ahorro estable. Esta medición excluye clasificación, revisión de respaldo y correcciones; no representa el consumo del recorrido RAG completo. Los contratos y las etiquetas de cita fueron válidos, pero su validez automática no acredita fidelidad documental.

## 10. Notebook ejecutado con proveedores reales

La [prueba local conservada](ejecuciones/20261025T183222Z/verificacion.json) se realizó el 25 de octubre de 2026, de 13:32:22 a 13:33:06, hora de Bogotá. Completó 18 celdas de código, OCR, consulta del corpus de 70 fragmentos y dos consultas reales con recuperación y generación. No modificó el corpus ni utilizó la reserva.

La segunda ejecución documentada también completó las **18 celdas de código**, con Groq y Supabase activos. El [informe del notebook](ejecuciones/20261025T225855Z-github-40241724176-intento2/notebook.json) registra:

| Comprobación del recorrido RAG | Resultado registrado |
|---|---|
| OCR | Correcto |
| Corpus consultado | 70 fragmentos |
| Recorrido del punto 10 | `consulta_real`, estado `OK_REQUIERE_HUMANO`, sin fallo registrado |
| Panel del profesor | `live_query`, estado `OK_VALIDADO`, sin fallo registrado |
| Exportaciones y ZIP | Generados |

`OK_REQUIERE_HUMANO` expresa una decisión del flujo, no un error de ejecución. `OK_VALIDADO` indica que se superaron los controles automáticos aplicados; la calidad de la respuesta sigue requiriendo revisión.

Estas ejecuciones verifican el recorrido y la producción de evidencias. No constituyen una evaluación nueva de todas las respuestas de desarrollo ni reemplazan la revisión humana. La ejecución real en Colab sigue pendiente.

## 11. Hallazgos del RAG, correcciones y decisiones

| Hallazgo | Tratamiento y alcance |
|---|---|
| Resumen del clasificador mayor de 240 caracteres en E06 | `system_v8` limita el resumen y pide reformular la solicitud; el esquema incorpora sus límites. |
| Pérdida de términos técnicos o pasajes aplicables | Normalización léxica y filtrado antes del corte, comprobados con los casos conocidos. |
| Cobertura documental completa sin evaluación humana de la respuesta | Separar recuperación, contexto y respuesta; no interpretar el 100 % de cobertura como corrección del contenido generado. |
| Presupuesto de contexto que dejaba fuera unidades relevantes | Compactar `rag_v6` conservando reglas, fuentes y pasajes completos; comparar cobertura de Top-3 y contexto final. |

Se mantiene la híbrida mejorada como configuración de recuperación de trabajo. La elección académica final requiere revisar respuestas y evaluar la reserva aprobada. No se decide únicamente por la cobertura de desarrollo.

## 12. Evidencias del RAG

El profesor puede recorrer el [notebook](../../notebooks/parcial2.ipynb) siguiendo su [guía](../../notebooks/GUIA_PROFESOR.md), inspeccionar los pasajes recuperados y contrastar las respuestas con sus fuentes y las métricas exportadas.

Cada ejecución del notebook crea una carpeta UTC bajo `backend/docs/parcial2/ejecuciones/`, con JSON, CSV, PDF comparativo y `parcial2_resultados.zip`. El PDF explica recuperación histórica de desarrollo; las respuestas de consultas nuevas se conservan en JSON. Todavía no se produce un PDF explicativo individual por consulta.

| Evidencia | Ubicación o referencia |
|---|---|
| Guía de interpretación de exportaciones | [RESULTADOS.md](guias/RESULTADOS.md) |
| Comparación de recuperación | [Informe JSON](../evaluacion/recuperacion/coverage_improvements_20261021.json) y [PDF](../evaluacion/recuperacion/coverage_improvements_20261021.pdf) |
| Consumo de generación | [Informe JSON](../evaluacion/generacion/generation_tokens_20261021.json) y [PDF](../evaluacion/generacion/generation_tokens_20261021.pdf) |
| Revisión humana pendiente | [Ficha JSON](../human_review/class09_review_v1.json) y [guía](../human_review/README.md) |
| Ejecución local del notebook | [Carpeta 20261025T183222Z](ejecuciones/20261025T183222Z/) |
| Segunda ejecución del notebook | [Informe local del recorrido](ejecuciones/20261025T225855Z-github-40241724176-intento2/notebook.json) |

El informe de la segunda ejecución está conservado localmente y no forma parte del repositorio público; su enlace no estará disponible en otro clon. La muestra local del 25 de octubre y los informes de recuperación y generación permiten consultar las evidencias compartibles del experimento.

## 13. Pendientes de evaluación y entrega

- [ ] Confirmar responsabilidades del equipo y completar `TEAM` en el notebook.
- [ ] Revisar humanamente las 27 respuestas guardadas, con identidad del revisor, fecha y justificación.
- [ ] Realizar doble revisión independiente de al menos tres casos y adjudicar diferencias.
- [ ] Consolidar métricas de respuesta a partir de esa revisión.
- [ ] Aprobar y congelar la reserva antes de ejecutarla, sin utilizarla para ajustar el sistema.
- [ ] Evaluar la reserva con el sistema congelado y conservar su protocolo y resultados.
- [ ] Formular la decisión comparativa final y sus límites.
- [ ] Ejecutar y verificar una sesión real en Colab con credenciales propias.
- [ ] Revisar esta bitácora y preparar la presentación PDF del segundo corte.

## 14. Estado de esta versión

Esta versión consolida los avances comprobados hasta el 25 de octubre de 2026. Su preparación reutiliza evidencias guardadas; no implica nuevas llamadas a Groq, cambios en Supabase ni apertura de la reserva.

La bitácora permanece como **borrador local, sin publicar**. Las conclusiones sobre calidad de respuesta y elección final quedan sujetas a la evaluación y aprobación del equipo.

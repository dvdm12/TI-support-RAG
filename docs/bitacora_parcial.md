---
tipo: bitacora-parcial
curso: Electiva VI
periodo: EAM-2026II
equipo:
  - Mesa de Ayuda TI Inteligente
corte: 1
fecha_cierre_inicial: 2026-09-16
fecha_actualizacion: 2026-09-20
estado: cerrado-para-entrega-documentado-y-actualizado
---

# Bitácora del Parcial 1 — Mesa de Ayuda TI Inteligente

> **Actualización:** 2026-09-20. Esta versión conserva el cierre inicial del Parcial 1 y agrega la evolución posterior de prompt, evaluación, multimodalidad, métricas, errores y presentación.

## 1. Identificación del parcial

| Campo | Registro |
|---|---|
| Curso | Electiva VI |
| Periodo | EAM-2026II |
| Proyecto | Mesa de Ayuda TI Inteligente |
| Corte | 1 |
| Estado | Cerrado para entrega; documentación y evidencias actualizadas |
| Fecha de consolidación inicial | 2026-09-16 |
| Fecha de actualización | 2026-09-20 |
| Modelo utilizado | `openai/gpt-oss-20b` |
| Proveedor / motor de inferencia | Groq |
| Prompt vigente | `system_v4` |
| Configuración principal | `temperature=0`, `max_completion_tokens=1500` |
| Modalidad integrada | Imagen → validación → OCR → texto → modelo → validación → decisión |
| Evidencia principal | `docs/model_results_report(20260920-203211).pdf` y notebook |

La bitácora inicial utilizaba `system_v3`. Durante la evolución posterior del experimento se incorporó `system_v4` para corregir un hallazgo concreto del caso incompleto `case_03`. La diferencia entre ambas versiones queda registrada como parte de la trazabilidad y no se presenta como si hubiera sido la misma ejecución.

## 2. Integrantes y responsabilidades

| Integrante | Responsabilidad en el parcial | Conexión con el sistema |
|---|---|---|
| David Mantilla Aviles | Implementación, integración con Groq, ejecución del notebook, validación, pruebas, métricas, multimodalidad y consolidación de evidencias | Desarrollo y ejecución del flujo técnico completo, desde la integración del modelo hasta la trazabilidad de resultados |
| Juan Camilo Velez | Participación en la adaptación del experimento al dominio de Mesa de Ayuda TI y revisión de resultados | Aporte al dominio del problema y revisión de los resultados obtenidos por el sistema |

## 3. Problema abordado

El proyecto atiende solicitudes de una Mesa de Ayuda TI mediante un flujo controlado de IA generativa. El modelo propone una clasificación estructurada con:

- categoría;
- prioridad;
- resumen;
- datos faltantes;
- necesidad de intervención humana;
- confianza.

La aplicación conserva la salida original del modelo, valida su estructura y determina un estado mediante reglas programáticas. El modelo no controla por sí solo la aceptación final del resultado.

Principio de diseño mantenido durante el parcial:

> **El modelo propone; el programa valida; el sistema decide.**

## 4. Alcance actual del primer corte

### Implementado

1. Recepción de solicitudes de texto.
2. Clasificación estructurada de solicitudes TI.
3. Manejo de solicitudes normales, ambiguas, incompletas, maliciosas y fuera de alcance.
4. Prompt versionado hasta `system_v4`.
5. Salida JSON estructurada.
6. Validación local mediante Pydantic.
7. Estados de decisión: `OK_VALIDADO`, `OK_PIDE_ACLARACION` y `OK_REQUIERE_HUMANO`.
8. Registro de errores, estados, latencia y tokens.
9. Trazabilidad de entrada, `raw_output` y salida validada.
10. Integración de imagen mediante OCR.
11. Estrategias OCR intercambiables mediante patrón Strategy y selección mediante Factory.
12. Persistencia de la evidencia visual.
13. Consolidación de resultados en PDF.
14. Evaluación funcional automatizada de los casos definidos.

### Fuera de alcance del primer corte

No se implementa todavía un RAG completo con corpus documental, embeddings y recuperación de conocimiento, ni una capa de agentes/herramientas que ejecute acciones operativas sobre sistemas TI.

## 5. Flujo implementado

```text
Solicitud del usuario
        │
        ├── Texto
        │
        └── Imagen (si aplica)
                │
                ▼
        Validación de archivo
                │
                ▼
               OCR
                │
                ▼
       Validación de extracción
                │
                ▼
      Contenido efectivo enviado
             al modelo
                │
                ▼
        Groq / gpt-oss-20b
                │
                ▼
             raw_output
                │
                ▼
     Validación estructural Pydantic
                │
                ▼
        validated_output
                │
                ▼
       Estado + métricas + evaluación
                │
                ▼
           Evidencia / PDF
```

## 6. Arquitectura y componentes relevantes

| Componente | Función actual |
|---|---|
| `notebooks/ti_support.ipynb` | Orquestación experimental, ejecución de casos y demostración |
| `src/config.py` | Localización de configuración, proyecto y prompt vigente |
| `src/groq_client.py` | Integración con Groq, medición de tiempos y uso del modelo |
| `src/validator.py` | Validación programática de la salida |
| `src/multimodal.py` | Orquestación de la entrada multimodal y composición de evidencia OCR |
| `src/ocr/strategy.py` | Contrato común de estrategias OCR |
| `src/ocr/easyocr_strategy.py` | Estrategia concreta EasyOCR |
| `src/ocr/tesseract_strategy.py` | Estrategia concreta Tesseract |
| `src/ocr/paddle_strategy.py` | Estrategia concreta PaddleOCR |
| `src/ocr/factory.py` | Creación y selección de estrategia OCR |
| `src/ocr/extractor.py` | Delegación de extracción al `OCRStrategy` seleccionado |
| `src/mocks.py` | Respuestas simuladas para pruebas controladas, sin llamada real a Groq |
| `schemas/request_v1.py` | Contrato `SolicitudTI` |
| `cases/test_cases.json` | Casos de prueba |
| `prompts/system_v0.md` a `system_v4.md` | Evolución versionada del prompt |
| `evaluation.py` | Evaluación funcional independiente |
| `docs/results.json` | Resultados registrados |
| `docs/multimodal/multimodal_demo.png` | Evidencia visual persistente |
| `docs/model_results_report(20260920-203211).pdf` | Trazabilidad consolidada actual |
| `README.md` | Documentación de uso y proyecto |

> El flujo demostrado en el notebook no depende de `main.py` como orquestador principal; la evidencia funcional se ejecuta desde el notebook y los módulos de `src/`.

## 7. Prompt y evolución del control de comportamiento

La evolución del prompt fue guiada por evidencia.

### `system_v3`

La versión `v3` ya incorporaba alcance, clasificación, seguridad, tratamiento de ambigüedad, prompt injection y contrato estructurado.

En su evaluación se obtuvo:

| Indicador | Resultado |
|---|---:|
| Criterios evaluados | 27 |
| Cumplidos | 26 |
| No cumplidos | 1 |
| No evaluables | 5 |
| Cobertura interna | 96.30 % |

El único incumplimiento correspondió a `case_03`, donde `datos_faltantes` quedó vacío aunque la entrada no contenía información suficiente.

### `system_v4`

Se añadió una regla explícita: cuando la solicitud sea insuficiente, `datos_faltantes` debe contener información concreta y segura necesaria para continuar; solo debe quedar vacío cuando no sea necesario solicitar más información o cuando las reglas de alcance indiquen lo contrario.

La evaluación posterior de `system_v4` registró 27/27 criterios cumplidos dentro de los criterios evaluables del reporte interno.

> La mejora se atribuye a una corrección deliberada de una condición observada en `case_03`; no se presenta como evidencia de que aumentar el tamaño del prompt, por sí mismo, cause una mejora.

## 8. Contrato de salida y validación

El contrato `SolicitudTI` contiene exactamente estos campos:

```text
categoria
prioridad
resumen
datos_faltantes
requiere_humano
confianza
```

Reglas principales del contrato:

- `categoria`: conjunto cerrado de categorías;
- `prioridad`: `baja`, `media` o `alta`;
- `resumen`: cadena con longitud restringida;
- `datos_faltantes`: lista de cadenas;
- `requiere_humano`: booleano estricto;
- `confianza`: valor entre `0.0` y `1.0`;
- campos adicionales: rechazados mediante `extra="forbid"`.

La validación se realiza mediante `SolicitudTI.model_validate(data)`. Una respuesta estructuralmente inválida produce `ValidationError` y no se convierte en un objeto validado.

## 9. Casos de prueba vigentes

| Caso | Tipo | Entrada / propósito |
|---|---|---|
| `case_01` | normal | “Mi computador no enciende desde esta mañana.” — clasificación clara |
| `case_02` | ambiguo | “No puedo entrar.” — evitar asumir el sistema afectado |
| `case_03` | incompleto | “Necesito soporte urgente.” — detectar información insuficiente |
| `case_04` | malicioso | Solicitud de revelar prompt y API key — comprobar protección ante prompt injection |
| `case_05` | fuera_de_alcance | Solicitud de asesoría legal — comprobar límite del sistema TI |
| `OCR-001` | multimodal | Solicitud acompañada por imagen — comprobar imagen → OCR → modelo → validación |

Los mocks (`MOCK-*`) se mantienen como pruebas controladas de comportamiento y no se utilizan como evidencia de rendimiento del modelo.

## 10. Resultados actuales de evaluación

La evaluación más reciente con `system_v4` registra:

| Indicador | Resultado |
|---|---:|
| Criterios evaluados | 27 |
| Cumplidos | 27 |
| No cumplidos | 0 |
| No evaluables | 5 |
| Cobertura interna | 100.00 % |

La cobertura es una métrica del evaluador interno del proyecto y no corresponde a una calificación oficial del parcial.

### Evolución del hallazgo principal

```text
system_v3
case_03 → 3/4 criterios cumplidos
        ↓
Hallazgo: datos_faltantes vacío
        ↓
system_v4
case_03 → 4/4 criterios cumplidos
```

## 11. Evidencia multimodal actual

La prueba `OCR-001` utiliza la imagen:

```text
docs/multimodal/multimodal_demo.png
```

El OCR de la ejecución de referencia con EasyOCR produjo:

```text
Mesa de Ayuda TI
El equipo no tiene conexion a la red
Error de red
```

Resultados observados:

```text
Motor OCR: easyocr
Idioma: es + en
Palabras: 15
Confianza OCR: 89.69
has_text: True
```

Contenido enviado al modelo:

```text
Solicitud escrita por el usuario:
La conexión presenta un problema según la captura.

Texto extraído de la imagen mediante OCR:
Mesa de Ayuda TI
El equipo no tiene conexion a la red
Error de red
```

Salida validada de la ejecución actual:

```json
{
  "categoria": "redes",
  "prioridad": "media",
  "resumen": "Equipo sin conexión a la red, error de red reportado.",
  "datos_faltantes": [
    "Nombre o modelo del equipo afectado",
    "Sistema operativo del equipo",
    "Tipo de conexión (Wi-Fi, Ethernet, VPN, etc.)",
    "Nombre de la red o SSID",
    "¿Otros dispositivos pueden conectarse a la red?",
    "¿Se ha intentado reiniciar el router o el equipo?"
  ],
  "requiere_humano": false,
  "confianza": 0.5
}
```

Estado final de esa ejecución:

```text
OK_PIDE_ACLARACION
```

Interpretación: el OCR cumplió la función de extraer evidencia visual; la información restante no era suficiente para establecer una causa concreta o una acción de resolución.

## 12. Métricas de la ejecución multimodal de referencia

En la ejecución de notebook utilizada para la evidencia de la presentación:

| Métrica | Resultado |
|---|---:|
| OCR | 5.4803 s |
| Modelo + validación + decisión | 1.4318 s |
| Recorrido multimodal total | 6.9121 s |
| Prompt tokens | 1195 |
| Completion tokens | 720 |
| Total tokens | 1915 |
| Llamadas Groq | 1 |

El tiempo de `modelo + validación + decisión` no incluye el OCR, porque el OCR se ejecuta antes de `run_case()`. El tiempo multimodal completo se obtiene sumando las etapas.

En esta ejecución el OCR concentra la mayor parte del tiempo observado. La explicación técnica es principalmente el costo de inferencia neuronal de EasyOCR ejecutado sobre CPU; la inicialización del lector y el procesamiento de metadatos también pueden contribuir. No se presenta ese valor como una propiedad universal de EasyOCR ni como una medición de throughput sostenido.

Las siguientes métricas no están disponibles de forma representativa en este corte:

```text
P95 / P99 de latencia: no disponible
Throughput / RPS: no disponible
Benchmark controlado por motor OCR: pendiente
```

## 13. Errores y comportamiento del sistema

### 13.1. Error técnico encontrado: import faltante

Una ejecución de una celda produjo:

```text
NameError: name 'tempfile' is not defined
```

La causa fue el uso de `tempfile.TemporaryDirectory()` sin importar el módulo.

Corrección:

```python
import tempfile
```

Estado: **corregido**.

### 13.2. Persistencia de la imagen multimodal

La primera implementación utilizaba un directorio temporal, lo que impedía conservar la imagen para el reporte después del bloque de ejecución.

Se cambió a una ruta persistente:

```text
docs/multimodal/multimodal_demo.png
```

Estado: **corregido**.

### 13.3. Orden de generación del PDF

Inicialmente el PDF se generaba antes de la prueba multimodal, por lo que el sexto caso no aparecía en el reporte.

Se corrigió el orden de ejecución para que la evidencia multimodal se registre antes de generar el consolidado.

Estado: **corregido**.

### 13.4. Error de validación controlable

La aplicación diferencia una respuesta estructuralmente inválida de una respuesta válida que simplemente requiere aclaración. El validador devuelve `False`, lista de errores y `validated=None` cuando `SolicitudTI.model_validate()` falla.

Estado: **implementado y disponible para pruebas controladas**.

## 14. Limitaciones actuales y mejoras pendientes

### Limitaciones evidenciadas

**1. Diagnóstico limitado por contexto de entrada.**

`OCR-001` permite identificar `redes`, pero termina en `OK_PIDE_ACLARACION` con confianza `0.5`. La captura no contiene por sí sola equipo, sistema operativo, tipo de conexión, SSID ni alcance del fallo.

**Mejora:** incorporar contexto estructurado adicional antes de intentar un diagnóstico concreto.

**2. Latencia del OCR en CPU.**

En la ejecución de referencia EasyOCR tardó 5.4803 s.

**Mejora:** reutilizar el lector, separar tiempos de inicialización/inferencia y realizar benchmark controlado de EasyOCR, Tesseract y PaddleOCR.

**3. El primer corte no ejecuta acciones sobre infraestructura.**

El sistema clasifica, valida y decide estado; no consulta todavía una base de conocimiento ni ejecuta comandos o acciones operativas.

**Mejora de siguientes cortes:** incorporar RAG y, posteriormente, herramientas/agentes con acciones controladas.

### Corrección ya aplicada

`case_03` reveló una condición concreta en `system_v3`: `datos_faltantes` podía quedar vacío para una solicitud insuficiente. `system_v4` incorporó una regla explícita para evitarlo.

Estado: **corregido**.

## 15. Decisiones técnicas vigentes

| Decisión | Estado / justificación |
|---|---|
| Groq | Mantener para integración por API y métricas de ejecución |
| `openai/gpt-oss-20b` | Mantener constante para comparabilidad del experimento |
| `temperature=0` | Mantener para mayor consistencia experimental |
| `max_completion_tokens=1500` | Mantener mientras se amplía la evidencia; revisar solo con nueva medición controlada |
| JSON estructurado | Mantener para facilitar procesamiento automático |
| Pydantic | Mantener como barrera programática del contrato |
| Prompt versionado | Mantener para trazabilidad de cambios |
| `raw_output` | Mantener para reconstruir la salida original antes de validar |
| OCR con Strategy + Factory | Mantener para poder intercambiar motores sin modificar el orquestador |
| PDF de trazabilidad | Mantener como evidencia consolidada |

## 16. Evidencias de la entrega actual

| Evidencia | Ubicación |
|---|---|
| Notebook | `notebooks/ti_support.ipynb` |
| Prompts | `prompts/system_v0.md` a `prompts/system_v4.md` |
| Prompt vigente | `prompts/system_v4.md` |
| Contrato | `schemas/request_v1.py` |
| Validación | `src/validator.py` |
| Multimodalidad | `src/multimodal.py` |
| OCR | `src/ocr/` |
| Cliente | `src/groq_client.py` |
| Casos | `cases/test_cases.json` |
| Resultados | `docs/results.json` |
| PDF consolidado actual | `docs/model_results_report(20260920-203211).pdf` |
| Imagen multimodal | `docs/multimodal/multimodal_demo.png` |
| Bitácora del parcial | `docs/bitacora_parcial_1.md` |
| Presentación | `TI_support_RAG_Parcial1_Diapositivas_01-15...pptx` |

## 17. Correspondencia con las evidencias del Parcial 1

| Elemento | Evidencia actual |
|---|---|
| Problema y usuario | Alcance y flujo de Mesa de Ayuda TI |
| Punto de entrada funcional | Notebook ejecutable |
| Modelo integrado | Groq + `openai/gpt-oss-20b` |
| Prompt versionado | `system_v0` → `system_v4` |
| Salida controlada | JSON + Pydantic + estados |
| Modalidad pertinente | OCR sobre imagen |
| Pruebas | `case_01` a `case_05` + `OCR-001` |
| Métricas | tokens, latencia y tiempos del recorrido |
| Errores | `NameError`, persistencia de imagen y orden de reporte; correcciones documentadas |
| Limitaciones | contexto diagnóstico, latencia OCR y ausencia de RAG/agentes |
| Bitácora | `docs/bitacora_parcial_1.md` |

## 18. Aprendizajes

- Una respuesta estructurada no es suficiente para demostrar que el contenido sea suficiente para diagnosticar.
- El programa debe controlar el formato y los rangos independientemente de la propuesta del modelo.
- El `raw_output` debe conservarse para trazabilidad.
- Las entradas ambiguas e incompletas necesitan reglas explícitas.
- Una prueba de prompt injection debe comprobar que no se expongan instrucciones internas o secretos.
- OCR debe evaluarse tanto por extracción como por la utilidad del contexto que entrega al modelo.
- Una métrica de latencia aislada describe una ejecución, no necesariamente el rendimiento sostenido del sistema.
- Los tiempos de mock no deben mezclarse con las métricas de la API real.
- Las limitaciones deben permanecer visibles y convertirse en acciones concretas de mejora.

## 19. Estado de cierre actualizado

### Completado

- [x] Problema y alcance
- [x] Punto de entrada funcional
- [x] Modelo integrado con Groq
- [x] Prompt versionado hasta `system_v4`
- [x] Contrato estructurado
- [x] Validación Pydantic
- [x] Estados de decisión
- [x] Manejo de solicitudes normales, ambiguas, incompletas, maliciosas y fuera de alcance
- [x] Manejo multimodal con OCR
- [x] Strategy + Factory para motores OCR
- [x] Métricas de tokens y latencia
- [x] Trazabilidad
- [x] Manejo y corrección de errores técnicos documentados
- [x] PDF consolidado
- [x] Presentación del Parcial 1 hasta la diapositiva 15
- [x] Bitácora actualizada

### Hallazgo corregido

- [x] `case_03`: regla reforzada en `system_v4` para evitar `datos_faltantes` vacío ante solicitudes insuficientes.

### Mejoras pendientes

- [ ] Benchmark controlado de motores OCR.
- [ ] Separación de inicialización e inferencia en las mediciones OCR.
- [ ] Métricas p95/p99 y throughput bajo carga.
- [ ] Integración RAG en el siguiente corte.
- [ ] Incorporación progresiva de herramientas/agentes para diagnóstico y acciones controladas.

## 20. Cierre

El Parcial 1 queda **cerrado para entrega y actualizado con la evolución posterior de la evidencia**. La implementación actual demuestra un flujo controlado en el que el modelo propone una estructura, el programa valida el contrato y la lógica determinista establece el estado del caso.

La principal corrección posterior al cierre inicial fue la evolución de `system_v3` a `system_v4` a partir del incumplimiento observado en `case_03`. La modalidad OCR quedó integrada y trazada desde la imagen de entrada hasta el texto enviado al modelo y la salida validada.

El sistema continúa deliberadamente limitado en dos dimensiones: profundidad de diagnóstico y capacidad de acción. RAG y agentes/herramientas quedan como evolución de los siguientes cortes, mientras que la optimización de OCR y la ampliación de las métricas de rendimiento permanecen como trabajo pendiente.

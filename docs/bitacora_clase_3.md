---
tipo: bitacora-clase
curso:
  - Electiva VI
periodo: EAM-2026II
equipo:
  - Mesa de Ayuda TI Inteligente
corte: 1
semana:
  - "3"
clase:
  - "3"
fecha: 2026-09-07
estado: finalizado
tags:
  - ai
  - bitacora
  - groq
  - prompt-engineering
  - pydantic
  - mesa-de-ayuda-ti
---

# Bitácora — Clase (3)

## 1. Datos de la sesión

| Campo | Registro |
|---|---|
| Tema | Diseño, validación y evaluación de prompts para una Mesa de Ayuda TI |
| Objetivo | Implementar y evaluar un flujo controlado donde el modelo genera una propuesta estructurada y el programa valida su salida mediante un contrato definido con Pydantic. |
| Proyecto | Mesa de Ayuda TI Inteligente |
| Modelo | `openai/gpt-oss-20b` |
| Motor de inferencia | API de Groq |
| Prompt evaluado | `system_v0` y `system_v1` |
| Casos de prueba | 5 |
| Estado | Ejecución realizada y resultados registrados |

## 2. Participación y responsabilidades

| Integrante | Asistió | Rol de la clase | Responsabilidad asumida | Aporte verificable |
|---|:---:|---|---|---|
| David Mantilla Aviles | Sí | Implementación y análisis | Configuración del entorno, ejecución del notebook, implementación de la integración con Groq y análisis de resultados | Notebook y resultados registrados |
| Juan Camilo Velez | Sí | Implementación y análisis | Adaptación del experimento al dominio de Mesa de Ayuda TI y revisión de los resultados | [Evidencia pendiente] |

## 3. Reto aplicado al proyecto

### Funcionalidad trabajada

Se implementó un flujo de evaluación para una **Mesa de Ayuda TI Inteligente**, donde el modelo de lenguaje recibe una solicitud del usuario y propone una clasificación estructurada.

La aplicación posteriormente procesa y valida la respuesta.

El flujo implementado es:

1. Cargar la versión del prompt.
2. Cargar los cinco casos de prueba.
3. Enviar la solicitud a Groq utilizando `openai/gpt-oss-20b`.
4. Recibir y conservar la salida original del modelo.
5. Convertir la respuesta JSON en datos utilizables por Python.
6. Validar la salida mediante el schema `SolicitudTI` de Pydantic.
7. Registrar errores de formato o errores técnicos.
8. Determinar una decisión para cada caso.
9. Registrar la latencia y el uso de tokens.
10. Conservar los resultados de la ejecución en `docs/results.json`.

### Contrato implementado

El schema `SolicitudTI` define los siguientes campos:

- `categoria`
- `prioridad`
- `resumen`
- `datos_faltantes`
- `requiere_humano`
- `confianza`

Además define los tipos y valores permitidos para los campos principales.

### Criterios de aceptación

- [x] El modelo puede ser invocado mediante la API de Groq.
- [x] Se utiliza el modelo `openai/gpt-oss-20b`.
- [x] El prompt se mantiene como un archivo versionado.
- [x] Se ejecutan cinco casos de prueba.
- [x] La respuesta original del modelo se conserva como `raw_output`.
- [x] La respuesta puede ser convertida a JSON.
- [x] La respuesta se valida mediante Pydantic.
- [x] Se registran errores de validación.
- [x] Se registran errores técnicos.
- [x] Se registra la latencia.
- [x] Se registran los tokens utilizados.
- [x] Se conserva un historial de ejecuciones en `results.json`.
- [x] Se compararon `system_v0` y `system_v1`.
- [ ] Resolver completamente los casos ambiguo e incompleto.
- [ ] Incorporar una validación más completa de las reglas de negocio.

## 4. Decisiones técnicas

| Decisión | Razón | Alternativa descartada |
|---|---|---|
| Utilizar Groq como motor de inferencia | Permite ejecutar el modelo mediante una API y registrar métricas de la interacción. | Ejecutar el modelo completamente de forma local. |
| Utilizar `openai/gpt-oss-20b` | Se mantuvo el mismo modelo para comparar las versiones del prompt bajo condiciones equivalentes. | Cambiar de modelo durante la comparación. |
| Mantener `temperature=0` | Busca favorecer la consistencia de las pruebas y facilitar la comparación entre versiones. | Utilizar una temperatura mayor para aumentar la variabilidad. |
| Mantener `max_tokens=500` | El formato requerido produce respuestas cortas y las salidas observadas no alcanzan este límite. | Incrementar el límite sin evidencia de que sea necesario. |
| Utilizar JSON como formato de salida | Permite procesar y validar la respuesta de manera estructurada. | Analizar texto libre. |
| Utilizar Pydantic | Permite validar campos, tipos y valores definidos en el contrato. | Confiar únicamente en la respuesta generada por el modelo. |
| Mantener `raw_output` | Permite conservar la respuesta original antes de ser procesada o validada. | Guardar únicamente el resultado final. |
| Versionar los prompts | Permite comparar cambios en el comportamiento del modelo sin perder la versión anterior. | Sobrescribir el prompt anterior. |

## 5. Problemas y soluciones

| Problema encontrado | Causa identificada | Solución aplicada | ¿Cómo se verificó? |
|---|---|---|---|
| `system_v0` producía campos como `category`, `priority` y `summary` en lugar de los nombres definidos por el contrato | El modelo no seguía el esquema esperado por la aplicación | Se creó `system_v1` con reglas más explícitas sobre los nombres y tipos de los campos | Comparación de las ejecuciones de `system_v0` y `system_v1` |
| Varias respuestas de `system_v0` fueron rechazadas por Pydantic | La estructura generada no coincidía con `SolicitudTI` | Se reforzó el contrato en `system_v1` | `system_v1` consiguió salidas validadas en los casos 01, 04 y 05 |
| Los casos ambiguo e incompleto no generan actualmente una salida JSON utilizable | El modelo presenta errores de generación JSON ante entradas muy cortas o insuficientes | Se identificó como limitación pendiente | `case_02` y `case_03` terminaron en `ERROR_TECNICO` |
| Se observaron latencias elevadas en algunos casos | La ejecución mediante la API presentó tiempos de respuesta variables | Se registró la latencia para poder analizarla | Se registraron aproximadamente 19.5 s y 19.8 s en los casos 04 y 05 de `system_v1` |
| La respuesta debe mantener una estructura controlada | Una respuesta correcta en contenido no es suficiente si no cumple el contrato | Se incorporó validación mediante Pydantic | El notebook registra `OK_VALIDADO` o `ERROR_FORMATO` |

## 6. Resultados del experimento

### `system_v0`

Los cinco casos fueron ejecutados.

Resultado general:

- 0/5 casos validados.
- 4 casos terminaron en `ERROR_FORMATO`.
- 1 caso terminó en `ERROR_TECNICO`.

El principal problema observado fue la incompatibilidad entre los nombres de campos generados por el modelo y los definidos en el contrato.

### `system_v1`

Los cinco casos fueron ejecutados.

Resultado general:

- 3/5 casos validados.
- 2 casos terminaron en `ERROR_TECNICO`.
- 0 casos terminaron en `ERROR_FORMATO`.

Los casos validados fueron:

- `case_01` — normal.
- `case_04` — malicioso.
- `case_05` — fuera de alcance.

Los casos que continúan presentando problemas son:

- `case_02` — ambiguo.
- `case_03` — incompleto.

## 7. Evidencias

| Tipo | Descripción | Enlace o ruta |
|---|---|---|
| Código | Notebook con la implementación del experimento | `notebooks/ti_support.ipynb` |
| Prompt | Versión inicial del prompt | `prompts/system_v0.md` |
| Prompt | Primera mejora del prompt | `prompts/system_v1.md` |
| Schema | Contrato `SolicitudTI` | `schemas/request_v1.py` |
| Pruebas | Cinco casos de prueba | `test/test_cases.json` |
| Resultados | Historial de ejecuciones | `docs/results.json` |
| Diagrama | Diagrama de actividades | `assets/diagrama_actividades_flujo_trabajo(1).svg` |

## 8. Uso de inteligencia artificial

| Herramienta | Objetivo o pregunta | Qué se utilizó | Cómo se verificó | Qué se modificó |
|---|---|---|---|---|
| Groq / `openai/gpt-oss-20b` | Generar una clasificación estructurada de solicitudes de soporte TI | Generación de JSON con las categorías y campos definidos por el proyecto | Validación mediante Python y Pydantic | Se compararon dos versiones del prompt |
| Inteligencia artificial generativa | Analizar y mejorar el diseño del prompt y el flujo experimental | Propuestas para estructurar instrucciones, validación y manejo de casos | Comparación con los resultados obtenidos en las pruebas | Se conservaron las decisiones implementadas y se registraron las limitaciones |

## 9. Defensa técnica y retroalimentación

| Campo | Registro |
|---|---|
| Integrante que defendió | [Pendiente de registrar] |
| Pregunta recibida | [Pendiente de registrar] |
| Respuesta resumida | [Pendiente de registrar] |
| Retroalimentación docente | [Pendiente de registrar] |
| Mejora acordada | Analizar los errores de los casos ambiguo e incompleto y fortalecer el comportamiento del prompt antes de crear una nueva versión. |

## 10. Aprendizajes

- **Concepto comprendido:** El modelo de lenguaje no debe tener el control sobre la validez final de su propia respuesta. Puede proponer una clasificación, pero el programa debe comprobar la estructura y las reglas.

- **Concepto comprendido:** Una respuesta del modelo puede ser aparentemente correcta pero incumplir el contrato esperado por la aplicación.

- **Concepto comprendido:** El `raw_output` permite conservar la respuesta original del modelo antes de realizar el procesamiento y la validación.

- **Concepto comprendido:** Pydantic permite convertir el contrato del sistema en una comprobación programática y detectar errores de estructura y tipos.

- **Concepto comprendido:** La comparación entre versiones del prompt permite observar cambios reales en el comportamiento del modelo.

- **Concepto comprendido:** Una mejora del prompt no necesariamente resuelve todos los casos. En `system_v1` mejoró la adherencia al contrato, pero los casos ambiguo e incompleto continúan presentando errores técnicos.

- **Algo que aún genera duda:** Determinar por qué el modelo presenta errores de generación JSON específicamente ante determinadas entradas ambiguas o incompletas.

- **Qué haríamos diferente:** Definir con mayor precisión el comportamiento esperado para entradas ambiguas e incompletas y realizar una nueva ejecución controlada antes de modificar otras variables del experimento.

## 11. Revisión antes de entregar

- [x] Se registró la implementación del experimento.
- [x] Se registraron los cinco casos de prueba.
- [x] Se utilizó un prompt versionado.
- [x] Se utilizó validación mediante Pydantic.
- [x] Se registraron las respuestas del modelo.
- [x] Se registraron errores técnicos y de formato.
- [x] Se registraron tokens y latencia.
- [x] Se conservaron las ejecuciones anteriores.
- [x] Se compararon `system_v0` y `system_v1`.
- [ ] Registrar la retroalimentación docente.
- [ ] Resolver los casos ambiguo e incompleto.
- [ ] Definir las siguientes reglas de negocio del sistema.

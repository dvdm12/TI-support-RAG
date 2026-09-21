# TI-support-RAG

Prototipo académico de una Mesa de Ayuda TI con IA generativa, validación estructural y trazabilidad.

> **Principio:** el modelo propone; el programa comprueba; el sistema decide.

## Estado del proyecto

| Elemento | Estado actual |
|---|---|
| Curso | Electiva VI · EAM-2026II |
| Corte | Parcial 1 |
| Modelo | `openai/gpt-oss-20b` |
| Proveedor | Groq |
| Prompt vigente | `system_v4` |
| Modalidad | Texto + OCR |
| Punto de entrada | `notebooks/ti_support.ipynb` |
| Contrato | `schemas/request_v1.py` |
| Validación | Pydantic |
| Resultados | `docs/results.json` |
| Evidencia | `docs/model_results_report.pdf` |
| Bitácora | `docs/bitacora_parcial.md` |

## Flujo de trabajo

![Diagrama de actividades — TI-support-RAG](assets/flujo_trabajo.png)

**Ruta:** `assets/flujo_trabajo.png`

## Diagrama de componentes

![Diagrama de componentes — TI-support-RAG](assets/diagrama_componentes_ti_support.jpeg)

**Ruta:** `assets/diagrama_componentes_ti_support.jpeg`

## Ejecución en Google Colab

| Paso | Qué hacer |
|---|---|
| 1 | Abrir `notebooks/ti_support.ipynb` en Google Colab. |
| 2 | Clonar el repositorio y entrar a `/content/TI-support-RAG`. |
| 3 | Instalar dependencias con `!pip install -r requirements.txt`. |
| 4 | En **Colab → Secrets**, crear el secreto `GROQ_API_KEY` con una clave propia de Groq. |
| 5 | Cargar el secreto en el entorno. |
| 6 | Ejecutar las celdas del notebook en orden. |
| 7 | Para una nueva solicitud, ir a **14. Defensa manual (opcional)**. |
| 8 | Cambiar `ENABLE_MANUAL_DEFENSE = False` a `True`. |
| 9 | Ejecutar esa celda. |
| 10 | Escribir la solicitud cuando aparezca `Solicitud:`. |

### 1. Abrir el notebook

Archivo:

```text
notebooks/ti_support.ipynb
```

En Colab se puede abrir el notebook después de clonar el repositorio o cargarlo directamente desde la carpeta del proyecto.

### 2. Preparar el proyecto

Ejecutar en una celda:

```python
!git clone https://github.com/dvdm12/TI-support-RAG.git
%cd /content/TI-support-RAG
```

La carpeta de trabajo debe ser la raíz del proyecto, donde están `src/`, `prompts/`, `schemas/`, `cases/` y `docs/`.

### 3. Instalar dependencias

```python
!pip install -r requirements.txt
```

### 4. Configurar la clave de Groq

Al clonar el proyecto, **lo único que debe aportar el revisor es su propia clave de Groq**.

Para una ejecución local, crear en la raíz del proyecto un archivo `.env`:

```text
GROQ_API_KEY=tu_clave_de_groq
```

El archivo `.env` es local y no debe subirse al repositorio.

En Google Colab también puede usarse **Colab → Secrets** con el nombre:

```text
GROQ_API_KEY
```

y cargarlo así:

```python
import os
from google.colab import userdata

os.environ["GROQ_API_KEY"] = userdata.get("GROQ_API_KEY")
```

Usar siempre una **clave propia del revisor**. No copiar la clave privada del equipo.

### 5. Ejecutar el notebook

Ejecutar las celdas en orden.

El notebook prepara la configuración, carga los casos, ejecuta las consultas contra Groq, valida las respuestas con Pydantic y registra resultados y métricas.

### 6. Ingresar una solicitud nueva

La entrada manual está en:

```text
14. Defensa manual (opcional)
```

La celda contiene:

```python
ENABLE_MANUAL_DEFENSE = False
```

Cambiar a:

```python
ENABLE_MANUAL_DEFENSE = True
```

y ejecutar la celda.

El notebook solicitará:

```text
Número de ejecuciones de defensa:
Solicitud:
```

Escribir la solicitud directamente después de `Solicitud:`.

También puede seleccionarse una imagen opcional para ejecutar el flujo multimodal.

Las ejecuciones manuales se identifican como:

```text
DEF-001
DEF-002
DEF-003
...
```

y se incorporan a la evidencia generada.

### 7. Revisar el resultado

| Evidencia | Ubicación |
|---|---|
| Resultado estructurado | salida de la celda de defensa |
| Resultados persistidos | `docs/results.json` |
| PDF consolidado | `docs/model_results_report.pdf` |
| Casos reproducibles | `cases/test_cases.json` |
| Imagen multimodal | `docs/multimodal/multimodal_demo.png` |

> **Credencial:** para ejecutar nuevas consultas solo se necesita una `GROQ_API_KEY` válida. No se requiere ninguna otra credencial del proyecto.

## ¿Dónde ingreso una solicitud?

| Uso | Ubicación |
|---|---|
| Casos reproducibles | `cases/test_cases.json` |
| Consulta manual | Celda **14. Defensa manual (opcional)** |
| Variable de activación | `ENABLE_MANUAL_DEFENSE = True` |
| Campo de entrada | `Solicitud:` |
| Imagen opcional | Selección desde la misma defensa manual |
| Evidencia generada | `docs/results.json` y PDF |

## Casos de prueba

| Caso | Tipo | Propósito |
|---|---|---|
| `case_01` | Normal | Clasificación clara |
| `case_02` | Ambiguo | Evitar asumir el sistema afectado |
| `case_03` | Incompleto | Solicitar información faltante |
| `case_04` | Malicioso | Resistir prompt injection y proteger secretos |
| `case_05` | Fuera de alcance | Mantener el límite de la Mesa de Ayuda TI |
| `OCR-001` | Multimodal | Imagen → OCR → modelo → validación |

## Componentes y evidencias

| Área | Archivo / carpeta | Función |
|---|---|---|
| Notebook | `notebooks/ti_support.ipynb` | Ejecución experimental y defensa |
| Configuración | `src/config.py` | Modelo, prompt, rutas y credencial |
| Integración Groq | `src/groq_client.py` | Llamada a la API y métricas |
| Orquestación | `src/pipeline.py` | Flujo principal |
| Validación | `src/validator.py` | Validación de salida |
| Multimodalidad | `src/multimodal.py` | Preparación texto + OCR |
| OCR | `src/ocr/` | Estrategias OCR |
| Contrato | `schemas/request_v1.py` | `SolicitudTI` |
| Casos | `cases/test_cases.json` | Casos de prueba |
| Prompts | `prompts/system_v0.md` … `system_v4.md` | Versionado |
| Evaluación | `evaluation.py` | Evaluación funcional |
| Resultados | `docs/results.json` | Registro estructurado |
| PDF | `docs/model_results_report.pdf` | Evidencia consolidada |
| Imagen | `docs/multimodal/multimodal_demo.png` | Evidencia multimodal |
| Bitácora | `docs/bitacora_parcial.md` | Decisiones, errores y estado |
| Flujo | `assets/flujo_trabajo.png` | Diagrama de actividades |
| Componentes | `assets/diagrama_componentes_ti_support.jpeg` | Diagrama de componentes |

## Estados del sistema

| Estado | Significado |
|---|---|
| `OK_VALIDADO` | Salida válida y suficiente según las reglas |
| `OK_PIDE_ACLARACION` | Salida válida, pero falta información |
| `OK_REQUIERE_HUMANO` | El caso debe pasar a intervención humana |
| `ERROR_TECNICO` | Fallo de consulta o generación |
| `ERROR_FORMATO` | La salida no cumple el contrato |

## Multimodalidad

| Etapa | Resultado |
|---|---|
| Imagen | `docs/multimodal/multimodal_demo.png` |
| OCR | Extracción de texto |
| Validación | Verificación de archivo y contenido |
| Contexto | Texto del usuario + texto OCR |
| Modelo | `openai/gpt-oss-20b` |
| Salida | JSON validado por Pydantic |

## Trazabilidad

Cada ejecución puede conservar:

| Dato | Registro |
|---|---|
| Entrada | Solicitud del usuario |
| Salida original | `raw_output` |
| Validación | `validated_output` / errores |
| Decisión | Estado final |
| Métricas | Latencia y tokens |
| Multimodalidad | Texto OCR y metadatos |
| Persistencia | `docs/results.json` + PDF |

## Mocks

Los mocks de `src/mocks.py` sirven para probar comportamiento controlado del programa **sin llamar a Groq**.

> Sus tiempos no deben utilizarse como rendimiento real del modelo.

## Alcance

| Incluido en este corte | Para siguientes cortes |
|---|---|
| Clasificación | RAG completo |
| Prompt versionado | Recuperación documental |
| JSON estructurado | Agentes / herramientas |
| Validación Pydantic | Ejecución de acciones |
| Estados de decisión | Diagnóstico asistido con conocimiento externo |
| OCR multimodal | — |
| Métricas y trazabilidad | — |

## Revisión rápida

### Solo revisar la evidencia

1. Abrir `README.md`.
2. Revisar `notebooks/ti_support.ipynb`.
3. Consultar `cases/test_cases.json`.
4. Revisar `prompts/` y `schemas/`.
5. Consultar `docs/results.json` y `docs/model_results_report.pdf`.
6. Revisar `docs/bitacora_parcial.md`.

### Ejecutar una nueva consulta

| Requisito | Valor |
|---|---|
| Entorno | Google Colab |
| Dependencias | `requirements.txt` |
| Credencial | `GROQ_API_KEY` propia del revisor |
| Notebook | `notebooks/ti_support.ipynb` |
| Entrada | Celda 14 · Defensa manual |
| Activación | `ENABLE_MANUAL_DEFENSE = True` |

> La evidencia ya generada puede revisarse sin una nueva llamada a Groq. La API key solo es necesaria para ejecutar nuevas consultas.

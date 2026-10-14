# Comprobación de clase 08 — 14 de octubre de 2026

**Resultado: cumplimiento parcial.** El recorrido técnico funciona, pero el
caso ambiguo incumple el comportamiento esperado y faltan tiempos por etapa y
la justificación semántica definitiva de la fragmentación.

Se ejecutaron las diez celdas de código con el kernel `ti-support-rag`, Supabase
y Groq reales. Se activaron las cinco pruebas opcionales en una copia ejecutada;
el notebook fuente conserva `EJECUTAR_PRUEBAS=False`, como en el ejemplo docente.
No hubo bloqueos de cuota ni errores de celda. El upsert mantuvo 70 fragmentos
con los mismos textos e identidades y la segunda sesión del mismo usuario
recuperó los mismos IDs, textos y puntajes.

## Métricas observadas

| Comprobación | Resultado |
|---|---|
| Consultas reales | 6 de 6 ejecutadas |
| Contratos y citas válidos | 6 de 6 |
| Estados esperados en pruebas adicionales | 3 de 5 coincidentes |
| Entrada informada por Groq | 717–736 tokens; media 726,5 |
| Límite local de entrada | 1000 tokens; respetado en las seis llamadas |
| Consumo total informado | 5334 tokens, incluyendo salida |
| Latencia de llamada de generación | 0,60–1,29 s; media 0,84 s |
| Ejecución del notebook | 16,68 s en este entorno y sesión |
| Filas persistidas verificadas | 70 |
| Persistencia desde otro cliente | Correcta, con el mismo usuario |
| Secretos encontrados en evidencia/notebook ejecutado | Ninguno de los valores sensibles locales comprobados |

Son medidas de seis consultas, no una estimación de exactitud universal ni un
benchmark de carga. El material revisado de clase 08 no fija una nota mínima,
un porcentaje obligatorio de aciertos ni un umbral de latencia. Las expectativas
de los casos sí están escritas antes de ejecutarlos.

## Casos y revisión documental

| Caso | Estado observado | Evaluación |
|---|---|---|
| Consulta inicial 403 | `parcial` | Niega suspensión con ACS-03; también añade rutas de otros síntomas documentadas pero no solicitadas. |
| Paráfrasis de 403 | `parcial` | Conserva la regla y no afirma suspensión; difiere del estado `respondida` esperado. |
| «¿Cómo lo hago?» | `respondida` | **Falla:** ofrece acceso/recuperación de contraseña sin pedir qué quiere hacer el usuario. |
| Requisitos de beca | `evidencia_insuficiente` | Reconoce falta de información en los pasajes sin inventar requisitos. |
| Estado actual de TI-123 | `evidencia_insuficiente` | No inventa el estado actual ni simula consultar un sistema de tickets. |
| Error 403 | `respondida` | Conserva la regla de ACS-03; añade desactivación y ataque como temas adicionales presentes en las fuentes. |

La consulta ambigua obtuvo etiquetas válidas, pero eso no justifica elegir un
procedimiento específico para una pregunta que no identifica la tarea. El estado
observado tampoco coincide con `aclaracion`. La paráfrasis tiene respaldo y un
límite prudente, por lo que su diferencia de estado se distingue del fallo de
comportamiento del caso ambiguo. La revisión registrada fue del agente de
implementación, no una revisión humana ni un juez semántico independiente.

## Aspectos pendientes frente al material

- Desambiguación: pedir la información que cambia el procedimiento antes de
  recomendar pasos concretos. No considerar una cita válida como suficiencia.
- Trazabilidad de tiempos: se registra generación y tiempo total del cliente,
  pero no se separan embedding, RPC, contexto y validación. La consulta inicial
  reutiliza candidatos del punto 6, cuya recuperación no está incluida en el
  total medido del punto 8.
- Fragmentación: hay comparación reproducible en `docs/rag_comparison.json`,
  pero la elección final de `sections` conserva revisión semántica pendiente.
- Como control adicional del proyecto, 5 de 6 salidas respetaron simultáneamente
  las longitudes pedidas en el prompt (90 palabras de respuesta y 25 de
  limitación). Ese límite de palabras no es un umbral de la práctica docente.
- Revisión humana de fuentes y prueba entre dos usuarios Auth distintos siguen
  pendientes. La práctica de persistencia realizada usa el mismo propietario.

## Evidencia

Sesión: `docs/rag_runs/clase08/20261014T203144285329Z/`.
Incluye `clase_08_ejecutado.ipynb`, las seis consultas, carga, persistencia,
`Clase_08_Evidencia_RAG.json`, `metricas_clase08.json` y `bitacora.json`.
Las trazas permanecen fuera de Git; el resumen revisable es
`docs/class08_metrics.json`, y la ejecución está en
`docs/class08_metrics_execution.json`.

Fuentes de los criterios: `parcial2/Clase_08_RevealJS/index.html`, apartados de
trazabilidad, avance y pruebas (líneas 445–485), y puntos 9–10 del notebook
docente `Clase_08_Demo_Colab_RAG_Supabase_Groq.ipynb`. No se infiere una rúbrica
oficial adicional ni se presenta esta comprobación como calificación del corte.

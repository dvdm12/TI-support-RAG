# Ficha de revisión humana — T1

`class09_review_v1.json` es la ficha principal; `.csv` contiene las mismas 27
filas (una por caso y variante), con objetos/listas serializados como JSON en
las celdas. Ambos conservan respuestas y pasajes completos, sin truncamiento.
No son métricas ni acreditan revisión humana. No se generaron nuevas respuestas.

## Alcance

- 14 respuestas del 21-10: siete pares `A_semantic` / `B_hybrid_rrf`, generación
  directa con `rag_v6`. B usa las selecciones híbridas mejoradas guardadas.
- 13 respuestas del 25-10: `API_system_v8`, pipeline completo. Esta ejecución
  no es una tercera alternativa del experimento controlado A/B.
- Los casos son desarrollo conocido; no se abrió la reserva. E11 menciona una
  Ricoh en la pregunta histórica de aclaración, pero no usa el manual Ricoh como corpus.

Cada fila incluye pregunta, objeto de respuesta completo (estado, texto, citas y
limitación), pasajes citados completos, unidades esperadas, condiciones y criterios
de fallo. Las referencias de política de los casos de comportamiento aparecen
separadas de la evidencia documental. Las expectativas son anotaciones del agente,
pendientes de revisión humana; `agent_draft` no contiene veredictos humanos.

Los pasajes API se resolvieron mediante sus `chunk_id` en el índice congelado cuyo
hash se comprobó. No representan todos los candidatos ni el contexto API completo.
La ficha registra rutas, localizadores y hashes de las cuatro entradas. La traza
HTTP original es local e ignorada por Git; la ficha es autocontenida para revisar.

## Cómo completar T2

1. Revisar la respuesta contra los pasajes, las unidades y las condiciones.
   Completar `human_review`: `correccion`, `fidelidad`, `respaldo`, `utilidad`
   con booleanos, más `justificacion`, `revisor` y `fecha` ISO (AAAA-MM-DD).
   `null` significa pendiente, nunca falso. La rúbrica está en `protocol.rubric`.
2. Segmentar las afirmaciones documentales en `claims`, con `text`, `supported`,
   `citation_covered`, `labels` y `justification`. Una cita existente no demuestra
   que respalde la afirmación. Las aclaraciones no son afirmaciones documentales.
   Completar `unit_reviews` indicando cobertura y justificación por unidad.
3. Elegir al menos tres casos para dos integrantes independientes. Copiar la ficha
   para cada persona antes de revisar; volcar sus decisiones en los dos espacios
   `independent_reviews`, conservando ambas. Resolver discrepancias en `adjudication`
   y registrar el resultado final en `human_review`, sin borrar los juicios iniciales.
4. Cambiar el estado global a `in_progress` al comenzar. No marcar `completed`
   hasta terminar la revisión y resolver discrepancias. Guardar el JSON principal;
   si se edita CSV, trasladar los cambios al JSON para evitar versiones divergentes.

No usar las evaluaciones automáticas como sustituto del equipo. Errores técnicos
se conservan en `technical_error`, separados de la falta de evidencia.

## Preparación y validación offline

Desde `backend`, sin Groq ni Supabase:

```sh
../.venv/bin/python -m scripts.prepare_class09_review --output /tmp/class09_review_copy.json
../.venv/bin/python -m unittest test.test_class09_review
```

El preparador necesita las cuatro entradas originales y rechaza sobrescribir una
ficha existente para proteger las decisiones humanas. El esquema está en
`schemas/human_review_v1.py`; las pruebas verifican población, pasajes, copia exacta
de respuestas, campos pendientes, booleanos estrictos y exportación sin pérdidas.
En otro clon se omite únicamente la reconstrucción que requiere la traza HTTP local.

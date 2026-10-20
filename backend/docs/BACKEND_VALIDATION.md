# Validación del backend y aclaraciones

La API conserva el corpus académico de 70 fragmentos. El manual Ricoh no está
integrado: las consultas que mencionan ese modelo usan soporte general.

## Comportamiento corregido

- Un incidente vago no se convierte en un síntoma confirmado. «Problemas al
  enviar impresiones» conserva esa formulación y solicita qué ocurre y el mensaje
  visible, si existe. Tener marca/modelo no describe el fallo.
- Para patrones de incidentes vagos reconocidos, la política local construye la
  aclaración desde `datos_faltantes`, sin generar un diagnóstico ni llamar al
  generador/revisor documental. La clasificación y recuperación siguen siendo reales.
- Las preguntas documentales claras no requieren detalles para diagnosticar un
  incidente. Los datos faltantes se conservan al compactar el contexto.
- Instalar sin privilegios requiere soporte aunque el clasificador elija acceso.
  Ante riesgo físico presente se excluyen comprobaciones ordinarias de alimentación.

## Criterios de evaluación

La suite `cases/rag_regression.json` contiene 13 consultas: las diez originales,
un incidente de impresión ambiguo, una consulta general de impresoras y un
incidente de software ambiguo. Las expectativas documentales originales se
conservan. Se agregan comprobaciones de datos faltantes, estado final y fidelidad
del resumen para los nuevos casos y el caso ambiguo original.

`MODEL_SUPPORTED` indica revisión de respaldo del modelo, que sigue siendo
falible. `LOCAL_CLARIFICATION` identifica preguntas construidas por la política
local, sin afirmaciones técnicas que necesiten citas. Para los casos que admiten
`evidencia_insuficiente`, la suite también admite el reemplazo local fijo de una
respuesta rechazada: debe ser exactamente la abstención prevista, sin citas.
Ese reemplazo no aprueba el texto rechazado ni demuestra que el modelo respondió
correctamente. Las consultas que exigen un procedimiento respaldado no pueden
aprobar mediante esa abstención. Cada resultado informa el tipo de revisión y si
se utilizó el reemplazo seguro.

El informe `backend_validation.json` recoge resultados y versiones. Las trazas
completas, incluidas salidas rechazadas, quedan en `docs/rag_runs/` (ignorado).

## Reproducir

Desde `backend/`, con las dependencias instaladas y `.env` configurado:

```sh
../.venv/bin/python -m unittest discover -s test -q
../.venv/bin/python manage.py test api --verbosity 0
../.venv/bin/python -m scripts.validate_rag_scenarios --output docs/rag_runs/validation
```

La última orden usa Supabase y Groq reales y consume cuota. Se detiene si recibe
un bloqueo de cuota fuera del presupuesto de reintentos.

Las reglas de lenguaje son conservadoras y no cubren todas las formulaciones.
Esta suite es una regresión pequeña: aprobarla no garantiza exactitud ante toda
pregunta ni sustituye revisar la evidencia de nuevas respuestas.

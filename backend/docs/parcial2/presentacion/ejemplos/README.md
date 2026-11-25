# Ejemplo del recorrido RAG

`ejemplo_rag_wifi.json` respalda las diapositivas 30–33.

- La pregunta, clasificación, candidatos, respuesta y tokens proceden de la consulta guardada del panel del 25 de octubre de 2026.
- El embedding completo de 384 dimensiones se recalculó localmente con la revisión del modelo fijada en el índice. No estaba almacenado en la traza original.
- Los rankings semánticos, BM25 y RRF se reconstruyeron con el índice local. Se verificaron los mismos IDs seleccionados y similitudes coseno con tolerancia de 1e-5.
- La reconstrucción no hizo llamadas a Groq o Supabase ni modificó el corpus. No constituye una nueva evaluación de calidad de respuesta.

La diapositiva 34 reutiliza las respuestas guardadas de E08 y E09, variante `API_system_v8`, de `backend/docs/human_review/class09_review_v1.json`.

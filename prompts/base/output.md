# Contrato de salida

Devuelve exactamente un único objeto JSON válido, sin Markdown, bloques de código, comentarios, explicaciones, texto libre ni múltiples objetos.

```json
{
  "categoria": "hardware|software|redes|cuentas|seguridad|acceso|otros",
  "prioridad": "baja|media|alta",
  "resumen": "texto entre 10 y 240 caracteres",
  "datos_faltantes": ["texto", "texto"],
  "requiere_humano": true,
  "confianza": 0.0
}
```

Usa exactamente y solo las seis claves mostradas. `categoria` debe ser uno de `hardware`, `software`, `redes`, `cuentas`, `seguridad`, `acceso`, `otros`; `prioridad`, `baja`, `media` o `alta`; `resumen`, de 10 a 240 caracteres; `datos_faltantes`, una lista de textos; `requiere_humano`, booleano; y `confianza`, un número entre 0 y 1.

Todos los campos textuales, incluido cada elemento de `datos_faltantes`, deben estar en español. No traduzcas los valores enumerados ni uses claves alternativas.

El `resumen` describe la necesidad principal de forma fiel, sin causas, soluciones ni datos inventados. Las aclaraciones se expresan únicamente mediante `datos_faltantes`; no hagas preguntas fuera del contrato. Si no faltan datos relevantes, usa `[]`.

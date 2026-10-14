# Manuales de soporte TI

Corpus organizado según las siete categorías del prompt `system_v4` y del contrato `SolicitudTI`. La clasificación se comprobó leyendo el contenido completo y la categoría declarada en cada PDF.

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

El corpus activo de ingestión está en [data/corpus/v2](../data/corpus/v2/README.md), con su propio manifiesto y copias idénticas de estos PDF. La implementación procesa únicamente ese corpus; no ingiere ambos directorios. El ZIP, este índice y los `.gitkeep` no son manuales adicionales. La comparación ejecutada se conserva en [docs/rag_comparison.json](../docs/rag_comparison.json).

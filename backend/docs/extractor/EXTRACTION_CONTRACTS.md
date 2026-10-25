# Contratos del extractor PDF externo — paso 2

Los contratos Pydantic de `src/rag/extraction_contracts.py` describen y validan
la extracción externa **schema_version=1**. No sustituyen los contratos del
corpus académico, de sus fragmentos ni de la API.

| Contrato | Datos y controles |
|---|---|
| DocumentSource | ID, ruta, SHA-256, versión, idioma, páginas, tamaño, condición no simulada y perfil. Conserva metadatos adicionales de origen, equipo y procedencia. |
| ExtractionProfile | Parser, rango de contenido, exclusiones motivadas, ajustes geométricos y correcciones de tablas. Admite ajustes adicionales específicos del documento. |
| ExtractedPage / ExcludedPage | Unión por status. Una página extraída requiere numeración impresa y auditoría; una excluida exige motivo registrado. |
| Paragraph | Texto no vacío, ID, página PDF/impresa y coordenadas finitas ordenadas. |
| Table / TableRow | Encabezados, celdas originales, números e IDs de filas, coordenadas y referencias de continuación. Comprueba dimensiones de la cuadrícula y contención de filas. |
| ExtractionSection | Título, jerarquía, antecesores, inicio, bloques y páginas. Permite marcadores estructurales sin contenido propio. |
| ExcludedLayoutText | Texto retirado del diseño, página y motivo. |
| ExtractionResult | Documento completo: versión, perfil consistente, páginas contabilizadas, IDs únicos, referencias y auditoría de tablas coherentes. |
| FigureReference | Referencia independiente a una figura con procedencia y estado not_performed. No interpreta dibujos ni se admite como bloque del formato v1. |
| ExtractionDiagnostic | Código, severidad info/review/error, mensaje, documento y localización opcional. Contrato separado para integración posterior. |

## Compatibilidad y uso

```python
from src.rag.extraction_contracts import validate_extraction

validated = validate_extraction(payload)
# Usar validated para acceso tipado; conservar payload para serializar v1.
```

Los tipos son estrictos: números en cadenas no se convierten, campos de registros
desconocidos se rechazan y coordenadas NaN/inf o invertidas fallan. Documento y
perfil conservan extensiones de metadatos explícitamente; los ajustes propios
de la biblioteca dentro de settings no tienen aquí una interpretación nueva.

`extract_real_document()` valida el resultado completo antes de devolverlo.
Devuelve el **diccionario original**, no model_dump(): se mantienen el orden de
campos, números, metadatos y omisión de campos opcionales. No se añade diagnostics
ni una lista ficticia de figuras al JSON. Las celdas None de tablas ambiguas
permanecen intactas y requieren indicadores de revisión y elegibilidad textual falsa.

Los antecesores deben corresponder a la jerarquía, los bloques a páginas extraídas
con numeración consistente y las continuaciones a tablas previas compatibles en
la misma sección. No se fusionan filas ni se corrigen datos automáticamente.

Las figuras y diagnósticos tienen contratos utilizables por futuras etapas, pero
todavía no se generan automáticamente ni se envían al fragmentador. El resultado
v1 solo admite los dos tipos que sus consumidores ya soportan: párrafos y tablas.
Cambiar ese conjunto requerirá versionar o adaptar explícitamente el formato.

## Validación y límites

```sh
# Desde backend, entorno de la raíz:
../.venv/bin/python -m unittest test.test_extraction_contracts test.test_extraction_baseline test.test_external_ingestion test.test_external_chunking
../.venv/bin/python -m scripts.check_extraction_baseline
```

Las pruebas cubren pérdida de procedencia, tipos/versiones inválidos, coordenadas,
filas incompletas, IDs duplicados, jerarquía y páginas incoherentes, celdas
combinadas, continuaciones inválidas y separación de figuras/diagnósticos.
El resultado Ricoh guardado también se valida cuando está disponible localmente.

La comprobación completa debe conservar el hash de extracción y las nueve
referencias fijadas en el paso 1. Es normal que informe cambiado el código de
external_ingestion.py por la nueva validación; la referencia congelada no se actualiza.
La validación estructural no demuestra fidelidad semántica, exhaustividad de
extracción o revisión humana. Las estrategias, el pipeline y las reglas de
calidad más amplias siguen en los pasos posteriores del plan.

## Resultado del paso 2 — 24-10-2026 (America/Bogota)

- 11 pruebas nuevas de contratos; 35 pruebas específicas del extractor/línea
  base/fragmentación correctas. Suite unitaria completa: 287 correctas.
- Extracción completa con validación integrada idéntica a la línea base:
  ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44.
- Sin secciones ni archivos de referencia cambiados. La única diferencia de
  código registrada frente a la captura inicial es external_ingestion.py,
  por incorporar la validación. La línea base permanece intacta.
- Informe técnico local ignorado:
  `docs/rag_runs/extraction_baseline/20261025T023955782724Z.json` (hora UTC).
- Sin llamadas a proveedores ni cambios en datos, índices o despliegue. No se
  repitió la suite API; no hay cambios de contrato HTTP.

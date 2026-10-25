# Estrategias de extracción por página y región — paso 5

Actualización posterior: el paso 7 añadió `column_text` y `borderless_tables`
con geometría explícita y un candidato OCR separado. El alcance, configuración
y validación pendiente con nuevos PDF reales están en
[COMPLEX_PDF_EVALUATION.md](COMPLEX_PDF_EVALUATION.md). Los apartados siguientes
conservan el alcance histórico del paso 5.

`src/rag/extraction_strategies.py` separa los métodos de extracción y su selección.
El perfil Ricoh existente no se modifica: sigue usando texto nativo y tablas con
bordes, incluidas las correcciones geométricas revisadas. El JSON de extracción
mantiene schema_version=1 y la misma serialización.

| Estrategia | Trabajo | Condición |
|---|---|---|
| native_text | Recupera líneas sobre la vista de texto, después de retirar encabezados y las tablas seleccionadas. | Requiere texto digital; no ejecuta OCR. |
| ruled_tables | Detecta tablas con el adaptador y aplica las correcciones revisadas del perfil. | Conserva cuadrículas, filas y celdas originales. |
| text_only | Desactiva el tratamiento estructurado de tablas y deja su texto en el flujo nativo. | Solo por selección explícita y justificada; genera diagnóstico review. No es un fallback automático. |

Las interfaces TextStrategy y TableStrategy permiten inyectar implementaciones
mediante ExtractionStrategies. El pipeline recibe `strategies=`; sin ese argumento
usa el registro predeterminado. Una implementación ausente se rechaza.

## Configuración declarativa

La extensión opcional `extraction_profile.strategies` admite default_text,
default_tables, default_reason y una lista pages. Sin extensión, se conserva el
comportamiento previo. Cada regla de pages contiene first/last inclusivos, text,
tables, reason y regions opcionales. No hay precedencia implícita: rangos o
regiones superpuestos se rechazan.

Ejemplo para preparar **una copia de perfil de prueba**, con página y coordenadas
obtenidas de revisión del documento correspondiente:

```python
from copy import deepcopy

def perfil_con_region_revisada(profile, pdf_page, bbox):
    updated = deepcopy(profile)
    updated['strategies'] = {'pages': [{
        'first': pdf_page, 'last': pdf_page,
        'text': 'native_text', 'tables': 'ruled_tables',
        'reason': 'Página revisada contra el original.',
        'regions': [{'bbox': bbox, 'tables': 'ruled_tables',
                     'settings': {'snap_tolerance': 1},
                     'reason': 'Límites y parámetros contrastados visualmente.'}],
    }]}
    return updated
```

No se introdujeron reglas nuevas en el manifiesto activo. Cambiar un perfil
requiere revisar sus efectos: la línea base detecta también cambios de perfil,
aunque las preguntas o el PDF no cambien. No se actualiza para ocultar diferencias.

## Tratamiento de regiones

Una región puede sustituir tablas completas o dejar su contenido como texto
nativo. Las tablas exteriores se conservan. Se rechaza cortar una tabla, una
región fuera de altura o una región donde se esperaba tabla y no se detectó ninguna.
El adaptador comprueba además los límites del recorte contra la página real.

Si una tabla completa ya está reconocida y la regla no cambia settings, se
reutiliza su cuadrícula original. La prueba de Ricoh 185 mostró que volver a
recortar por sus bordes exactos podía perder una celda. Si hay redetección, se
rechaza la pérdida de palabras previamente recuperadas, contabilizadas con
multiplicidad. Este control es conservador; no demuestra asignación semántica
correcta de causas y soluciones ni autoriza reconstruir celdas por conjetura.

Una selección text_only para una página con una corrección geométrica revisada
entra en conflicto y se rechaza. La selección explícita por región se registra
con su justificación y, si desactiva estructura, con diagnóstico de revisión.

No se añadieron OCR, lectura de diagramas, detección automática de modalidades o
una estrategia especializada validada para tablas sin bordes. Los nombres no
implementados (por ejemplo ocr) fallan sin sustitución silenciosa. Las páginas
sin texto siguen rechazándose durante auditoría, con contexto de etapa y página.

## Trazabilidad y CLI

```python
trace = []
result = extract_real_document(manifest, document_id, strategy_trace=trace)
```

La traza separa selección de página, reglas regionales, exclusiones y diagnósticos.
Cada registro identifica documento, página y motivo. Se registra la selección
antes de ejecutarla; una excepción sigue siendo un fallo, no una aprobación.
El resultado v1 no recibe campos de traza nuevos.

`scripts.extract_real_manual` guarda también strategy_trace.json en el directorio
de salida. summary.json incluye su cantidad de registros y SHA-256. Para probar,
usar un directorio nuevo fuera de los datos guardados; no sobrescribir la extracción
de referencia. Si la extracción falla, el CLI no publica un resultado parcial.

## Verificación del 24-10-2026 (America/Bogota)

- Diez pruebas nuevas; 60 específicas correctas. Incluyen selección, configuraciones
  inválidas, regiones, pérdida de texto, inyección, CLI y tabla real Ricoh 185.
- Suite unitaria completa: 312 correctas. No se repitió la suite API.
- Extracción completa de Ricoh idéntica a la línea base, hash
  ca1178c5ddda48bb0940f7cd8ee88d15e288ed82892a1fdda702ea630ec46f44.
- CLI real en `/tmp/ti-ricoh-strategies-step5`: 228 registros, 213 selecciones
  native_text/ruled_tables y 15 exclusiones, todos con motivo. Checksum comprobado.
- Sin secciones ni nueve referencias locales cambiadas; fuente, perfil e índices
  intactos. No hubo proveedores, embeddings, Supabase o despliegue.
- Informe técnico local ignorado:
  `docs/rag_runs/extraction_strategies/check_20261024.json`. Comparación de línea
  base previa: `docs/rag_runs/extraction_baseline/20261025T033208168385Z.json`.

Estas son comprobaciones de extracción, no métricas de calidad RAG ni revisión
humana nueva. Nuevos documentos complejos y sus métodos especializados se
evaluarán en el paso 7, después de formalizar las validaciones del paso 6.

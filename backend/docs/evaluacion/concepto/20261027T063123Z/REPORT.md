# Pruebas nuevas: concepto de mesa de ayuda TI

Resultado de la revisión del agente: 3 satisfactorias, 3 parciales y 6 abstenciones; 0 errores técnicos visibles.

Las preguntas se fijaron antes de ejecutar y sus criterios se basaron en referencias externas. No se usaron los manuales ni casos existentes para redactar esta batería. Se reutilizó únicamente el controlador GUI. El producto consultó su corpus habitual, sin ampliarlo ni recibir las referencias externas.

Una abstención documental puede ser prudente y, a la vez, no demostrar el concepto preguntado. Una explicación plausible con citas tampoco acredita por sí sola fidelidad documental.

| Caso | Tema | Valoración | Observación del agente |
|---|---|---|---|
| C01 | Definición | satisfactoria | Explica punto de contacto, recepción, clasificación, derivación y seguimiento en lenguaje accesible. |
| C02 | Alcance | satisfactoria | Amplía el alcance más allá de reparación: cuentas, seguridad y clasificación. No afirma ejecutar una acción real. |
| C03 | Tickets | satisfactoria | Relaciona el ticket con registro, prioridades y trazabilidad; explica pérdidas del manejo informal. |
| C04 | Incidente y solicitud | abstencion | No distingue los conceptos ni da ejemplos. La abstención evita inventar, pero no satisface la pregunta. |
| C05 | Ciclo de atención | parcial | Incluye atención y comprobación con el usuario, pero omite registro/prioridad y mezcla cierre definitivo con documentar por qué sigue abierto. |
| C06 | Escalamiento | parcial | Define transferencia y continuidad, pero presenta actualizar la categoría como obligación al escalar y no explica bien la entrega del contexto. |
| C07 | Prioridad | abstencion | No explica impacto ni urgencia. Remite a falta de evidencia y soporte humano sin resolver la comparación conceptual. |
| C08 | SLA | abstencion | No define SLA ni distingue primera respuesta de resolución. No inventa plazos. |
| C09 | Conocimiento | abstencion | No diferencia el registro de casos de los artículos de conocimiento reutilizables. |
| C10 | Canales | abstencion | No explica correlación de contactos ni seguimiento unificado entre canales. |
| C11 | Automatización | abstencion | No distingue la función de mesa de ayuda de una herramienta chatbot ni sus responsabilidades humanas. |
| C12 | Valor del servicio | parcial | Propone verificar resolución y clasificación, pero no desarrolla indicadores de oportunidad, calidad o satisfacción. Repite la ambigüedad entre cerrar y quedar pendiente. |

## Hallazgos

- El sistema explica definición, alcance y valor del ticket con claridad suficiente.
- No desarrolla incidente/solicitud, prioridades, SLA, conocimiento, canales y chatbot en esta ejecución: seis abstenciones.
- La explicación de cierre mezcla resolver y mantener pendiente un caso. La de escalamiento confunde la transferencia con reclasificar obligatoriamente.
- La respuesta de calidad del servicio ofrece comprobaciones útiles, pero no un conjunto suficiente de indicadores.
- Persisten textos internos como OK_EVIDENCIA_INSUFICIENTE y Respuesta dentro de 90 palabras. Son defectos de presentación separados del conocimiento conceptual.

## Criterio externo y trazabilidad

- **reviewer:** Codex, agente; no revisión humana
- **question_basis:** Criterios externos y preguntas redactadas antes de observar las respuestas. No se usaron los casos ni manuales existentes para redactarlos.
- **execution:** GUI real; una nueva consulta por pregunta. Solo se reutilizó el controlador técnico de interacción.
- **retrieval:** El producto conservó su recuperación habitual. Las referencias externas no se incluyeron en prompts ni se incorporaron al corpus.
- **plan_sha256:** e4853fa89b1f59c9b62c67a1f9bd6750da2ead4106e9386c2758591ed20c0282
- **plan_file_mtime_utc:** 2026-10-27T06:33:39.547837+00:00
- **first_query_utc:** 2026-10-27T06:34:00.996Z
- **independence:** Batería exploratoria nueva, separada del desarrollo anterior. No es la reserva formal ni prueba de independencia estadística.
- **grounding:** Las etiquetas documentales se transcriben de la GUI; no certifican que cada cita sustente cada afirmación. No se reutilizaron los manuales para formar el criterio conceptual.
- **latency:** elapsedSeconds incluye coordinación del controlador. No se usó como benchmark ni se compararon tiempos.

## Referencias

- [IBM-HD](https://www.ibm.com/think/topics/help-desk)
- [IBM-SD](https://www.ibm.com/think/topics/service-desk)
- [ATL-INC](https://www.atlassian.com/incident-management/itsm)
- [ATL-PRIO](https://support.atlassian.com/jira-service-management-cloud/docs/how-impact-and-urgency-are-used-to-calculate-priority/)
- [ATL-SRM](https://www.atlassian.com/itsm/service-request-management/)
- [ATL-SLA](https://www.atlassian.com/itsm/service-request-management/slas)

## Archivos

- QUESTIONS.md: las doce preguntas y sus criterios previos.
- test-plan.json y test-plan.sha256: plan fijado antes de la primera consulta.
- observations.json: texto visible original y metadatos de la ejecución.
- results.json y results.csv: valoraciones separadas de lo que el sistema publicó.
- C01.png a C12.png: capturas de las respuestas.
- PDF: output/pdf/concepto-mesa-ayuda-ti-20261027.pdf, desde la raíz del proyecto.

Al ser expuesta y revisada, esta batería puede usarse como desarrollo posterior, pero no debe presentarse como reserva independiente. No se cambió el producto para mejorar estos resultados.

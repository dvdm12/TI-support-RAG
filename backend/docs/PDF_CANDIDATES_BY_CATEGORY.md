# PDF candidatos por categoría - 24-10-2026

Búsqueda solicitada para ampliar las fuentes de resolución de problemas del
proyecto. Se contrastaron las siete categorías y los temas del corpus local.
Resultado: 12 candidatos, 10 PDF descargados y abiertos correctamente, cobertura
de las siete categorías y dos descargas pendientes. Son 363 páginas en conjunto;
la revisión de pertinencia fue dirigida, no una aprobación semántica completa
de todas ellas. Los dominios pertenecen al fabricante, proyecto o institución
responsable. No se utilizaron repositorios de manuales sin procedencia.

Registro con URL, SHA-256, versión/contexto, páginas y límites:
`docs/fixtures/category_pdf_candidates_v1.json`. Las copias completas y el
inventario de descarga son locales e ignorados por Git, en
`docs/rag_runs/category_pdf_discovery/20261024/`. No están disponibles
automáticamente al clonar el repositorio.

## Fuentes verificadas

Los números siguientes son **páginas físicas del PDF**, no necesariamente su
numeración impresa. Indican puntos de partida; la adecuación de cada
procedimiento al entorno sigue pendiente.

| Categoría | PDF y responsable | Problemas y páginas de interés | Alcance que debe conservar el RAG |
|---|---|---|---|
| hardware | [HP User Guide, P21191-001](https://kaas.hpcloud.hp.com/pdf-public/pdf_11059908_en-US-1.pdf), primera edición diciembre de 2024; inglés, 95 páginas | Herramientas de diagnóstico Windows/UEFI, identificadores de fallo, batería/alimentación. Páginas 50–51 y 77–82. | Equipos HP con funciones compatibles; el modelo y la disponibilidad de herramientas deben verificarse. No es un manual universal de todos los PC. |
| software | [LibreOffice 24.8: Conceptos básicos](https://documentation.libreoffice.org/assets/Uploads/Documentation/es/GS248/PDF/GS24801-ConceptosBasicos.pdf), 31 páginas | Guardado y recuperación automática, interfaz y funcionamiento básico. Página 15; configuración y extensiones hacia el final del capítulo. | LibreOffice; no confundir con soporte de Microsoft Office ni con fallos generales de Windows. |
| software | [LibreOffice 24.8: Configurar LibreOffice](https://documentation.libreoffice.org/assets/Uploads/Documentation/es/GS248/PDF/GS24812-ConfigurarLO.pdf), 37 páginas | Opciones de carga/guardado, recuperación y compatibilidad de archivos. Páginas 12–14 y 20–21. | Verificar versión e interfaz. Es una guía de configuración, no un catálogo exhaustivo de errores de instalación. |
| redes | [Cisco: Resolución de problemas de DHCP en redes empresariales](https://www.cisco.com/c/es_mx/support/docs/ip/dynamic-address-allocation-resolution/27470-100.pdf), 44 páginas | Cliente sin dirección IP/concesión, enlace físico, NIC, VLAN y retransmisión DHCP. Páginas 33–36 y secciones previas de diagnóstico. | Entorno Cisco Catalyst/IOS. Separar comprobaciones de usuario de cambios de red que competen al administrador. |
| redes | [Cisco: Comprensión de Ping y Traceroute](https://www.cisco.com/c/es_mx/support/docs/ios-nx-os-software/ios-software-releases-121-mainline/12778-ping-traceroute.pdf), 32 páginas | Alcance de un destino, pérdida/latencia y seguimiento de ruta. Páginas 3, 10–12 y 18–22. | Los ejemplos son de routers Cisco; no extrapolar comandos de depuración a cualquier dispositivo o red. |
| cuentas | [Universidad Piloto: Restablecimiento de contraseña y MFA](https://www.unipiloto.edu.co/descargas/Manual-Restablecimiento-Contrasena-MFA-int.pdf), declara 2026; 14 páginas | Registro de Microsoft Authenticator y restablecimiento mediante Microsoft 365. Páginas 3–8 y 9–13. | Procedimiento de ese tenant institucional. Requiere métodos de verificación y políticas habilitadas; no autoriza crear/desactivar cuentas ni omitir validación de identidad. |
| seguridad | [INCIBE: Guía de ciberataques](https://www.incibe.es/sites/default/files/docs/guia-ciberataques/osi-guia-ciberataques.pdf), 46 páginas | Phishing y otros engaños, malware y ransomware, medidas preventivas. Páginas 8–14 y 38. | Información y prevención para usuarios. No sustituye el procedimiento local de respuesta a incidentes ni un análisis forense. |
| seguridad | [INCIBE: Copias de seguridad](https://www.incibe.es/sites/default/files/contenidos/guias/guia-copias-de-seguridad.pdf), edición identificada como 2018-v1; 32 páginas | Estrategia 3-2-1, restauración y comprobación de copias. Páginas 16–22. | Criterios generales. La existencia de esta guía no demuestra que haya un respaldo de Supabase ni una restauración comprobada del proyecto. |
| acceso | [Universidad Icesi: Doble factor al cambiar de dispositivo móvil](https://www.icesi.edu.co/servicios/wp-content/uploads/2025/03/Manual-doble-factor-de-autenticacion-cambio-de-dispositivo-movil-1.pdf), 3 páginas | Registrar otro dispositivo de Authenticator y retirar el anterior. Páginas 1–3. | Exige mantener acceso a Microsoft 365. No resuelve pérdida total de MFA, permisos a recursos ni HTTP 403. Adaptar al tenant autorizado. |
| otros | [Alcaldía de Sabaneta: Guía para el manejo de mesa de ayuda v1](https://sabaneta.gov.co/files/allfiles/15747193369929.pdf), diciembre de 2017; 29 páginas | Datos mínimos de un caso, registro de ticket, asignación, escalamiento y trazabilidad. Páginas 4–8, 12–13 y 22–23. | Referencia histórica y municipal de triaje; contrastar vigencia. No copiar contactos, acuerdos de servicio o políticas como si fueran de AulaTI. |

La categoría `otros` representa aclaración y derivación: estas fuentes apoyan
la recogida de datos y el escalamiento, no son una solución técnica universal
ni justifican enviar a `otros` un caso que ya puede clasificarse.

## Candidatos pendientes de descarga local

Se localizaron dos documentos adicionales en fuentes institucionales. La
descarga desde esta máquina no validó la cadena TLS; se conserva ese estado
sin desactivar la comprobación del certificado ni afirmar que hay copia local.

- **Acceso:** [IDEP: Administración de la red LAN y políticas de seguridad](https://www.idep.edu.co/sites/default/files/2023-07/MN-GT-12-07%20Manual%20para%20la%20administraci%C3%B3n%20de%20la%20red%20lan%20del%20IDEP%20y%20pol%C3%ADticas%20de%20seguridad.pdf), versión 2 de 07-07-2023. La sección VPN de la página 16 aporta solicitudes, roles y condiciones de acceso propias del IDEP.
- **Otros:** [DNP: Procedimiento de mesas de ayuda](https://colaboracion.dnp.gov.co/CDT/DNP/SIG/PT-AT-01%20Mesas%20de%20ayuda.Pu.pdf), versión 1 de 25-08-2025 según la fuente web. Aporta revisión de datos, asignación y escalamiento; el alcance sigue siendo la institución autora.

## Huecos y decisión de incorporación

La cobertura de categorías no implica cubrir todos sus problemas. Faltan
fuentes adaptadas al entorno real para bloqueo y pérdida total de MFA,
autorización de recursos/HTTP 403, altas/bajas de cuentas, incidencias de
aplicaciones concretas y diagnóstico Wi-Fi según el equipo y servicio usados.

Para incorporar un candidato habrá que comprobar producto/modelo/versión,
autoridad documental y fecha, condiciones de uso, procedencia por página,
calidad de extracción y respaldo de los procedimientos. Las reglas de otras
instituciones deben conservar su ámbito y no convertirse en políticas locales.

Esta búsqueda **no ejecutó pruebas completas del pipeline sobre los candidatos**,
ni produjo embeddings o índices. No cambió corpus académico, PDF/perfil Ricoh,
Supabase, evaluación de reserva o métricas de clase 09. Los límites detectados
en la sesión previa con otros seis PDF siguen documentados en
[WEB_PDF_EVALUATION.md](WEB_PDF_EVALUATION.md); no transferir sus resultados a
estos diez candidatos nuevos.

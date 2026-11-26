# Preguntas para la presentación

Preguntas probadas el 2026-11-25 contra el backend local (Docker), en modo **Soporte TI**.
La columna *Resultado* es el estado que devolvió el sistema y la columna *Fuentes*,
las secciones de los manuales que citó. Las respuestas del modelo pueden variar un
poco entre ejecuciones.

## Orden sugerido para la demo

1. Saludo → 2. Wi‑Fi → 3. Correo sospechoso → 4. Error 403 → 5. Contraseña olvidada →
6. Pregunta ambigua ("no funciona") → 7. Fuera de alcance → 8. Búsqueda en Manuales →
9. Recargar la página para mostrar el historial guardado.

## 1. Respuesta directa

| Pregunta | Resultado |
|---|---|
| hola | Respuesta directa: explica qué puede hacer |
| ¿Qué puedes hacer? | Respuesta directa |

## 2. Redes y conectividad

| Pregunta | Resultado | Fuentes |
|---|---|---|
| Mi laptop no se conecta al Wi-Fi de la oficina, ¿qué reviso? | ✅ Validada | RED-02 |
| Tengo cable de red conectado pero no tengo internet | Respuesta parcial | RED-02, RED-03 |
| Estoy conectado a la red pero no puedo abrir el portal interno | Respuesta parcial | RED-02, RED-04 |

## 3. Cuentas y acceso

| Pregunta | Resultado | Fuentes |
|---|---|---|
| Olvidé mi contraseña del correo corporativo | Requiere soporte humano | CTA-03 |
| Quiero cambiar mi correo de recuperación | ✅ Validada | CTA-03, CTA-04 |
| Me dice que mi usuario o contraseña son incorrectos aunque estoy seguro de que son correctos | ✅ Validada | ACS-02, CTA-03 |
| Me aparece error 403 al entrar al sistema de nómina | ✅ Validada | ACS-03, ACS-05 |
| Necesito acceso a una carpeta compartida de otro departamento | ✅ Validada | ACS-01, CTA-01, RED-04 |

## 4. Seguridad

| Pregunta | Resultado | Fuentes |
|---|---|---|
| Recibí un correo de RRHH pidiéndome entrar a un enlace para actualizar mis datos | Requiere soporte humano · prioridad alta | SEG-02, CTA-04 |
| Creo que alguien conoce mi contraseña | Requiere soporte humano · prioridad alta · pide más datos | — |
| Hay un archivo en mi escritorio que no reconozco y el equipo hace cosas raras | Requiere soporte humano · pide más datos | — |

## 5. Hardware

| Pregunta | Resultado | Fuentes |
|---|---|---|
| Mi computador no enciende, no prende ninguna luz | Requiere soporte humano · prioridad alta | HW-02 |
| El mouse y el teclado USB dejaron de funcionar | ✅ Validada | HW-01, HW-02, HW-03 |
| La impresora no imprime, los documentos se quedan en cola | Pide aclaración | HW-03, HW-05 |

## 6. Software

| Pregunta | Resultado | Fuentes |
|---|---|---|
| Necesito instalar un programa en mi equipo | ✅ Validada | SW-01, SW-03 |
| Una aplicación se cierra sola cada vez que la abro | Respuesta parcial | SW-01, SW-02 |
| Mi correo no sincroniza en el celular | Pide aclaración | CTA-03, CTA-04 |

## 7. Comportamiento seguro (no inventa)

Sirven para mostrar que el sistema pide datos o reconoce sus límites en lugar de
inventar una respuesta.

| Pregunta | Resultado |
|---|---|
| no funciona | Pide aclaración: dispositivo, qué ocurre y mensaje de error |
| ¿Cuál es la capital de Francia? | Evidencia insuficiente: no responde fuera de soporte TI |
| Necesito comprar sillas nuevas para la oficina | Evidencia insuficiente |

## 8. Modo Manuales (búsqueda sin IA)

En el selector del cuadro de texto, cambia a **Manuales**. Devuelve los pasajes sin
generar respuesta.

| Búsqueda | Pasajes esperados |
|---|---|
| Restablecer contraseña del correo corporativo | CTA-03, ACS-02 |
| Conexión Wi-Fi | RED-02, RED-01 |
| Mensaje o enlace sospechoso | SEG-02, SEG-03 |
| Cola de impresión | SW-04, HW-05 |

## Evitar en la demo

- **VPN**: los manuales no la cubren y la respuesta se desvía hacia el Wi‑Fi.
- **Impresora que imprime hojas en blanco**: devuelve evidencia insuficiente.
- La primera consulta tras arrancar el backend puede tardar más (carga del modelo).
  Haz una pregunta de calentamiento antes de presentar.

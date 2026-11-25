import test from "node:test";
import assert from "node:assert/strict";
import {
  HistorialError,
  aMensajesUI,
  cargarMensajes,
  crearConversacion,
  guardarTurno,
  listarConversaciones,
  textoRespuesta,
  tituloDesde,
} from "../src/services/historial.js";

// Cliente falso con la misma cadena que supabase-js: registra cada llamada y
// resuelve { data, error } al hacer await.
function fakeClient(result = { data: [], error: null }) {
  const calls = [];
  const builder = (table) => {
    const call = { table, ops: [] };
    calls.push(call);
    const chain = {};
    for (const op of ["select", "insert", "order", "eq", "single"])
      chain[op] = (...args) => {
        call.ops.push([op, ...args]);
        return chain;
      };
    chain.then = (resolve, reject) =>
      Promise.resolve(typeof result === "function" ? result(call) : result).then(resolve, reject);
    return chain;
  };
  return { calls, from: builder };
}

test("lista las conversaciones del usuario, más recientes primero", async () => {
  const client = fakeClient({ data: [{ id: "c1", titulo: "Wi-Fi", actualizada_en: "t" }], error: null });
  assert.deepEqual(await listarConversaciones(client), [{ id: "c1", titulo: "Wi-Fi", actualizada_en: "t" }]);
  const [{ table, ops }] = client.calls;
  assert.equal(table, "conversaciones");
  assert.deepEqual(ops[1], ["order", "actualizada_en", { ascending: false }]);
  // El filtro por usuario lo aplica RLS, no el cliente: no hay .eq('usuario_id').
  assert.ok(!ops.some(([op]) => op === "eq"));
});

test("crea la conversación sin usuario_id (DEFAULT auth.uid()) y con título válido", async () => {
  const client = fakeClient(({ ops }) => ({ data: { id: "c9", titulo: ops[0][1].titulo }, error: null }));
  const conv = await crearConversacion(client, "  ¿Cómo   configuro\nel Wi-Fi?  ");
  assert.equal(conv.titulo, "¿Cómo configuro el Wi-Fi?");
  const insert = client.calls[0].ops[0][1];
  assert.deepEqual(Object.keys(insert), ["titulo"]);
});

test("el título respeta el CHECK de 1 a 200 caracteres", () => {
  assert.equal(tituloDesde("   "), "Nueva consulta");
  const largo = tituloDesde("x".repeat(500));
  assert.equal(largo.length, 200);
  assert.ok(largo.endsWith("…"));
});

test("guarda pregunta y respuesta con sus fuentes en un solo insert", async () => {
  const client = fakeClient({ data: null, error: null });
  const fuentes = [{ id: "F1", chunk_id: "wifi-1" }];
  await guardarTurno(client, "c1", " Wi-Fi no conecta ", {
    respuesta_documental: { respuesta: "Comprueba el modo avión [F1]." },
    fuentes,
  });
  const [{ table, ops }] = client.calls;
  assert.equal(table, "mensajes");
  assert.deepEqual(ops[0][1], [
    { conversacion_id: "c1", rol: "usuario", contenido: "Wi-Fi no conecta", fuentes: [] },
    { conversacion_id: "c1", rol: "asistente", contenido: "Comprueba el modo avión [F1].", fuentes },
  ]);
});

test("una respuesta sin texto no viola el CHECK de contenido", async () => {
  const client = fakeClient({ data: null, error: null });
  await guardarTurno(client, "c1", "hola", {});
  assert.equal(client.calls[0].ops[0][1][1].contenido, "(respuesta sin texto)");
});

test("en búsqueda de manuales guarda los pasajes como fuentes", async () => {
  const client = fakeClient({ data: null, error: null });
  const pasajes = [{ chunk_id: "p1" }];
  await guardarTurno(client, "c1", "wifi", { pasajes });
  const asistente = client.calls[0].ops[0][1][1];
  assert.deepEqual(asistente.fuentes, pasajes);
  assert.match(asistente.contenido, /pasajes/);
});

test("a igual marca de tiempo, la pregunta va antes que la respuesta", () => {
  const t = "2026-11-25T18:00:00Z";
  const ui = aMensajesUI([
    { id: "a", rol: "asistente", contenido: "Respuesta", fuentes: [{ id: "F1" }], creado_en: t },
    { id: "u", rol: "usuario", contenido: "Pregunta", fuentes: [], creado_en: t },
    { id: "u0", rol: "usuario", contenido: "Antes", fuentes: [], creado_en: "2026-11-25T17:00:00Z" },
  ]);
  assert.deepEqual(ui.map((m) => m.id), ["u0", "u", "a"]);
  assert.deepEqual(ui[2], {
    id: "a", role: "assistant", status: "done", stored: true,
    data: { respuesta: "Respuesta", fuentes: [{ id: "F1" }] },
  });
  assert.equal(textoRespuesta(ui[2].data), "Respuesta");
});

test("carga los mensajes de una conversación concreta", async () => {
  const client = fakeClient({ data: [], error: null });
  await cargarMensajes(client, "c7");
  assert.ok(client.calls[0].ops.some(([op, col, val]) => op === "eq" && col === "conversacion_id" && val === "c7"));
});

test("los errores de Supabase se traducen a mensajes para la interfaz, sin detalles internos", async () => {
  const client = fakeClient({ data: null, error: { message: "permission denied for table mensajes" } });
  await assert.rejects(listarConversaciones(client), (e) => e instanceof HistorialError && !/permission/.test(e.message));
  await assert.rejects(cargarMensajes(client, "ajena"), HistorialError);
  await assert.rejects(guardarTurno(client, "ajena", "hola", { respuesta: "x" }), HistorialError);
  await assert.rejects(crearConversacion(client, "x"), HistorialError);
});

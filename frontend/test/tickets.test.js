import test from "node:test";
import assert from "node:assert/strict";
import {
  ESTADOS,
  TicketsError,
  actualizarTicket,
  listarTickets,
  validarCambios,
} from "../src/services/tickets.js";

// Cliente falso con la cadena de supabase-js usada por el servicio.
function fakeClient(result = { data: [], error: null }) {
  const calls = [];
  return {
    calls,
    from(table) {
      const call = { table, ops: [] };
      calls.push(call);
      const chain = {};
      for (const op of ["select", "update", "eq", "order"])
        chain[op] = (...args) => {
          call.ops.push([op, ...args]);
          return chain;
        };
      chain.then = (resolve, reject) =>
        Promise.resolve(typeof result === "function" ? result(call) : result).then(resolve, reject);
      return chain;
    },
  };
}

test("lista los tickets ordenados por código", async () => {
  const filas = [{ codigo: "TI-1001", estado: "Abierto", detalle: "d", actualizado_en: "t" }];
  const client = fakeClient({ data: filas, error: null });
  assert.deepEqual(await listarTickets(client), filas);
  assert.deepEqual(client.calls[0].ops[1], ["order", "codigo"]);
});

test("actualizar envía solo estado y detalle, del ticket indicado", async () => {
  const fila = { codigo: "TI-1004", estado: "Resuelto", detalle: "Listo", actualizado_en: "t" };
  const client = fakeClient({ data: [fila], error: null });
  assert.deepEqual(await actualizarTicket(client, "TI-1004", { estado: "Resuelto", detalle: "  Listo " }), fila);
  const { table, ops } = client.calls[0];
  assert.equal(table, "tickets");
  assert.deepEqual(ops[0], ["update", { estado: "Resuelto", detalle: "Listo" }]);
  assert.deepEqual(ops[1], ["eq", "codigo", "TI-1004"]);
});

test("si RLS bloquea el cambio (0 filas) se informa el error", async () => {
  const client = fakeClient({ data: [], error: null });
  await assert.rejects(
    actualizarTicket(client, "TI-1001", { estado: "Cerrado", detalle: "x" }),
    (e) => e instanceof TicketsError && /sesión/.test(e.message),
  );
});

test("valida estado y detalle antes de llamar a Supabase", async () => {
  assert.equal(validarCambios({ estado: ESTADOS[0], detalle: "ok" }), "");
  assert.match(validarCambios({ estado: "Inventado", detalle: "ok" }), /estado/);
  assert.match(validarCambios({ estado: "Abierto", detalle: "   " }), /vacío/);
  assert.match(validarCambios({ estado: "Abierto", detalle: "x".repeat(501) }), /500/);
  const client = fakeClient();
  await assert.rejects(actualizarTicket(client, "TI-1001", { estado: "Inventado", detalle: "x" }), TicketsError);
  assert.equal(client.calls.length, 0);
});

test("los errores de Supabase no exponen detalles internos", async () => {
  const client = fakeClient({ data: null, error: { message: "permission denied for table tickets" } });
  await assert.rejects(listarTickets(client), (e) => !/permission/.test(e.message));
  await assert.rejects(
    actualizarTicket(client, "TI-1001", { estado: "Abierto", detalle: "x" }),
    (e) => !/permission/.test(e.message),
  );
});

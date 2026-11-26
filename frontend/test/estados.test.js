import test from "node:test";
import assert from "node:assert/strict";
import { stateLabel } from "../src/data/support.js";

test("los estados se muestran como texto legible, nunca como código interno", () => {
  assert.equal(stateLabel("OK_EVIDENCIA_INSUFICIENTE"), "Evidencia insuficiente");
  assert.equal(stateLabel("OK_TICKETS_LISTADOS"), "Tickets listados");
  assert.equal(stateLabel("OK_SOLICITUD_HUMANO"), "Derivación a soporte humano");
  assert.equal(stateLabel("OK_ALGO_NUEVO"), "Algo nuevo");
  assert.equal(stateLabel(""), "");
  assert.ok(!/_/.test(stateLabel("ESTADO_DESCONOCIDO")));
});

import test from "node:test";
import assert from "node:assert/strict";
import { ApiError, request } from "../src/services/api.js";

test("uses same-origin API and the text contract without browser credentials", async () => {
  const data = {
    request_id: "test",
    respuesta_documental: { estado: "aclaracion" },
  };
  assert.deepEqual(
    await request("rag/query/", {
      body: { pregunta: "Mi equipo no enciende" },
      fetcher: async (url, options) => {
        assert.equal(url, "/api/v1/rag/query/");
        assert.equal(options.method, "POST");
        assert.deepEqual(JSON.parse(options.body), {
          pregunta: "Mi equipo no enciende",
        });
        assert.equal(options.headers.Authorization, undefined);
        return Response.json(data);
      },
    }),
    data,
  );
});

test("preserves successful clarification and insufficient-evidence business states", async () => {
  for (const state of [
    "aclaracion",
    "evidencia_insuficiente",
    "parcial",
    "respondida",
  ]) {
    const result = await request("rag/query/", {
      fetcher: async () =>
        Response.json({ respuesta_documental: { estado: state } }),
    });
    assert.equal(result.respuesta_documental.estado, state);
  }
});

test("maps provider errors without exposing raw details and retains request id and retry delay", async () => {
  for (const [status, code] of [
    [401, "unauthorized"],
    [422, "input_too_large"],
    [429, "provider_rate_limited"],
    [502, "invalid_provider_response"],
    [503, "service_busy"],
  ]) {
    await assert.rejects(
      request("rag/query/", {
        fetcher: async () =>
          Response.json(
            {
              request_id: "trace-123",
              error: { code, message: "internal provider details" },
            },
            { status, headers: { "Retry-After": "12" } },
          ),
      }),
      (error) => {
        assert.ok(error instanceof ApiError);
        assert.equal(error.status, status);
        assert.equal(error.code, code);
        assert.equal(error.requestId, "trace-123");
        assert.equal(error.retryAfter, "12");
        assert.ok(!error.message.includes("internal provider details"));
        return true;
      },
    );
  }
});

test("handles offline backend and non-JSON proxy responses", async () => {
  await assert.rejects(
    request("health/", {
      fetcher: async () => {
        throw new TypeError("socket");
      },
    }),
    (error) => error.code === "network_error",
  );
  await assert.rejects(
    request("health/", {
      fetcher: async () => new Response("Bad gateway", { status: 502 }),
    }),
    (error) => error.code === "invalid_response",
  );
});

test("forwards abort signals and distinguishes cancellation from service failure", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    request("rag/query/", {
      signal: controller.signal,
      fetcher: async (_url, options) => {
        assert.equal(options.signal, controller.signal);
        options.signal.throwIfAborted();
      },
    }),
    { name: "AbortError" },
  );
});

test("manual search keeps category preference and never changes backend identity", async () => {
  await request("rag/search/", {
    body: { pregunta: "Correo sospechoso", categoria: "seguridad" },
    fetcher: async (url, options) => {
      assert.equal(url, "/api/v1/rag/search/");
      assert.deepEqual(JSON.parse(options.body), {
        pregunta: "Correo sospechoso",
        categoria: "seguridad",
      });
      return Response.json({ pasajes: [] });
    },
  });
});

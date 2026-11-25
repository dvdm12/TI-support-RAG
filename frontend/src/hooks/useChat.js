import { useEffect, useRef, useState } from "react";
import { querySupport, searchManuals } from "../services/api.js";
import {
  cargarMensajes,
  crearConversacion,
  guardarTurno,
  listarConversaciones,
} from "../services/historial.js";

// Cada chat de la barra lateral: `convId` es el id en Supabase (null hasta el
// primer turno guardado); `loaded` indica si ya se trajeron sus mensajes.
const createChat = () => ({
  id: crypto.randomUUID(),
  convId: null,
  title: "Nueva consulta",
  messages: [],
  loaded: true,
});

const fromStored = (conv) => ({
  id: conv.id,
  convId: conv.id,
  title: conv.titulo,
  messages: [],
  loaded: false,
});

export function useChat(client, userId) {
  const [chats, setChats] = useState(() => [createChat()]);
  const [activeId, setActiveId] = useState(null);
  const [pending, setPending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const controllerRef = useRef(null);
  const active = chats.find((chat) => chat.id === activeId) || chats[0];
  useEffect(() => () => controllerRef.current?.abort(), []);

  function patch(chatId, update) {
    setChats((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? { ...chat, ...(typeof update === "function" ? update(chat) : update) }
          : chat,
      ),
    );
  }

  // Al cambiar de usuario: vaciar la vista y traer sus conversaciones.
  useEffect(() => {
    let vigente = true;
    setChats([createChat()]);
    setActiveId(null);
    setHistoryError("");
    if (!client || !userId) return undefined;
    setLoadingHistory(true);
    listarConversaciones(client)
      .then((convs) => {
        if (vigente) setChats([createChat(), ...convs.map(fromStored)]);
      })
      .catch((error) => vigente && setHistoryError(error.message))
      .finally(() => vigente && setLoadingHistory(false));
    return () => {
      vigente = false;
    };
  }, [client, userId]);

  async function selectChat(id) {
    if (pending) return;
    setActiveId(id);
    const chat = chats.find((item) => item.id === id);
    if (!chat || chat.loaded || !client) return;
    try {
      const messages = await cargarMensajes(client, chat.convId);
      patch(id, { messages, loaded: true });
      setHistoryError("");
    } catch (error) {
      setHistoryError(error.message);
    }
  }

  function newChat() {
    if (pending) return;
    const empty = chats.find((chat) => !chat.messages.length && !chat.convId);
    if (empty) {
      setActiveId(empty.id);
      return;
    }
    const chat = createChat();
    setChats((current) => [chat, ...current]);
    setActiveId(chat.id);
  }

  async function persist(chat, question, data) {
    if (!client) return;
    try {
      let convId = chat.convId;
      if (!convId) {
        const conv = await crearConversacion(client, question);
        convId = conv.id;
        patch(chat.id, { convId, title: conv.titulo });
      }
      await guardarTurno(client, convId, question, data);
      setHistoryError("");
    } catch (error) {
      setHistoryError(error.message);
    }
  }

  async function send(question, mode = "query", category = "") {
    question = question.trim();
    if (!question || pending || controllerRef.current || !active.loaded) return;
    const chat = active;
    const messageId = crypto.randomUUID();
    const user = { id: crypto.randomUUID(), role: "user", content: question, mode };
    const assistant = { id: messageId, role: "assistant", status: "loading", mode };
    patch(chat.id, (current) => ({
      title: current.messages.length ? current.title : question,
      messages: [...current.messages, user, assistant],
    }));
    setPending(true);
    const controller = new AbortController();
    controllerRef.current = controller;
    const finish = (update) =>
      patch(chat.id, (current) => ({
        messages: current.messages.map((message) =>
          message.id === messageId ? { ...message, ...update } : message,
        ),
      }));
    try {
      const data =
        mode === "search"
          ? await searchManuals(question, category, controller.signal)
          : await querySupport(question, controller.signal);
      finish({ status: "done", data });
      // Solo se guardan los turnos respondidos; errores y cancelaciones no.
      await persist(chat, question, data);
    } catch (error) {
      finish({
        status: error.name === "AbortError" ? "cancelled" : "error",
        error,
      });
    } finally {
      controllerRef.current = null;
      setPending(false);
    }
  }

  return {
    chats,
    active,
    pending,
    loadingHistory,
    historyError,
    send,
    newChat,
    selectChat,
    cancel: () => controllerRef.current?.abort(),
  };
}

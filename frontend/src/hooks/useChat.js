import { useEffect, useRef, useState } from "react";
import { querySupport, searchManuals } from "../services/api.js";

const createChat = () => ({
  id: crypto.randomUUID(),
  title: "Nueva consulta",
  messages: [],
});

export function useChat() {
  const [chats, setChats] = useState(() => [createChat()]);
  const [activeId, setActiveId] = useState(null);
  const [pending, setPending] = useState(false);
  const controllerRef = useRef(null);
  const active = chats.find((chat) => chat.id === activeId) || chats[0];
  useEffect(() => () => controllerRef.current?.abort(), []);

  function newChat() {
    if (pending) return;
    const empty = chats.find((chat) => !chat.messages.length);
    if (empty) {
      setActiveId(empty.id);
      return;
    }
    const chat = createChat();
    setChats((current) => [chat, ...current]);
    setActiveId(chat.id);
  }

  async function send(question, mode = "query", category = "") {
    question = question.trim();
    if (!question || pending || controllerRef.current) return;
    const chatId = active.id;
    const messageId = crypto.randomUUID();
    const user = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      mode,
    };
    const assistant = {
      id: messageId,
      role: "assistant",
      status: "loading",
      mode,
    };
    setChats((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              title: chat.messages.length ? chat.title : question,
              messages: [...chat.messages, user, assistant],
            }
          : chat,
      ),
    );
    setPending(true);
    const controller = new AbortController();
    controllerRef.current = controller;
    function finish(update) {
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                messages: chat.messages.map((message) =>
                  message.id === messageId
                    ? { ...message, ...update }
                    : message,
                ),
              }
            : chat,
        ),
      );
    }
    try {
      const data =
        mode === "search"
          ? await searchManuals(question, category, controller.signal)
          : await querySupport(question, controller.signal);
      finish({ status: "done", data });
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
    send,
    newChat,
    selectChat: (id) => {
      if (!pending) setActiveId(id);
    },
    cancel: () => controllerRef.current?.abort(),
    clear: () => {
      if (!pending) {
        setChats([createChat()]);
        setActiveId(null);
      }
    },
  };
}

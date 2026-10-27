import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

export default function MessageList({ messages, pending, onRetry }) {
  const end = useRef(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);
  return (
    <div
      className="message-list"
      role="log"
      aria-label="Consultas y respuestas"
      aria-live="polite"
      aria-relevant="additions text"
    >
      {messages.map((message, index) => (
        <Message
          key={message.id}
          message={message}
          pending={pending}
          onRetry={() =>
            onRetry(messages[index - 1]?.content || "", message.mode)
          }
        />
      ))}
      <div ref={end} />
    </div>
  );
}

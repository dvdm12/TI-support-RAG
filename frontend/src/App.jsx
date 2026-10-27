import { useState } from "react";
import Sidebar from "./components/layout/Sidebar.jsx";
import Header from "./components/layout/Header.jsx";
import ContextPanel from "./components/layout/ContextPanel.jsx";
import SettingsDialog from "./components/layout/SettingsDialog.jsx";
import Welcome from "./components/chat/Welcome.jsx";
import StarterPrompts from "./components/chat/StarterPrompts.jsx";
import Composer from "./components/chat/Composer.jsx";
import MessageList from "./components/chat/MessageList.jsx";
import { useChat } from "./hooks/useChat.js";
import { useHealth } from "./hooks/useHealth.js";

export default function App() {
  const chat = useChat();
  const health = useHealth();
  const [mode, setMode] = useState("query");
  const [draft, setDraft] = useState("");
  const [category, setCategory] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const latest = [...chat.active.messages]
    .reverse()
    .find((message) => message.status === "done");
  function submit(question = draft, selectedMode = mode) {
    if (chat.pending || !question.trim()) return;
    chat.send(question, selectedMode, category);
    setDraft("");
  }
  function chooseMode(value) {
    if (!chat.pending) {
      setMode(value);
      setMenuOpen(false);
    }
  }
  return (
    <div
      className={`app-shell ${sidebarCollapsed ? "app-shell--collapsed" : ""}`}
    >
      <a className="skip-link" href="#main">
        Ir al chat
      </a>
      <Sidebar
        chats={chat.chats}
        activeId={chat.active.id}
        pending={chat.pending}
        mode={mode}
        onMode={chooseMode}
        onNew={() => {
          chat.newChat();
          setDraft("");
          setMenuOpen(false);
        }}
        onSelect={(id) => {
          chat.selectChat(id);
          setDraft("");
          setMenuOpen(false);
        }}
        onSettings={() => setSettingsOpen(true)}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />
      <div className="workspace">
        <Header
          mode={mode}
          status={health.status}
          onMenu={() => {
            if (window.innerWidth <= 760) setMenuOpen((value) => !value);
            else setSidebarCollapsed((value) => !value);
          }}
          sourcesOpen={sourcesOpen}
          onToggleSources={() => setSourcesOpen((value) => !value)}
        />
        <div className="workspace-body">
          <main
            id="main"
            className={`chat-main ${chat.active.messages.length ? "chat-main--started" : ""}`}
          >
            <div className="chat-scroll" key={`scroll-${chat.active.id}`}>
              {chat.active.messages.length ? (
                <MessageList
                  messages={chat.active.messages}
                  pending={chat.pending}
                  onRetry={submit}
                />
              ) : (
                <Welcome mode={mode} />
              )}
            </div>
            <Composer
              key={`composer-${chat.active.id}`}
              value={draft}
              onChange={setDraft}
              onSubmit={() => submit()}
              pending={chat.pending}
              onCancel={chat.cancel}
              mode={mode}
              onMode={chooseMode}
              category={category}
              onCategory={setCategory}
            />
            {!chat.active.messages.length && (
              <StarterPrompts
                onSelect={(prompt) => {
                  setDraft(prompt);
                  document.querySelector("textarea")?.focus();
                }}
              />
            )}
          </main>
          {sourcesOpen && (
            <ContextPanel
              onClose={() => setSourcesOpen(false)}
              latest={latest}
              onSearch={() => chooseMode("search")}
            />
          )}
        </div>
      </div>
      {settingsOpen && (
        <SettingsDialog
          health={health}
          pending={chat.pending}
          onClear={chat.clear}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  );
}

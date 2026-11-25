import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import RouterDemo from "./RouterDemo.jsx";
import "./styles/theme.css";
import "./styles/layout.css";
import "./styles/chat.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {new URLSearchParams(window.location.search).get("vista") === "enrutador"
      ? <RouterDemo />
      : <App />}
  </React.StrictMode>,
);

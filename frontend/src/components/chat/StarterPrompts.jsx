import { suggestions } from "../../data/support.js";

export default function StarterPrompts({ onSelect }) {
  return (
    <div className="starter-prompts" aria-label="Consultas sugeridas">
      {suggestions.map(({ label, prompt }) => (
        <button key={label} onClick={() => onSelect(prompt)}>
          {label}
        </button>
      ))}
    </div>
  );
}

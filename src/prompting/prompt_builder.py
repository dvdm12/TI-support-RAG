from pathlib import Path
from typing import Iterable

from .token_budget import MAX_PROMPT_TOKENS, count_tokens


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT / "prompts"


class PromptBuilder:
    """Construye el system prompt a partir de módulos Markdown."""

    def __init__(self, prompts_dir: Path | str = PROMPTS_DIR) -> None:
        self.prompts_dir = Path(prompts_dir)

    def _read_module(self, relative_path: str) -> str:
        path = self.prompts_dir / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Módulo no encontrado: {path}")

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"El módulo está vacío: {path}")

        return content

    def build(self, modules: Iterable[str]) -> str:
        """Concatena módulos en el orden recibido y valida el presupuesto."""
        module_list = list(modules)
        if not module_list:
            raise ValueError("Debe proporcionarse al menos un módulo.")

        parts = [self._read_module(module) for module in module_list]
        prompt = "\n\n".join(parts)

        tokens = count_tokens(prompt)
        if tokens > MAX_PROMPT_TOKENS:
            raise ValueError(
                f"El prompt supera el presupuesto: {tokens} tokens > "
                f"{MAX_PROMPT_TOKENS}."
            )

        return prompt
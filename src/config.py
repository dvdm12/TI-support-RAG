
from pathlib import Path
import os
import re

from dotenv import load_dotenv


MODEL = "openai/gpt-oss-20b"
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def find_project_root() -> Path:
    """Busca la raíz del proyecto a partir del directorio actual."""
    current = Path.cwd().resolve()

    for path in [current, *current.parents]:
        if (path / "prompts").is_dir():
            return path

    raise FileNotFoundError(
        "No se encontró la raíz del proyecto TI-support-RAG."
    )


def find_latest_prompt(prompts_dir: Path) -> tuple[str, Path]:
    """
    Encuentra el prompt system_vN.md con la versión numérica más alta.
    """
    pattern = re.compile(r"^system_v(\d+)\.md$")

    versions = []

    for path in prompts_dir.glob("system_v*.md"):
        match = pattern.match(path.name)

        if match:
            version = int(match.group(1))
            versions.append((version, path))

    if not versions:
        raise FileNotFoundError(
            f"No se encontraron prompts versionados en: {prompts_dir}"
        )

    version, prompt_path = max(versions, key=lambda item: item[0])

    return f"system_v{version}", prompt_path


PROJECT_ROOT = find_project_root()

PROMPTS_DIR = PROJECT_ROOT / "prompts"
PROMPT_VERSION, PROMPT_PATH = find_latest_prompt(PROMPTS_DIR)

TEST_PATH = PROJECT_ROOT / "cases" / "test_cases.json"
RESULTS_PATH = PROJECT_ROOT / "docs" / "results.json"

load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "No se encontró GROQ_API_KEY en el archivo .env."
    )
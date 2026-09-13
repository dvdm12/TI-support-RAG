from src.prompting.prompt_builder import PromptBuilder
from src.prompting.token_budget import count_tokens, MAX_PROMPT_TOKENS


def main():
    print("=== PRUEBA PROMPT BUILDER ===\n")

    builder = PromptBuilder()

    modules = [
        "base/role.md",
        "base/safety.md",
        "base/output.md",
    ]

    prompt = builder.build(modules)
    tokens = count_tokens(prompt)

    print("Módulos utilizados:")
    for module in modules:
        print(f"  - {module}")

    print("\n--- RESULTADO ---")
    print(f"Tokens: {tokens}")
    print(f"Límite: {MAX_PROMPT_TOKENS}")
    print(f"Dentro del presupuesto: {tokens <= MAX_PROMPT_TOKENS}")

    print("\n--- PROMPT GENERADO ---")
    print(prompt)


if __name__ == "__main__":
    main()
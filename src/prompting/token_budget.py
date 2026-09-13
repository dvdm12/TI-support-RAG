from transformers import AutoTokenizer

MODEL_NAME = "openai/gpt-oss-20b"
MAX_PROMPT_TOKENS = 1000


tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def count_tokens(text: str) -> int:
    """
    Cuenta los tokens de un texto utilizando
    el tokenizador de openai/gpt-oss-20b.
    """
    if not isinstance(text, str):
        raise TypeError("text debe ser un string.")

    return len(
        tokenizer.encode(
            text,
            add_special_tokens=False,
        )
    )


def within_budget(
    text: str,
    max_tokens: int = MAX_PROMPT_TOKENS,
) -> bool:
    """
    Determina si el texto está dentro del presupuesto.
    """
    return count_tokens(text) <= max_tokens
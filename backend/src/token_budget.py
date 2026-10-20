"""GPT-OSS input budget: actual tokenizer, schema and conservative framing."""
import json
import os
from functools import lru_cache
from pathlib import Path

INPUT_TOKEN_LIMIT = 1000
FRAMING_RESERVE = 96


class InputBudgetError(ValueError):
    pass


@lru_cache(maxsize=1)
def encoding():
    import tiktoken
    os.environ.setdefault('TIKTOKEN_CACHE_DIR',str(Path(__file__).resolve().parents[1]/'.cache/tiktoken'))
    return tiktoken.get_encoding('o200k_harmony')


def input_budget(payload):
    count=lambda text:len(encoding().encode(text,disallowed_special=()))
    content=sum(count(message['content']) for message in payload['messages'])
    schema=count(json.dumps(payload['response_format'],ensure_ascii=False,separators=(',',':'))) if payload.get('response_format') else 0
    return {'content_tokens':content,'schema_tokens':schema,'framing_reserve':FRAMING_RESERVE,
            'total_tokens':content+schema+FRAMING_RESERVE,'limit':INPUT_TOKEN_LIMIT,
            'tokenizer':'o200k_harmony','provider_framing':'conservative_reserve'}


def enforce_input_budget(payload):
    budget=input_budget(payload)
    if budget['total_tokens']>INPUT_TOKEN_LIMIT:
        raise InputBudgetError(f"Entrada excede {INPUT_TOKEN_LIMIT} tokens ({budget['total_tokens']} con reserva y esquema); no se envió la petición.")
    return budget

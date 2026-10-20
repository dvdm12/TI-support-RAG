"""Spanish lexical ranking, independent of case IDs and document sections."""
import math
import re
import unicodedata
from collections import Counter

STOP = set('a al algo ante como con cual cuando de del debe debo el en es esta este hacer la las lo los me mi no para por que segun se si sin solo su sus tengo un una y indica manual necesito dame'.split())


def tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    terms = [t for t in re.findall(r'[a-z0-9]+', text) if len(t) > 2 and t not in STOP]
    return [t[:-1] if len(t) > 4 and t.endswith('s') else t for t in terms]


def rank(query, candidates, k=10):
    documents = [Counter(tokens(c.content)) for c in candidates]
    terms = set(tokens(query))
    average = sum(map(lambda d: sum(d.values()), documents)) / max(len(documents), 1)
    frequencies = {term: sum(term in doc for doc in documents) for term in terms}
    scored = []
    for candidate, document in zip(candidates, documents):
        score = 0.0
        for term in terms:
            count = document[term]
            if count:
                idf = math.log(1 + (len(documents) - frequencies[term] + .5) / (frequencies[term] + .5))
                score += idf * count * 2.5 / (count + 1.5 * (.25 + .75 * sum(document.values()) / max(average, 1)))
        if score:
            scored.append((score, candidate))
    return [candidate for _, candidate in sorted(scored, key=lambda pair: (-pair[0], pair[1].chunk_id))[:k]]

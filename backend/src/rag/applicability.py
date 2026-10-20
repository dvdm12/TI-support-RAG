"""Conservative incident-condition guard, without case IDs or section names."""
import re
import unicodedata


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def password_route_relevant(question):
    text = normalized(question)
    no_opening = (re.search(r'\bno\b.{0,18}\b(?:abri|abierto|abrir|abro|hice clic|hecho clic)\b', text)
                  or re.search(r'\bsin abrir\b', text))
    if not no_opening or not re.search(r'\b(?:correo|mensaje|enlace|adjunto)\b', text):
        return True
    # An exposure reported through another channel still makes account response
    # pertinent; don't confuse a negative opening statement with that report.
    exposure = False
    for match in re.finditer(r'\b(?:introduje|ingrese|escribi|comparti|revele|proporcione)\b.{0,45}\b(?:contrasena|clave|codigo)\b', text):
        if not re.search(r'\bno\b.{0,15}$', text[max(0,match.start()-20):match.start()]):
            exposure = True
    explicit_request = re.search(r'\b(?:olvide|recuperar|restablecer|cambiar)\b.{0,30}\b(?:contrasena|clave)\b', text)
    return exposure or bool(explicit_request)


def applicable_candidates(question, candidates, *, physical_risk=False):
    included, omitted = [], []
    for candidate in candidates:
        section = normalized(candidate.metadata.get('section',''))
        content = normalized(candidate.content)
        reason = None
        if not password_route_relevant(question) and re.search(r'credencial.*expuest|recuper.*contrasena|contrasena.*recuper', section):
            reason = 'password_route_not_requested_or_exposed'
        if physical_risk and re.search(r'conexion de alimentacion|estado externo del cable|adaptador', content) and not re.search(r'humo|olor a quemado|interrumpe el uso', content):
            reason = 'ordinary_power_checks_not_applicable_during_physical_risk'
        if reason:
            omitted.append({'chunk_id':candidate.chunk_id,'reason':reason})
        else:
            included.append(candidate)
    return included, omitted


def applicability_issues(question, response):
    advice = re.search(r'\b(?:cambi\w*|recuper\w*|restablec\w*)\b.{0,55}\b(?:contrasena|clave)\b', normalized(response))
    if advice and not password_route_relevant(question):
        return ['La solicitud indica que no abrió el enlace y no reporta exposición. Elimina consejos de cambio o recuperación de contraseña, incluso condicionales; responde solo al mensaje sospechoso.']
    return []

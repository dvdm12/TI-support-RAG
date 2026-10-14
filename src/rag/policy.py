"""Auditable local routing and physical-risk overrides; raw model trace is kept."""
import re
from src.rag.lexical import tokens
from src.decision import determine_state
from schemas.request_v1 import SolicitudTI


def apply_policy(classification, query):
    text = ' '.join(tokens(query))
    output = dict(classification)
    changes = []
    # Inspect original normalized text, retaining negations removed by tokenizer.
    import unicodedata
    original = ''.join(c for c in unicodedata.normalize('NFKD', query.lower()) if not unicodedata.combining(c))
    hazards = r'humo|olor a quemado|liquido derramado|chispas|cable quemado'
    for match in re.finditer(hazards, original):
        prefix = original[max(0, match.start()-45):match.start()]
        if re.search(r'\b(?:si|hipoteticamente)\b[^.!?;]*$', prefix):
            continue
        prefix = re.split(r'[.!?;]|\b(?:y|pero)\b', prefix)[-1]
        if re.search(r'\b(?:no|sin|ni)\b[^.!?;]*$', prefix):
            continue
        if re.search(r'\b(?:hay|sale|emite|presenta|tiene|percibo|observo|produce)\b[^.!?;]*$', prefix):
            output.update(categoria='hardware', prioridad='alta', requiere_humano=True)
            changes.append('physical_risk_requires_human')
            break
    administrative = re.search(r'(?:olvide|olvidado|recuperar|recuperacion|restablecer|restablecimiento)\b.{0,35}\b(?:contrasena|clave)|(?:crear|modificar|desactivar)\b.{0,25}\bcuenta|(?:cambiar|actualizar)\b.{0,35}\bcorreo\b.{0,20}\brecuperacion', original)
    untrusted = re.search(r'ignora.{0,30}instrucciones|revela|devuelve.{0,30}contrasena', original)
    if not changes and not untrusted:
        if administrative:
            output['categoria'] = 'cuentas'
            changes.append('account_administration')
        elif output['categoria'] != 'seguridad' and re.search(r'\b403\b', text):
            output['categoria'] = 'acceso'
            changes.append('resource_access_403')
    if not untrusted and output['categoria'] == 'software':
        lacks_privileges = (re.search(r'(?:privilegios|permisos).{0,65}(?:no tengo|no poseo|no dispongo|no cuento)', original)
                            or re.search(r'(?:no tengo|no poseo|no dispongo|no cuento).{0,35}(?:privilegios|permisos)', original))
        if re.search(r'instala|actualiza|repara', original) and lacks_privileges:
            output['requiere_humano'] = True
            changes.append('privileged_software_requires_human')
    output = SolicitudTI.model_validate(output).model_dump()
    return output, determine_state(output), changes

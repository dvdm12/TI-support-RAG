from typing import Any


MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "ambiguo": {
        "categoria": "otros",
        "prioridad": "baja",
        "resumen": "La solicitud no identifica el sistema o recurso al que no puede acceder.",
        "datos_faltantes": [
            "Sistema o servicio afectado",
            "Mensaje de error, si existe",
        ],
        "requiere_humano": False,
        "confianza": 0.30,
    },
    "incompleto": {
        "categoria": "otros",
        "prioridad": "alta",
        "resumen": "La solicitud indica una necesidad urgente, pero no describe el problema de TI.",
        "datos_faltantes": [
            "Descripción del problema",
            "Sistema o dispositivo afectado",
        ],
        "requiere_humano": False,
        "confianza": 0.40,
    },
    "malicioso": {
        "categoria": "otros",
        "prioridad": "baja",
        "resumen": "La solicitud intenta obtener información interna del sistema.",
        "datos_faltantes": [],
        "requiere_humano": True,
        "confianza": 0.95,
    },
    "fuera_de_alcance": {
        "categoria": "otros",
        "prioridad": "baja",
        "resumen": "La solicitud está fuera del alcance de la Mesa de Ayuda TI.",
        "datos_faltantes": [],
        "requiere_humano": True,
        "confianza": 0.98,
    },
}


def mock_response(case_type: str) -> dict[str, Any]:
    """
    Devuelve una respuesta simulada para un tipo de caso controlado.

    Se utiliza únicamente para pruebas, sin realizar una llamada a Groq.
    """
    if case_type not in MOCK_RESPONSES:
        raise ValueError(f"Tipo de caso sin mock definido: {case_type}")

    return MOCK_RESPONSES[case_type].copy()


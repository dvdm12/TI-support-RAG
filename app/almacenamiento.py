"""Historial de conversaciones por usuario en Supabase.

Cada función recibe el cliente ya autenticado; la identidad la resuelve RLS
a partir del JWT de sesión. No existe cliente global: app.py crea uno por
sesión de Gradio y lo descarta al cerrar sesión.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from supabase import Client, ClientOptions, create_client


# ── Tipos ────────────────────────────────────────────────────────────────────

@dataclass
class Conversacion:
    id: str
    titulo: str
    actualizada_en: str


@dataclass
class Mensaje:
    id: str
    rol: str          # 'usuario' | 'asistente'
    contenido: str
    fuentes: list[dict] = field(default_factory=list)
    creado_en: str = ""


class AlmacenamientoError(RuntimeError):
    pass


# ── Cliente ───────────────────────────────────────────────────────────────────

def construir_cliente() -> Client:
    """Crea un cliente Supabase sin autenticar usando las variables de entorno."""
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise AlmacenamientoError(
            "Define SUPABASE_URL y SUPABASE_PUBLISHABLE_KEY en el entorno."
        )
    return create_client(url, key, options=ClientOptions(persist_session=False))


def autenticar(client: Client, email: str, password: str) -> str:
    """Inicia sesión; devuelve el user_id. Lanza AlmacenamientoError si falla."""
    try:
        result = client.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        if not result.user or not result.session:
            raise AlmacenamientoError("Credenciales incorrectas o sesión no creada.")
        return result.user.id
    except AlmacenamientoError:
        raise
    except Exception:
        raise AlmacenamientoError("No se pudo autenticar con Supabase.") from None


def cerrar_sesion(client: Client) -> None:
    try:
        client.auth.sign_out()
    except Exception:
        pass


# ── Conversaciones ────────────────────────────────────────────────────────────

def crear_conversacion(client: Client, titulo: str = "Nueva conversación") -> str:
    """Inserta una conversación para el usuario activo; devuelve su id."""
    titulo = titulo.strip() or "Nueva conversación"
    if len(titulo) > 200:
        titulo = titulo[:197] + "..."
    try:
        rows = (
            client.table("conversaciones")
            .insert({"titulo": titulo})
            .execute()
            .data
        )
        if not rows:
            raise AlmacenamientoError("Supabase no devolvió la fila insertada.")
        return rows[0]["id"]
    except AlmacenamientoError:
        raise
    except Exception:
        raise AlmacenamientoError("No se pudo crear la conversación.") from None


def listar_conversaciones(client: Client) -> list[Conversacion]:
    """Devuelve las conversaciones del usuario activo, más recientes primero."""
    try:
        rows = (
            client.table("conversaciones")
            .select("id, titulo, actualizada_en")
            .order("actualizada_en", desc=True)
            .execute()
            .data
        )
        return [
            Conversacion(id=r["id"], titulo=r["titulo"], actualizada_en=r["actualizada_en"])
            for r in (rows or [])
        ]
    except Exception:
        raise AlmacenamientoError("No se pudieron listar las conversaciones.") from None


def renombrar_conversacion(client: Client, conversacion_id: str, nuevo_titulo: str) -> None:
    nuevo_titulo = nuevo_titulo.strip() or "Sin título"
    try:
        client.table("conversaciones").update({"titulo": nuevo_titulo}).eq(
            "id", conversacion_id
        ).execute()
    except Exception:
        raise AlmacenamientoError("No se pudo renombrar la conversación.") from None


def eliminar_conversacion(client: Client, conversacion_id: str) -> None:
    """Borra la conversación y sus mensajes (cascade definido en la migración)."""
    try:
        client.table("conversaciones").delete().eq("id", conversacion_id).execute()
    except Exception:
        raise AlmacenamientoError("No se pudo eliminar la conversación.") from None


# ── Mensajes ──────────────────────────────────────────────────────────────────

def cargar_mensajes(client: Client, conversacion_id: str) -> list[Mensaje]:
    """Devuelve los mensajes de una conversación en orden de creación."""
    try:
        rows = (
            client.table("mensajes")
            .select("id, rol, contenido, fuentes, creado_en")
            .eq("conversacion_id", conversacion_id)
            .order("creado_en", desc=False)
            .execute()
            .data
        )
        return [
            Mensaje(
                id=r["id"],
                rol=r["rol"],
                contenido=r["contenido"],
                fuentes=r.get("fuentes") or [],
                creado_en=r.get("creado_en", ""),
            )
            for r in (rows or [])
        ]
    except Exception:
        raise AlmacenamientoError("No se pudieron cargar los mensajes.") from None


def guardar_turno(
    client: Client,
    conversacion_id: str,
    pregunta: str,
    respuesta: str,
    fuentes: list[dict[str, Any]] | None = None,
) -> None:
    """Persiste un turno completo: mensaje del usuario y respuesta del asistente."""
    filas = [
        {"conversacion_id": conversacion_id, "rol": "usuario",    "contenido": pregunta,  "fuentes": []},
        {"conversacion_id": conversacion_id, "rol": "asistente",  "contenido": respuesta, "fuentes": fuentes or []},
    ]
    try:
        client.table("mensajes").insert(filas).execute()
    except Exception:
        raise AlmacenamientoError("No se pudo guardar el turno en Supabase.") from None


# ── Historial para el modelo ──────────────────────────────────────────────────

def historial_como_pares(mensajes: list[Mensaje]) -> list[tuple[str, str]]:
    """Convierte la lista de mensajes en pares (usuario, asistente) para Gradio Chatbot."""
    pares: list[tuple[str, str]] = []
    pendiente: str | None = None
    for m in mensajes:
        if m.rol == "usuario":
            pendiente = m.contenido
        elif m.rol == "asistente" and pendiente is not None:
            pares.append((pendiente, m.contenido))
            pendiente = None
    return pares

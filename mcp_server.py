"""
Ruta: mcp_server.py
Descripción: Servidor Model Context Protocol (MCP) de Argon 4 // Hermes Edition.
Expone la memoria SQLite, Notion, Agenda Local, Telemetría y WhatsApp a clientes MCP (VS Code / Antigravity).
"""
from typing import Any, Callable, Dict, List

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
except ImportError:
    class FastMCP:  # type: ignore[no-redef]
        """Respaldo ligero para evitar errores de importación si 'mcp' no está instalado en .venv."""
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: List[Callable[..., Any]] = []

        def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self.tools.append(func)
                return func
            return decorator

        def run(self) -> None:
            print(f"[{self.name}] Instala el paquete oficial ejecutando: .venv\\Scripts\\pip install mcp")

from config import Config
from modules.advanced_skills import AdvancedSkills
from modules.notion_bridge import NotionBridge
from modules.productivity_tools import ProductivityTools
from modules.system_tasks import SystemTasks
from modules.whatsapp_bridge import WhatsAppBridge

mcp = FastMCP("Argon4-Hermes-MCP")

skills = AdvancedSkills()
notion = NotionBridge()
productivity = ProductivityTools()
tasks = SystemTasks()
whatsapp = WhatsAppBridge()


@mcp.tool()
def remember_fact(note: str, category: str = "Proyecto") -> Dict[str, Any]:
    """Guarda un hecho o nota técnica en la memoria SQLite permanente de Argon 4."""
    return skills.save_memory(note, category=category)


@mcp.tool()
def recall_facts(limit: int = 10) -> List[Dict[str, Any]]:
    """Recupera los recuerdos almacenados en la memoria SQLite de Argon 4."""
    return skills.recall_memories(limit=limit)


@mcp.tool()
def get_hardware_telemetry() -> Dict[str, Any]:
    """Devuelve métricas en tiempo real de CPU, RAM, espacio en disco y batería."""
    return tasks.get_system_status()


@mcp.tool()
def get_top_ram_processes(limit: int = 5) -> Dict[str, Any]:
    """Lista los procesos de Windows 11 que consumen más memoria RAM."""
    return skills.get_top_processes(limit=limit)


@mcp.tool()
def list_unified_tasks() -> List[Dict[str, Any]]:
    """Obtiene la agenda combinada (Calendario Local JSON + Notion API)."""
    return notion.fetch_tasks(limit=5) + productivity.list_calendar_events()


@mcp.tool()
def create_unified_task(title: str) -> Dict[str, Any]:
    """Crea un pendiente simultáneamente en la agenda local y en Notion API."""
    local_res = productivity.add_calendar_event(title)
    notion_res = notion.create_task(title)
    return {"local": local_res, "notion": notion_res}


@mcp.tool()
def audit_project_code(relative_path: str) -> Dict[str, Any]:
    """Analiza el árbol AST y devuelve un fragmento seguro de un archivo del proyecto."""
    return productivity.analyze_code_file(relative_path)


@mcp.tool()
def dispatch_whatsapp(message: str, phone: str = "") -> Dict[str, Any]:
    """Envía un mensaje por el puente de WhatsApp de Argon 4."""
    target = phone.strip() if phone else Config.DEFAULT_TARGET_PHONE
    return whatsapp.send_message(target, message)


if __name__ == "__main__":
    mcp.run()
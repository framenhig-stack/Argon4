"""
Ruta: main_agent.py
Descripción: Orquestador Definitivo Argon 4 // Hermes Edition v4.5 SOTA.
Integra: Trazabilidad de Pasos en Vivo (estilo ChatGPT), Visión Multimodal de Pantalla con Gemini,
HUD Holográfico 60 FPS, Voz Neuronal Grave (-14Hz) sin cortes, Memoria SQLite y Notion API.
"""
import base64
import logging
import os
import re
import subprocess
import threading
import time
import webbrowser
from typing import Dict, Any, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, request, jsonify, Response

from config import Config, write_telemetry_snapshot
from modules.voice_engine import VoiceEngine
from modules.system_tasks import SystemTasks
from modules.whatsapp_bridge import WhatsAppBridge
from modules.voip_caller import VoIPCaller
from modules.productivity_tools import ProductivityTools
from modules.advanced_skills import AdvancedSkills
from modules.notion_bridge import NotionBridge
from modules.tool_router import AgentToolRouter
from modules.hud_template import HUD_HTML


class PollingLogFilter(logging.Filter):
    """Oculta únicamente el polling de alta frecuencia de Rainmeter y el HUD."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "GET /telemetry" not in msg and "GET /api/state" not in msg


logger = logging.getLogger("MainAgent")
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addFilter(PollingLogFilter())


class ArgonHermesOrchestrator:
    def __init__(self) -> None:
        self.state = "IDLE"
        self.active_tool = "NONE"
        self.last_action = "Núcleo Argon 4 // Hermes inicializado con Google Gemini."
        self.handsfree = False
        self.ui_logs: List[Dict[str, str]] = []
        self.live_steps: List[Dict[str, str]] = []
        self.is_processing: bool = False
        self.task_start_ts: float = 0.0
        self._state_lock = threading.RLock()

        # Pool de conexiones HTTP persistentes para baja latencia
        self.http = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=2, backoff_factor=0.2)
        )
        self.http.mount("http://", adapter)
        self.http.mount("https://", adapter)

        self.voice = VoiceEngine(on_state_change=self._on_state_change)
        self.tasks = SystemTasks()
        self.whatsapp = WhatsAppBridge()
        self.voip = VoIPCaller()
        self.productivity = ProductivityTools()
        self.skills = AdvancedSkills()
        self.notion = NotionBridge()

        self.notion.export_rainmeter_skin()

        self.active_model: str = Config.OLLAMA_MODEL
        self.gemini_online: bool = bool(Config.GEMINI_API_KEY)
        self.ollama_online: bool = self._detect_ollama()

        self.system_prompt = (
            f"Eres {Config.AGENT_NAME} (Edición Hermes), un sistema agéntico multimodal avanzado estilo J.A.R.V.I.S. "
            "impulsado por Google Gemini y ejecutándose en Windows 11 junto a Franco. Tu voz es grave, serena y futurista. "
            "Cuentas con visión de pantalla en tiempo real, memoria persistente SQLite, agenda sincronizada con Notion, "
            "triaje de correo y WhatsApp. Responde siempre en español con precisión ejecutiva en 1 a 3 oraciones claras."
        )
        self.chat_history: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        past_turns = self.skills.load_recent_conversation(limit=8)
        if past_turns:
            self.chat_history.extend(past_turns)

        self.router = AgentToolRouter(self)
        write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    # ---------------- TRAZABILIDAD EN VIVO (ESTILO CHATGPT) ----------------
    def start_live_trace(self, initial_label: str) -> None:
        with self._state_lock:
            self.is_processing = True
            self.task_start_ts = time.time()
            self.live_steps = [{
                "label": initial_label,
                "status": "running",
                "elapsed": "0.0s"
            }]

    def push_live_step(self, label: str, status: str = "running") -> None:
        with self._state_lock:
            now_elapsed = f"{round(time.time() - self.task_start_ts, 1)}s" if self.task_start_ts else "0.1s"
            for step in self.live_steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["elapsed"] = now_elapsed
            self.live_steps.append({
                "label": label,
                "status": status,
                "elapsed": now_elapsed
            })

    def finish_live_trace(self) -> None:
        with self._state_lock:
            now_elapsed = f"{round(time.time() - self.task_start_ts, 1)}s" if self.task_start_ts else "0.1s"
            for step in self.live_steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["elapsed"] = now_elapsed
            self.is_processing = False

    def _on_state_change(self, new_state: str) -> None:
        with self._state_lock:
            self.state = new_state
            write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    def _set_tool_telemetry(self, tool_name: str, description: str) -> None:
        self.push_live_step(f"[{tool_name}] {description}")
        with self._state_lock:
            self.active_tool = tool_name
            self.last_action = description
            self.state = "TOOL_EXEC" if tool_name != "NONE" else "IDLE"
            write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    def _detect_ollama(self) -> bool:
        try:
            resp = self.http.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", []) if m.get("name")]
                if models:
                    self.active_model = Config.OLLAMA_MODEL if Config.OLLAMA_MODEL in models else models[0]
                    return True
        except requests.RequestException:
            pass
        return False

    def add_log(self, sender: str, text: str, tag: str = "agent") -> None:
        with self._state_lock:
            self.ui_logs.append({"sender": sender, "text": text, "tag": tag})
            if len(self.ui_logs) > 60:
                self.ui_logs = self.ui_logs[-60:]

    def respond(self, text: str) -> None:
        self.push_live_step("Sintetizando voz neuronal grave (-14Hz)...", status="done")
        self.finish_live_trace()
        with self._state_lock:
            self.last_action = text
            self.active_tool = "VOICE_SYNTH"
            write_telemetry_snapshot("SPEAKING", self.active_tool, self.last_action)
        self.add_log(Config.AGENT_NAME.upper(), text, "agent")
        self.skills.log_conversation_turn("assistant", text)
        self.voice.speak(text)
        with self._state_lock:
            self.active_tool = "NONE"
            self.state = "IDLE"
            write_telemetry_snapshot("IDLE", self.active_tool, self.last_action)

    # ---------------- VISIÓN MULTIMODAL DE PANTALLA (GEMINI VISION) ----------------
    def analyze_screen_with_gemini(self, user_prompt: str) -> str:
        """Captura la pantalla actual de Windows 11 y la envía a Google Gemini Vision."""
        self._set_tool_telemetry("GEMINI_VISION", "Capturando pantalla en alta resolución...")
        snap = self.tasks.take_screenshot()
        if not snap.get("ok"):
            return f"No pude capturar la pantalla: {snap.get('error')}"

        filepath = snap["filepath"]
        if not self.gemini_online:
            return f"Captura guardada en {filepath}. Configura GEMINI_API_KEY para análisis visual."

        try:
            with open(filepath, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode("utf-8")

            self._set_tool_telemetry("GEMINI_VISION", f"Inspeccionando imagen con {Config.GEMINI_MODEL}...")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
            )
            prompt_text = (
                f"El usuario Franco te pide analizar su pantalla actual en Windows 11. "
                f"Solicitud: '{user_prompt}'. Responde en español de forma directa, técnica y ejecutiva."
            )
            payload = {
                "systemInstruction": {"parts": [{"text": self.system_prompt}]},
                "contents": [{
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {"inlineData": {"mimeType": "image/png", "data": b64_img}}
                    ]
                }],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 450}
            }
            resp = self.http.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if reply:
                        return reply
            return f"Gemini Vision respondió con código {resp.status_code}."
        except Exception as exc:
            logger.error(f"Error en Gemini Vision: {exc}")
            return f"Ocurrió un error al analizar la pantalla: {exc}"

    def ask_brain(self, user_prompt: str, extra_context: str = "") -> str:
        """Consulta a Google Gemini como motor principal y usa Ollama como respaldo local."""
        self.push_live_step("Consultando memoria cognitiva SQLite...")
        memories = self.skills.recall_memories(limit=10)
        mem_block = ""
        if memories:
            facts = "; ".join([f"[{m['category']}] {m['note']}" for m in memories])
            mem_block = f"\n[MEMORIA PERMANENTE SOBRE FRANCO: {facts}]"

        full_user_msg = f"{user_prompt}{mem_block}"
        if extra_context:
            full_user_msg += f"\n{extra_context}"

        with self._state_lock:
            self.chat_history.append({"role": "user", "content": full_user_msg})
            if len(self.chat_history) > 15:
                self.chat_history = [self.chat_history[0]] + self.chat_history[-14:]
            history_snapshot = list(self.chat_history)

        # 1. Motor Principal: Google Gemini API
        if self.gemini_online:
            try:
                self._set_tool_telemetry("GOOGLE_GEMINI", f"Razonando con {Config.GEMINI_MODEL}...")
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
                )
                gemini_contents = []
                for m in history_snapshot:
                    role = m.get("role")
                    if role == "user":
                        gemini_contents.append({"role": "user", "parts": [{"text": m["content"]}]})
                    elif role == "assistant":
                        gemini_contents.append({"role": "model", "parts": [{"text": m["content"]}]})

                payload = {
                    "systemInstruction": {"parts": [{"text": self.system_prompt}]},
                    "contents": gemini_contents,
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 450,
                    },
                }
                resp = self.http.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        reply = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                        if reply:
                            with self._state_lock:
                                self.chat_history.append({"role": "assistant", "content": reply})
                            return reply
                else:
                    logger.warning(f"Gemini API HTTP {resp.status_code}: {resp.text[:160]}")
            except Exception as exc:
                logger.warning(f"Fallo en Google Gemini, conmutando a Ollama local: {exc}")
            finally:
                with self._state_lock:
                    self.state = "IDLE"

        # 2. Motor de Respaldo Offline: Ollama Local
        if not self.ollama_online:
            self.ollama_online = self._detect_ollama()
            if not self.ollama_online:
                return "Configura tu GEMINI_API_KEY en el archivo .env o inicia el servidor local Ollama."

        try:
            self._set_tool_telemetry("OLLAMA_LLM", f"Inferencia en {self.active_model}...")
            payload = {
                "model": self.active_model,
                "messages": history_snapshot,
                "stream": False
            }
            resp = self.http.post(
                f"{Config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT
            )
            if resp.status_code == 200:
                reply = resp.json().get("message", {}).get("content", "").strip()
                if reply:
                    with self._state_lock:
                        self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
        except Exception as exc:
            logger.error(f"Error consultando Ollama: {exc}")
        finally:
            with self._state_lock:
                self.state = "IDLE"
        return "Tuve una breve latencia en el motor neuronal. ¿Me lo repites?"

    def get_unified_calendar(self) -> List[Dict[str, Any]]:
        """Combina los pendientes locales con las tareas de Notion API si están activas."""
        local_events = self.productivity.list_calendar_events()
        notion_events = self.notion.fetch_tasks(limit=4)
        return notion_events + local_events

    def process_command(self, user_text: str) -> None:
        self.start_live_trace(f"Analizando instrucción: '{user_text[:45]}...'")
        text = user_text.lower().strip()
        self.skills.log_conversation_turn("user", user_text)
        self.skills.auto_extract_memory(user_text)

        # 0. VISIÓN MULTIMODAL DE PANTALLA (SOTA SCREEN AWARENESS)
        if any(k in text for k in [
            "mira mi pantalla", "analiza mi pantalla", "qué ves en mi pantalla",
            "que ves en mi pantalla", "captura de pantalla", "qué hay en mi pantalla"
        ]):
            reply = self.analyze_screen_with_gemini(user_text)
            self.respond(reply)
            return

        # Si el usuario encadena acciones múltiples ("y", "luego", "además"), usar el ToolRouter paralelo
        if any(conn in text for conn in [" y ", " luego ", " además ", " ademas "]):
            self.push_live_step("Planificando ejecución paralela multi-herramienta...")
            routed_compound = self.router.route_and_execute(user_text)
            if routed_compound:
                self.respond(routed_compound)
                return

        # 1. MEMORIA PERSISTENTE
        if any(k in text for k in ["recuerda que", "memoriza que", "guarda en tu memoria", "no olvides que"]):
            self._set_tool_telemetry("SQLITE_MEMORY", "Guardando recuerdo permanente en SQLite")
            cleaned = re.sub(
                r"^(recuerda que|memoriza que|guarda en tu memoria|no olvides que)\s*:?\s*",
                "",
                user_text,
                flags=re.IGNORECASE
            ).strip()
            res = self.skills.save_memory(cleaned, category="Clave")
            self.respond(f"Registrado en mi núcleo de memoria permanente: {cleaned}." if res["ok"] else res["error"])
            return

        if any(k in text for k in ["qué recuerdas", "que recuerdas", "qué sabes de mí", "que sabes de mi"]):
            self._set_tool_telemetry("SQLITE_MEMORY", "Consultando recuerdos permanentes")
            mems = self.skills.recall_memories(limit=6)
            if not mems:
                self.respond("Aún estamos construyendo mi base de recuerdos permanentes contigo.")
            else:
                notes = ". ".join([m["note"] for m in mems])
                self.respond(f"Tengo presente en mi memoria permanente lo siguiente: {notes}.")
            return

        # 2. ACCESO DIRECTO Y AUTO-ARRANQUE WINDOWS 11
        if any(k in text for k in ["acceso directo", "arrancar con windows", "inicio automático", "inicio automatico"]):
            self._set_tool_telemetry("WIN11_DEPLOY", "Configurando acceso directo / inicio")
            enable_boot = "arrancar" in text or "inicio" in text
            res = self.skills.setup_windows_integration(enable_startup=enable_boot)
            self.respond(res["message"] if res["ok"] else res["error"])
            return

        # 3. INTELIGENCIA DE PORTAPAPELES
        if any(k in text for k in ["portapapeles", "lo que copié", "lo que copie"]):
            self._set_tool_telemetry("CLIPBOARD_AI", "Extrayendo contenido del portapapeles")
            res = self.skills.read_clipboard()
            if not res["ok"]:
                self.respond(res["error"])
                return
            reply = self.ask_brain(
                "Analiza lo que el usuario tiene en su portapapeles y dale una respuesta directa y útil:",
                extra_context=f"[PORTAPAPELES]:\n{res['content']}"
            )
            self.respond(reply)
            return

        # 4. BÚSQUEDA WEB EN TIEMPO REAL
        if any(k in text for k in ["busca en internet", "buscar en internet", "noticias de", "investiga sobre"]):
            query = re.sub(
                r"^(busca en internet|buscar en internet|investiga sobre)\s*:?\s*",
                "",
                user_text,
                flags=re.IGNORECASE
            ).strip() or user_text
            self._set_tool_telemetry("WEB_SEARCH", f"Buscando en vivo: '{query}'")
            web_res = self.skills.search_web(query)
            if web_res["ok"]:
                self.push_live_step("Resultados web obtenidos. Sintetizando hallazgos...")
                reply = self.ask_brain(
                    f"Sintetiza en 2 frases estos resultados web actuales sobre '{query}':",
                    extra_context=web_res["context"]
                )
                self.respond(reply)
            else:
                self.respond(web_res["error"])
            return

        # 5. TELEMETRÍA Y TOP PROCESOS
        if any(k in text for k in ["qué procesos", "que procesos", "consumiendo más ram", "consumiendo mas ram"]):
            self._set_tool_telemetry("PSUTIL_PROC", "Escaneando procesos activos en RAM")
            res = self.skills.get_top_processes()
            self.respond(f"Los procesos más exigentes en memoria son: {res['summary']}." if res["ok"] else res["error"])
            return

        if any(k in text for k in ["estado del sistema", "telemetría", "telemetria"]):
            self._set_tool_telemetry("SYSTEM_STATUS", "Recolectando biometría de hardware")
            res = self.tasks.get_system_status()
            if res["ok"]:
                d = res["data"]
                self.respond(
                    f"Todos los sistemas estables. CPU al {d['cpu_percent']}%, RAM al {d['ram_percent']}% "
                    f"con {d['ram_available_gb']} gigabytes libres y batería al {d['battery_percent']}%."
                )
            return

        # 6. AGENDA HÍBRIDA (LOCAL + NOTION API)
        if any(k in text for k in ["agendar", "agregar pendiente", "nuevo pendiente", "anota en notion"]):
            self._set_tool_telemetry("NOTION_CALENDAR", "Registrando evento en agenda local y Notion API")
            cleaned = re.sub(
                r"^(agendar|agregar pendiente|nuevo pendiente|anota en notion)\s*:?\s*",
                "",
                user_text,
                flags=re.I
            ).strip()
            if cleaned:
                self.productivity.add_calendar_event(cleaned)
                notion_res = self.notion.create_task(cleaned)
                if notion_res.get("ok"):
                    self.respond(f"Evento sincronizado en tu agenda local y en tu base de datos de Notion: {cleaned}.")
                else:
                    self.respond(f"Agendado en tu panel táctico local: {cleaned}.")
                return

        if any(k in text for k in ["calendario", "pendientes", "qué tengo hoy", "que tengo hoy", "notion"]):
            self._set_tool_telemetry("NOTION_CALENDAR", "Sincronizando tareas de Notion y calendario local")
            evs = self.get_unified_calendar()
            if not evs:
                self.respond("No tienes pendientes activos en tu agenda ni en Notion.")
            else:
                titles = ", ".join([f"{e['id']}: {e['title']}" for e in evs[:4]])
                self.respond(f"Tus pendientes activos son: {titles}.")
            return

        # 7. CORREOS Y AUDITORÍA DE CÓDIGO
        if any(k in text for k in ["revisar correo", "revisar correos", "mis correos"]):
            self._set_tool_telemetry("IMAP_MAIL", f"Consultando bandeja {Config.EMAIL_USER}")
            res = self.productivity.check_emails()
            self.respond(res["summary"] if res["ok"] else res["error"])
            return

        if any(k in text for k in ["revisar código", "revisar codigo", "analizar código", "analizar codigo"]):
            file_match = re.search(r"([a-zA-Z0-9_./\\-]+\.(?:py|js|ts|json|txt|md))", user_text)
            target_file = file_match.group(1) if file_match else "main_agent.py"
            self._set_tool_telemetry("AST_CODE_AUDIT", f"Analizando árbol AST de {target_file}")
            res = self.productivity.analyze_code_file(target_file)
            if not res["ok"]:
                self.respond(res["error"])
                return
            reply = self.ask_brain(
                f"Evalúa técnicamente este código ({res['filepath']}, {res['syntax']}):",
                extra_context=res["snippet"]
            )
            self.respond(reply)
            return

        # 8. APLICACIONES, WHATSAPP Y VOIP
        for app_name in ["calculadora", "bloc de notas", "explorador", "terminal"]:
            if f"abrir {app_name}" in text or f"abre la {app_name}" in text:
                self._set_tool_telemetry("OS_SUBPROCESS", f"Lanzando binario de {app_name}")
                res = self.tasks.open_application(app_name)
                self.respond(f"Desplegando {app_name}." if res["ok"] else res["error"])
                return

        if "whatsapp" in text:
            self._set_tool_telemetry("WHATSAPP_BRIDGE", "Preparando despacho de mensaje WhatsApp")
            match = re.search(r"(\+?\d[\d\s\-]{7,}\d).*?(?:diciendo|mensaje|que diga)\s+(.+)", user_text, re.I)
            if match:
                phone, msg = match.group(1).strip(), match.group(2).strip()
            else:
                msg_match = re.search(r"(?:diciendo|mensaje|que diga)\s+(.+)", user_text, re.I)
                phone = Config.DEFAULT_TARGET_PHONE
                msg = msg_match.group(1).strip() if msg_match else ""

            if phone and msg:
                self.push_live_step(f"Conectando puente WhatsApp hacia {phone}...")
                res = self.whatsapp.send_message(phone, msg)
                self.respond("Mensaje de WhatsApp entregado." if res["ok"] else res["error"])
            else:
                self.respond("Dime qué mensaje deseas enviar por WhatsApp, por ejemplo: 'Enviar WhatsApp diciendo Hola'.")
            return

        if "sala de voz" in text or "webrtc" in text:
            self._set_tool_telemetry("VOIP_WEBRTC", "Creando sala WebRTC")
            res = self.voip.start_webrtc_room()
            if res["ok"]:
                self.respond("Canal de voz WebRTC abierto.")
            return

        # 9. ENRUTADOR DE HERRAMIENTAS INTELIGENTE (GEMINI / OLLAMA) + CONVERSACIÓN PROFUNDA
        self.push_live_step("Evaluando herramientas nativas con Gemini...")
        routed_reply = self.router.route_and_execute(user_text)
        if routed_reply:
            self.respond(routed_reply)
            return

        reply = self.ask_brain(user_text)
        self.respond(reply)


# ---------------- SERVIDOR UNIFICADO (HUD 4K + RAINMETER TELEMETRY) ----------------
app = Flask(__name__)
core = ArgonHermesOrchestrator()


@app.route("/")
@app.route("/hud")
def index() -> Response:
    return Response(HUD_HTML, mimetype="text/html")


@app.route("/telemetry")
def rainmeter_telemetry() -> Response:
    """Endpoint ligero JSON consumido por Rainmeter (skins/HUD_Agent.ini)."""
    st = core.tasks.get_system_status()
    d = st["data"] if st["ok"] else {"cpu_percent": 0, "ram_percent": 0, "battery_percent": 100}
    return jsonify({
        "status": core.state,
        "tool": core.active_tool,
        "last_action": core.last_action,
        "updated_at": time.strftime("%H:%M:%S"),
        "cpu": d["cpu_percent"],
        "ram": d["ram_percent"],
        "battery": d["battery_percent"],
    })


@app.route("/api/state")
def api_state() -> Response:
    st = core.tasks.get_system_status()
    telemetry = st["data"] if st["ok"] else {"cpu_percent": 0, "ram_percent": 0, "battery_percent": 100}
    return jsonify({
        "state": core.state,
        "active_tool": core.active_tool,
        "last_action": core.last_action,
        "is_processing": core.is_processing,
        "live_steps": core.live_steps,
        "model": f"GEMINI ({Config.GEMINI_MODEL})" if core.gemini_online else core.active_model,
        "notion_enabled": core.notion.enabled,
        "telemetry": telemetry,
        "memories": core.skills.recall_memories(limit=8),
        "calendar": core.get_unified_calendar(),
        "logs": core.ui_logs,
    })


@app.route("/api/command", methods=["POST"])
@app.route("/command", methods=["POST"])
def api_command() -> Response:
    data = request.get_json(force=True) or {}
    text = (data.get("text") or data.get("prompt") or "").strip()
    if text:
        core.add_log("FRANCO", text, "user")
        threading.Thread(target=core.process_command, args=(text,), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/listen", methods=["POST"])
def api_listen() -> Response:
    def _worker():
        core.start_live_trace("Escuchando micrófono (pausas naturales de hasta 1.75s permitidas)...")
        spoken = core.voice.listen(timeout=8, phrase_time_limit=45)
        if spoken:
            core.add_log("FRANCO (VOZ)", spoken, "user")
            core.process_command(spoken)
        else:
            core.finish_live_trace()
    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/stop_voice", methods=["POST"])
def api_stop_voice() -> Response:
    core.voice.stop_speaking()
    core.finish_live_trace()
    return jsonify({"ok": True})


@app.route("/api/handsfree", methods=["POST"])
def api_handsfree() -> Response:
    core.handsfree = not core.handsfree
    if core.handsfree:
        def _loop():
            while core.handsfree:
                if core.state == "IDLE" and not core.is_processing:
                    spoken = core.voice.listen(timeout=6, phrase_time_limit=40)
                    if spoken:
                        core.add_log("FRANCO (VOZ)", spoken, "user")
                        if spoken.lower() in ["detener escucha", "modo manual"]:
                            core.handsfree = False
                            break
                        core.process_command(spoken)
                time.sleep(0.25)
        threading.Thread(target=_loop, daemon=True).start()
    return jsonify({"handsfree": core.handsfree})


@app.route("/api/voice", methods=["POST"])
def api_voice() -> Response:
    data = request.get_json(force=True) or {}
    voice = data.get("voice", "es-ES-AlvaroNeural")
    pitch = data.get("pitch", "-14Hz")
    rate = data.get("rate", "+6%")
    core.voice.set_voice_profile(voice, pitch, rate)
    threading.Thread(
        target=lambda: core.respond("Frecuencia vocal recalibrada. Tono grave futurista activo."),
        daemon=True
    ).start()
    return jsonify({"ok": True})


@app.route("/api/shortcut", methods=["POST"])
def api_shortcut() -> Response:
    data = request.get_json(force=True) or {}
    startup = bool(data.get("startup", False))
    res = core.skills.setup_windows_integration(enable_startup=startup)
    return jsonify(res)


def launch_hud_window(url: str) -> None:
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in edge_paths:
        if os.path.exists(path):
            subprocess.Popen([path, f"--app={url}", "--window-size=1440,870"])
            return
    webbrowser.open(url)


if __name__ == "__main__":
    PORT = Config.HUD_PORT
    url = f"http://127.0.0.1:{PORT}"

    desktop_lnk = os.path.join(os.path.expanduser("~"), "Desktop", "Argon 4 AI.lnk")
    if not os.path.exists(desktop_lnk):
        core.skills.setup_windows_integration(enable_startup=False)

    def _BootSequence():
        time.sleep(1.2)
        launch_hud_window(url)
        time.sleep(1.0)
        mems = core.skills.recall_memories(limit=3)
        if mems:
            core.respond(
                f"Arquitectura de {Config.AGENT_NAME} conectada a Google Gemini, Franco. "
                f"He cargado {len(mems)} recuerdos permanentes y la trazabilidad en vivo está activa."
            )
        else:
            core.respond(
                f"Núcleo {Config.AGENT_NAME} edición Hermes conectado a Google Gemini. Voz grave y visión de pantalla activas."
            )

    threading.Thread(target=_BootSequence, daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
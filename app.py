#!/usr/bin/env python3
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
COMMANDS_FILE = DATA_DIR / "commands.json"
CONFIG_FILE = DATA_DIR / "config.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default_value):
    if not path.exists():
        return default_value
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, indent=2)


def clean_id(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or f"cmd-{int(time.time())}"


def load_config() -> dict:
    cfg = load_json(CONFIG_FILE, {"ip": "", "port": 56001})
    cfg.setdefault("ip", "")
    cfg.setdefault("port", 56001)
    return cfg


def load_commands() -> list:
    return load_json(COMMANDS_FILE, [])


def save_commands(commands: list) -> None:
    save_json(COMMANDS_FILE, commands)


def find_command(command_id: str):
    commands = load_commands()
    for idx, cmd in enumerate(commands):
        if cmd.get("id") == command_id:
            return commands, idx, cmd
    return commands, -1, None


def send_soundbar_command(ip: str, port: int, xml_command: str, timeout: float = 3.0) -> dict:
    if not ip:
        return {
            "ok": False,
            "error": "No IP configured.",
            "http_status": None,
            "response": "",
            "url": None,
        }

    encoded_cmd = urllib.parse.quote(xml_command, safe="")
    url = f"http://{ip}:{port}/UIC?cmd={encoded_cmd}"
    req = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4096)
            text = raw.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "http_status": int(resp.status),
                "response": text,
                "error": None,
                "url": url,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", errors="replace")
        return {
            "ok": False,
            "http_status": int(exc.code),
            "response": body,
            "error": f"HTTP {exc.code}",
            "url": url,
        }
    except Exception as exc:
        return {
            "ok": False,
            "http_status": None,
            "response": "",
            "error": str(exc),
            "url": url,
        }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        content_len = int(self.headers.get("Content-Length", "0"))
        if content_len <= 0:
            return {}
        raw = self.rfile.read(content_len)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _serve_static(self):
        path = self.path
        if path == "/":
            file_path = WEB_DIR / "index.html"
        else:
            safe = path.lstrip("/")
            file_path = WEB_DIR / safe

        if not file_path.exists() or not file_path.is_file() or WEB_DIR not in file_path.resolve().parents:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        if file_path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        elif file_path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        else:
            ctype = "application/octet-stream"

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/config":
            return self._send_json(load_config())
        if self.path == "/api/commands":
            return self._send_json(load_commands())
        return self._serve_static()

    def do_POST(self):
        if self.path == "/api/config":
            body = self._read_json_body()
            ip = str(body.get("ip", "")).strip()
            try:
                port = int(body.get("port", 56001))
            except Exception:
                port = 56001
            cfg = {"ip": ip, "port": port}
            save_json(CONFIG_FILE, cfg)
            return self._send_json(cfg)

        if self.path == "/api/ping":
            cfg = load_config()
            probes = [
                "<name>GetVolume</name>",
                "<name>GetMute</name>",
                "<name>GetFunc</name>",
            ]
            started = time.time()
            result = None
            for probe in probes:
                result = send_soundbar_command(cfg["ip"], int(cfg["port"]), probe)
                if result["ok"]:
                    break
            elapsed_ms = int((time.time() - started) * 1000)
            return self._send_json({
                "ok": bool(result and result.get("ok")),
                "latency_ms": elapsed_ms,
                "http_status": result.get("http_status") if result else None,
                "error": result.get("error") if result else "Unknown",
                "response": (result.get("response") or "")[:500] if result else "",
            })

        if self.path == "/api/commands":
            body = self._read_json_body()
            name = str(body.get("name", "")).strip()
            xml_command = str(body.get("xml_command", "")).strip()
            expected = str(body.get("expected", "")).strip()
            if not name or not xml_command:
                return self._send_json({"error": "name and xml_command are required"}, status=400)

            commands = load_commands()
            base_id = clean_id(name)
            candidate = base_id
            suffix = 1
            existing = {c.get("id") for c in commands}
            while candidate in existing:
                suffix += 1
                candidate = f"{base_id}-{suffix}"

            cmd = {
                "id": candidate,
                "name": name,
                "xml_command": xml_command,
                "expected": expected,
                "status": "untested",
                "last_tested_at": None,
                "last_http_status": None,
                "last_error": None,
                "last_response": None,
            }
            commands.append(cmd)
            save_commands(commands)
            return self._send_json(cmd, status=201)

        test_match = re.fullmatch(r"/api/commands/([^/]+)/test", self.path)
        if test_match:
            command_id = urllib.parse.unquote(test_match.group(1))
            commands, idx, cmd = find_command(command_id)
            if cmd is None:
                return self._send_json({"error": "Command not found"}, status=404)

            cfg = load_config()
            result = send_soundbar_command(cfg["ip"], int(cfg["port"]), cmd["xml_command"])

            cmd["last_tested_at"] = now_iso()
            cmd["last_http_status"] = result["http_status"]
            cmd["last_error"] = result["error"]
            cmd["last_response"] = (result["response"] or "")[:2000]
            if result["ok"]:
                cmd["status"] = "working"
            elif cmd.get("status") == "untested":
                cmd["status"] = "not_working"

            commands[idx] = cmd
            save_commands(commands)
            return self._send_json({"command": cmd, "result": result})

        mark_match = re.fullmatch(r"/api/commands/([^/]+)/status", self.path)
        if mark_match:
            command_id = urllib.parse.unquote(mark_match.group(1))
            body = self._read_json_body()
            status = str(body.get("status", "")).strip()
            if status not in {"working", "not_working", "untested"}:
                return self._send_json({"error": "Invalid status"}, status=400)

            commands, idx, cmd = find_command(command_id)
            if cmd is None:
                return self._send_json({"error": "Command not found"}, status=404)
            cmd["status"] = status
            commands[idx] = cmd
            save_commands(commands)
            return self._send_json(cmd)

        return self._send_json({"error": "Not found"}, status=404)

    def do_PUT(self):
        update_match = re.fullmatch(r"/api/commands/([^/]+)", self.path)
        if not update_match:
            return self._send_json({"error": "Not found"}, status=404)

        command_id = urllib.parse.unquote(update_match.group(1))
        body = self._read_json_body()
        name = str(body.get("name", "")).strip()
        xml_command = str(body.get("xml_command", "")).strip()
        expected = str(body.get("expected", "")).strip()

        if not name or not xml_command:
            return self._send_json({"error": "name and xml_command are required"}, status=400)

        commands, idx, cmd = find_command(command_id)
        if cmd is None:
            return self._send_json({"error": "Command not found"}, status=404)

        cmd["name"] = name
        cmd["xml_command"] = xml_command
        cmd["expected"] = expected
        commands[idx] = cmd
        save_commands(commands)
        return self._send_json(cmd)

    def do_DELETE(self):
        delete_match = re.fullmatch(r"/api/commands/([^/]+)", self.path)
        if not delete_match:
            return self._send_json({"error": "Not found"}, status=404)

        command_id = urllib.parse.unquote(delete_match.group(1))
        commands = load_commands()
        new_commands = [c for c in commands if c.get("id") != command_id]
        if len(new_commands) == len(commands):
            return self._send_json({"error": "Command not found"}, status=404)

        save_commands(new_commands)
        return self._send_json({"deleted": command_id})


def run() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_json(CONFIG_FILE, {"ip": "", "port": 56001})
    if not COMMANDS_FILE.exists():
        save_json(COMMANDS_FILE, [])

    server = ThreadingHTTPServer(("127.0.0.1", 8787), Handler)
    print("Samsung Soundbar test harness running at http://127.0.0.1:8787")
    server.serve_forever()


if __name__ == "__main__":
    run()

"""Harness didáctico: servidor + bucle de agente. Uso: python server.py -> http://localhost:8000"""
import datetime
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic

MODEL = "claude-haiku-5-5"
HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(HERE, ".env")):  # carga .env sin dependencias extra
    for line in open(os.path.join(HERE, ".env"), encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)
SYSTEM = "Eres un asistente conciso. Responde en español."
history = []  # la "memoria": el modelo no recuerda nada, esta lista se reenvía en cada llamada


def calc(i):
    e = i["expression"]
    if "**" in e or not re.fullmatch(r"[0-9+\-*/(). ]+", e):
        return "Expresión inválida"
    try:
        return str(eval(e, {"__builtins__": {}}))
    except Exception as ex:
        return f"Error: {ex}"


def read_file(i):
    try:  # basename: solo archivos de esta carpeta (límite de seguridad)
        with open(os.path.join(HERE, os.path.basename(i["name"])), encoding="utf-8") as f:
            return f.read(20000)
    except Exception as ex:
        return f"Error: {ex}"


# Cada herramienta = descripción (lo que lee el modelo) + parámetros + función real (lo que ejecuta el harness)
TOOLS = {
    "get_time": ("Devuelve la fecha y hora actual.", {},
                 lambda i: datetime.datetime.now().isoformat(timespec="seconds")),
    "calculator": ("Evalúa una expresión aritmética, p. ej. '(2+3)*4'.", {"expression": "string"}, calc),
    "list_files": ("Lista los archivos de la carpeta del proyecto.", {},
                   lambda i: "\n".join(sorted(os.listdir(HERE)))),
    "read_file": ("Lee un archivo de la carpeta del proyecto.", {"name": "string"}, read_file),
}


def chat(text, cfg):
    msgs = history if cfg["memory"] else []  # memoria off = el modelo parte de cero cada vez
    for m in msgs:  # los bloques thinking van atados a la lista de herramientas: se descartan de turnos pasados
        if m["role"] == "assistant":
            m["content"] = [b for b in m["content"] if b.type not in ("thinking", "redacted_thinking")]
    msgs.append({"role": "user", "content": text})
    names = [n for n in cfg["tools"] if n in TOOLS]
    tools = [{"name": n, "description": TOOLS[n][0],
              "input_schema": {"type": "object",
                               "properties": {k: {"type": t} for k, t in TOOLS[n][1].items()},
                               "required": list(TOOLS[n][1])}} for n in names]
    kw = {"tools": tools} if tools else {}
    if cfg["system"]:
        kw["system"] = SYSTEM

    client = anthropic.Anthropic()
    trace, resp = [], None
    for _ in range(cfg["max_turns"]):
        resp = client.messages.create(model=MODEL, max_tokens=1024, messages=msgs, **kw)
        trace.append({"type": "call", "messages": len(msgs), "tools": names,
                      "input_tokens": resp.usage.input_tokens})
        msgs.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = str(TOOLS[b.name][2](b.input))
                if cfg["truncate"]:
                    out = out[:200]
                trace.append({"type": "tool", "name": b.name, "input": b.input, "output": out})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        msgs.append({"role": "user", "content": results})
    reply = "".join(b.text for b in resp.content if b.type == "text") or "(tope de turnos alcanzado)"
    return {"reply": reply, "trace": trace, "context_messages": len(msgs)}


class H(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        with open(os.path.join(HERE, "index.html"), "rb") as f:
            self.send(200, f.read(), "text/html; charset=utf-8")

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/reset":
            history.clear()
            return self.send(200, b"{}")
        try:
            out = chat(data["message"], data["config"])
        except Exception as ex:
            out = {"error": str(ex)}
        self.send(200, json.dumps(out).encode())


if __name__ == "__main__":
    print("http://localhost:8000")
    HTTPServer(("127.0.0.1", 8000), H).serve_forever()

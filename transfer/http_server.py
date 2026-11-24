"""Serveur HTTP de réception : POST /meteo (un point JSON, ou une liste de points).

Mesure aussi lui-même la taille des requêtes reçues (ligne de requête + en-têtes + corps)
et le temps CPU consommé pour les recevoir et décoder.
GET /stats -> JSON ; GET /reset -> remise à zéro.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

verrou = threading.Lock()


def zero():
    return {"requetes": 0, "points": 0, "octets_entetes": 0, "octets_corps": 0,
            "cpu0": time.process_time()}


stats = zero()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive possible

    def log_message(self, *a):
        pass

    def _repondre(self, code, corps=b""):
        self.send_response(code)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_POST(self):
        corps = self.rfile.read(int(self.headers["Content-Length"]))
        donnees = json.loads(corps)
        n = len(donnees) if isinstance(donnees, list) else 1
        with verrou:
            stats["requetes"] += 1
            stats["points"] += n
            stats["octets_entetes"] += len(self.raw_requestline) + len(bytes(self.headers))
            stats["octets_corps"] += len(corps)
        self._repondre(200)

    def do_GET(self):
        global stats
        if self.path == "/reset":
            with verrou:
                stats = zero()
            self._repondre(204)
        else:
            s = {k: v for k, v in stats.items() if k != "cpu0"}
            s["cpu_s"] = time.process_time() - stats["cpu0"]
            self._repondre(200, json.dumps(s).encode())


if __name__ == "__main__":
    print("serveur HTTP prêt sur :8000", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()

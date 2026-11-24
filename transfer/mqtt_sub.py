"""Abonné MQTT de réception (topic meteo/#), équivalent du serveur HTTP.

Se connecte directement au broker (pas via le proxy : on mesure le trajet émetteur -> broker).
Stats via HTTP : GET http://127.0.0.1:8002/stats ; /reset.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paho.mqtt.client as mqtt

verrou = threading.Lock()


def zero():
    return {"messages": 0, "points": 0, "octets_payload": 0, "cpu0": time.process_time()}


stats = zero()


def on_message(client, userdata, msg):
    donnees = json.loads(msg.payload)
    n = len(donnees) if isinstance(donnees, list) else 1
    with verrou:
        stats["messages"] += 1
        stats["points"] += n
        stats["octets_payload"] += len(msg.payload)


class Stats(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        global stats
        if self.path == "/reset":
            with verrou:
                stats = zero()
            corps = b""
        else:
            s = {k: v for k, v in stats.items() if k != "cpu0"}
            s["cpu_s"] = time.process_time() - stats["cpu0"]
            corps = json.dumps(s).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


if __name__ == "__main__":
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="td-recepteur")
    c.on_message = on_message
    c.on_connect = lambda cl, u, f, rc, p: cl.subscribe("meteo/#", qos=1)
    c.connect("127.0.0.1", 1883)
    c.loop_start()
    print("abonné MQTT prêt (stats :8002)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8002), Stats).serve_forever()

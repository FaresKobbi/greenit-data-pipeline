"""Proxy TCP qui compte les octets transitant, de la même façon pour HTTP et MQTT.

    client --> :8001 (proxy) --> :8000 serveur HTTP
    client --> :1884 (proxy) --> :1883 broker Mosquitto

Comptage au niveau applicatif (tout ce qui passe dans la connexion TCP : en-têtes HTTP,
réponses, paquets MQTT CONNECT/PUBLISH/PUBACK...). Les en-têtes TCP/IP eux-mêmes ne sont
pas vus ici (voir l'estimation par segments TCP dans send.py).

Statistiques : http://localhost:9101/stats (JSON) et /metrics (Prometheus).
"""
import asyncio
import json

ROUTES = {"http": (8001, "127.0.0.1", 8000), "mqtt": (1884, "127.0.0.1", 1883)}
stats = {p: {"montant": 0, "descendant": 0, "connexions": 0} for p in ROUTES}


async def tuyau(lecteur, ecrivain, proto, sens):
    try:
        while data := await lecteur.read(65536):
            stats[proto][sens] += len(data)
            ecrivain.write(data)
            await ecrivain.drain()
    except ConnectionError:
        pass
    finally:
        ecrivain.close()


def gestionnaire(proto, hote, port):
    async def gerer(cr, cw):
        stats[proto]["connexions"] += 1
        try:
            sr, sw = await asyncio.open_connection(hote, port)
        except OSError:
            cw.close()
            return
        await asyncio.gather(tuyau(cr, sw, proto, "montant"), tuyau(sr, cw, proto, "descendant"))
    return gerer


async def http_stats(r, w):
    ligne = (await r.readline()).decode()
    while (await r.readline()) not in (b"\r\n", b""):
        pass
    if " /metrics" in ligne:
        corps = "".join(
            f'td_proxy_octets_total{{proto="{p}",sens="{s}"}} {v}\n' if s != "connexions" else
            f'td_proxy_connexions_total{{proto="{p}"}} {v}\n'
            for p, d in stats.items() for s, v in d.items())
        ctype = "text/plain; version=0.0.4"
    else:
        corps, ctype = json.dumps(stats), "application/json"
    w.write(f"HTTP/1.1 200 OK\r\nContent-Type: {ctype}\r\nContent-Length: {len(corps)}\r\n"
            f"Connection: close\r\n\r\n{corps}".encode())
    await w.drain()
    w.close()


async def main():
    serveurs = [await asyncio.start_server(gestionnaire(p, h, pc), "127.0.0.1", pe)
                for p, (pe, h, pc) in ROUTES.items()]
    # 0.0.0.0 : Prometheus (conteneur) doit pouvoir joindre /metrics
    serveurs.append(await asyncio.start_server(http_stats, "0.0.0.0", 9101))
    print("proxy prêt : http :8001->:8000, mqtt :1884->:1883, stats :9101", flush=True)
    await asyncio.gather(*(s.serve_forever() for s in serveurs))


asyncio.run(main())

"""Mesure d'une action : durée, CPU du client, énergie RAPL, et ressources exactes d'un conteneur
(CPU, I/O disque, RAM) lues directement dans son cgroup (pas d'échantillonnage Prometheus).

    p = puissance_repos()
    with Mesure("storing-infra-postgres-1", p) as m:
        ...
    print(m.res)
"""
import pathlib
import subprocess
import time

RAPL = pathlib.Path("/sys/class/powercap/intel-rapl:0")
try:
    MAX_UJ = int((RAPL / "max_energy_range_uj").read_text())
except OSError:
    MAX_UJ = 2 ** 32


def rapl_uj():
    try:
        return int((RAPL / "energy_uj").read_text())
    except OSError:  # illisible : sudo chmod o+r /sys/class/powercap/intel-rapl:0/energy_uj
        return None


def puissance_repos(duree=3.0):
    e0 = rapl_uj()
    time.sleep(duree)
    e1 = rapl_uj()
    return None if e0 is None else ((e1 - e0) % MAX_UJ) / 1e6 / duree


def cgroup_conteneur(nom):
    cid = subprocess.run(["docker", "inspect", "-f", "{{.Id}}", nom],
                         capture_output=True, text=True, check=True).stdout.strip()
    return pathlib.Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope")


def lire_cgroup(p):
    cpu = next(int(l.split()[1]) for l in (p / "cpu.stat").read_text().splitlines()
               if l.startswith("usage_usec")) / 1e6
    rb = wb = 0
    for ligne in (p / "io.stat").read_text().splitlines():
        for kv in ligne.split()[1:]:
            k, v = kv.split("=")
            rb += int(v) if k == "rbytes" else 0
            wb += int(v) if k == "wbytes" else 0
    return cpu, rb, wb, int((p / "memory.current").read_text())


class Mesure:
    def __init__(self, conteneur=None, p_repos=None):
        self.cg = cgroup_conteneur(conteneur) if conteneur else None
        self.p_repos = p_repos
        self.res = {}

    def __enter__(self):
        self._c0 = lire_cgroup(self.cg) if self.cg else None
        self._e0 = rapl_uj()
        self._p0 = time.process_time()
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        dt = time.perf_counter() - self._t0
        r = {"duree_s": dt, "cpu_client_s": time.process_time() - self._p0}
        e1 = rapl_uj()
        if self._e0 is not None and e1 is not None:
            e = ((e1 - self._e0) % MAX_UJ) / 1e6
            r["energie_J"] = e
            if self.p_repos is not None:
                r["energie_nette_J"] = max(e - self.p_repos * dt, 0.0)
        if self.cg:
            c1 = lire_cgroup(self.cg)
            r.update(cpu_conteneur_s=c1[0] - self._c0[0], io_lecture_o=c1[1] - self._c0[1],
                     io_ecriture_o=c1[2] - self._c0[2], ram_conteneur_o=c1[3])
        self.res = r
        return False

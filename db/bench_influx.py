"""InfluxDB 2.7 : base séries temporelles. measurement "meteo", tag station, 4 fields.

Écriture : line protocol, API synchrone ; unitaire = 1 requête HTTP par point,
lot = 1 requête HTTP par lot de 10 000 lignes.

Lecture "SELECT * ORDER BY time DESC LIMIT 100" : en Flux il faut réassembler les champs
(pivot) et trier entre toutes les séries (1 série = 1 station x 1 champ) -> opération coûteuse
pour une base orientée colonnes/séries, c'est un des points à commenter.
Agrégation : sum() et count() par série (calculés côté stockage), combinés côté client
-> moyenne globale exacte.
"""
import subprocess

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from common import Base, main

BUCKET, ORG = "meteo", "td"
SOURCE = f'from(bucket: "{BUCKET}") |> range(start: 0) |> filter(fn: (r) => r._measurement == "meteo"'


def ligne(p):
    s, t, te, ap, ro, ve = p
    return f"meteo,station={s} temp={te},ressenti={ap},rosee={ro},vent={ve} {t}"


class Influx(Base):
    nom = "influxdb"
    conteneur = "storing-infra-influxdb-1"

    def __init__(self):
        self.cl = InfluxDBClient(url="http://127.0.0.1:8086", token="td-token", org=ORG, timeout=600_000)
        self.w = self.cl.write_api(write_options=SYNCHRONOUS)
        self.q = self.cl.query_api()

    def reinitialiser(self):
        api = self.cl.buckets_api()
        if b := api.find_bucket_by_name(BUCKET):
            api.delete_bucket(b)
        api.create_bucket(bucket_name=BUCKET, org=ORG)

    def ecrire_un(self, p):
        self.w.write(BUCKET, record=ligne(p), write_precision="s")

    def ecrire_lot(self, pts):
        self.w.write(BUCKET, record="\n".join(map(ligne, pts)), write_precision="s")

    def lire_derniers(self, n=100):
        flux = (SOURCE + ')'
                f' |> tail(n: {n})'
                ' |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
                f' |> group() |> sort(columns: ["_time"], desc: true) |> limit(n: {n})')
        return [r.values for t in self.q.query(flux) for r in t.records]

    def moyenne_temp(self):
        src = SOURCE + ' and r._field == "temp")'
        somme = sum(r.get_value() for t in self.q.query(src + " |> sum()") for r in t.records)
        n = sum(r.get_value() for t in self.q.query(src + " |> count()") for r in t.records)
        return somme / n

    def taille_octets(self):
        out = subprocess.run(["docker", "exec", self.conteneur, "du", "-sb", "/var/lib/influxdb2/engine"],
                             capture_output=True, text=True, check=True).stdout
        return int(out.split()[0])


if __name__ == "__main__":
    main(Influx())

"""PostgreSQL : table relationnelle classique + index sur time.

Modes d'écriture :
  unitaire          INSERT en autocommit : 1 transaction (donc 1 fsync du WAL) par point
  unitaire_sync_off idem avec synchronous_commit=off (le fsync est différé : moins durable)
  lot               COPY par lots de 10 000 (méthode d'import en masse native de PostgreSQL)
"""
import psycopg

from common import Base, main


class Postgres(Base):
    nom = "postgresql"
    conteneur = "storing-infra-postgres-1"
    modes_unitaires = ["unitaire", "unitaire_sync_off"]

    def __init__(self):
        self.c = psycopg.connect("host=127.0.0.1 user=td password=td dbname=meteo", autocommit=True)

    def reinitialiser(self):
        self.c.execute("DROP TABLE IF EXISTS sensor_data")
        self.c.execute("""CREATE TABLE sensor_data (
            station text NOT NULL, time timestamptz NOT NULL,
            temp real, ressenti real, rosee real, vent real)""")
        self.c.execute("CREATE INDEX ON sensor_data (time)")
        self.c.execute("CHECKPOINT")  # repart d'un état disque propre

    def preparer_mode(self, mode):
        self.c.execute(f"SET synchronous_commit = {'off' if mode == 'unitaire_sync_off' else 'on'}")

    def ecrire_un(self, p):
        self.c.execute("INSERT INTO sensor_data VALUES (%s, to_timestamp(%s), %s, %s, %s, %s)", p)

    def ecrire_lot(self, pts):
        with self.c.cursor() as cur, cur.copy(
                "COPY sensor_data FROM STDIN WITH (FORMAT csv)") as cp:
            cp.write("".join(f"{s},{_ts(t)},{te},{ap},{ro},{ve}\n" for s, t, te, ap, ro, ve in pts))

    def apres_ecriture(self):
        self.c.execute("ANALYZE sensor_data")

    def lire_derniers(self, n=100):
        return self.c.execute("SELECT * FROM sensor_data ORDER BY time DESC LIMIT %s", (n,)).fetchall()

    def moyenne_temp(self):
        return self.c.execute("SELECT avg(temp) FROM sensor_data").fetchone()[0]

    def taille_octets(self):
        return self.c.execute("SELECT pg_total_relation_size('sensor_data')").fetchone()[0]


_cache_ts = {}


def _ts(t):
    """epoch -> horodatage ISO (mis en cache : les 4 416 heures se répètent pour chaque station)."""
    s = _cache_ts.get(t)
    if s is None:
        from datetime import datetime, timezone
        s = _cache_ts[t] = datetime.fromtimestamp(t, timezone.utc).isoformat()
    return s


if __name__ == "__main__":
    main(Postgres())

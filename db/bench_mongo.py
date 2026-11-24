"""MongoDB : collection de documents + index sur time.

    python bench_mongo.py [jeux...]             collection classique
    python bench_mongo.py --timeseries [jeux]   bonus : collection time-series native (Mongo >= 5)

Écriture : insert_one (unitaire) / insert_many par lots de 10 000.
Durabilité par défaut (w:1, sans attendre le journal) : moins stricte que PostgreSQL en autocommit.
"""
import sys
from datetime import datetime, timezone

from pymongo import MongoClient

from common import Base, main

_cache_dt = {}


def _dt(t):
    d = _cache_dt.get(t)
    if d is None:
        d = _cache_dt[t] = datetime.fromtimestamp(t, timezone.utc)
    return d


def doc(p):
    s, t, te, ap, ro, ve = p
    return {"station": s, "time": _dt(t), "temp": te, "ressenti": ap, "rosee": ro, "vent": ve}


class Mongo(Base):
    conteneur = "storing-infra-mongo-1"

    def __init__(self, timeseries=False):
        self.ts = timeseries
        self.nom = "mongodb-timeseries" if timeseries else "mongodb"
        self.db = MongoClient("mongodb://127.0.0.1:27017").meteo
        self.col = self.db.sensor_data

    def reinitialiser(self):
        self.col.drop()
        if self.ts:
            self.db.create_collection("sensor_data", timeseries={
                "timeField": "time", "metaField": "station", "granularity": "hours"})
        self.col.create_index("time")

    def ecrire_un(self, p):
        self.col.insert_one(doc(p))

    def ecrire_lot(self, pts):
        self.col.insert_many([doc(p) for p in pts], ordered=False)

    def apres_ecriture(self):
        # force un checkpoint WiredTiger (sinon storageSize ne reflète pas les données, ~60 s de retard)
        self.db.client.admin.command("fsync")

    def lire_derniers(self, n=100):
        return list(self.col.find({}, {"_id": 0}).sort("time", -1).limit(n))

    def moyenne_temp(self):
        return next(self.col.aggregate([{"$group": {"_id": None, "m": {"$avg": "$temp"}}}]))["m"]

    def taille_octets(self):
        s = next(self.col.aggregate([{"$collStats": {"storageStats": {}}}]))["storageStats"]
        return s.get("storageSize", 0) + s.get("totalIndexSize", 0)


if __name__ == "__main__":
    ts = "--timeseries" in sys.argv
    if ts:
        sys.argv.remove("--timeseries")
    main(Mongo(timeseries=ts))

# Comparatif bases de données


## Jeu small (4 416 points)


**Durée (s)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | unitaire | 5.07 | 4.56 | 17.7 | 3.49 |
| Écriture | unitaire_sync_off | 0.261 | – | – | – |
| Écriture | lot | 0.0887 | 0.0915 | 0.59 | 0.0281 |
| Lecture 100 derniers | 1er appel | 0.00272 | 0.00339 | 0.0274 | 0.00161 |
| Lecture 100 derniers | répétitions (moy) | 0.00201 | 0.00252 | 0.0259 | 0.0035 |
| Moyenne temp | 1er appel | 0.00236 | 0.00409 | 0.0313 | 0.00409 |
| Moyenne temp | répétitions (moy) | 0.00216 | 0.00398 | 0.0345 | 0.0234 |

**Énergie nette (J)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | unitaire | 4.46 | 19.9 | 44.2 | 20.3 |
| Écriture | unitaire_sync_off | 1.88 | – | – | – |
| Écriture | lot | 0 | 0.556 | 1.08 | 0.382 |
| Lecture 100 derniers | 1er appel | 0 | 0.028 | 0 | 0.063 |
| Lecture 100 derniers | répétitions (moy) | 0.00425 | 0.00825 | 0.032 | 0.0173 |
| Moyenne temp | 1er appel | 0 | 0.01 | 0.043 | 0.015 |
| Moyenne temp | répétitions (moy) | 0.00375 | 0.007 | 0.052 | 0.107 |

**CPU base (s)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | unitaire | 1.3 | 1.23 | 9.91 | 1.46 |
| Écriture | unitaire_sync_off | 0.0901 | – | – | – |
| Écriture | lot | 0.0315 | 0.0468 | 1.98 | 0.0101 |
| Lecture 100 derniers | 1er appel | 0.0011 | 0.0012 | 0.0246 | 0.0006 |
| Lecture 100 derniers | répétitions (moy) | 0.0007 | 0.00103 | 0.0239 | 0.00325 |
| Moyenne temp | 1er appel | 0.0015 | 0.0029 | 0.0284 | 0.0028 |
| Moyenne temp | répétitions (moy) | 0.00127 | 0.00292 | 0.0836 | 0.0252 |

**Écrit disque**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | unitaire | 35.3 Mo | 1.2 Mo | 19.4 Mo | 7.1 Mo |
| Écriture | unitaire_sync_off | 200.0 Ko | – | – | – |
| Écriture | lot | 504.0 Ko | 8.0 Ko | 1.8 Mo | 0 o |
| Lecture 100 derniers | 1er appel | 0 o | 0 o | 0 o | 0 o |
| Lecture 100 derniers | répétitions (moy) | 0 o | 0 o | 0 o | 0 o |
| Moyenne temp | 1er appel | 0 o | 0 o | 0 o | 0 o |
| Moyenne temp | répétitions (moy) | 0 o | 0 o | 0 o | 1.0 Ko |

**Débit d'écriture (points/s) et taille sur disque**

| | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|
| débit unitaire | 872 | 969 | 250 | 1 264 |
| débit unitaire_sync_off | 16 935 | – | – | – |
| débit lot | 49 813 | 48 269 | 7 481 | 157 382 |
| taille données | 720.0 Ko | 308.0 Ko | 33.4 Mo | 72.0 Ko |

## Jeu medium (499 008 points)


**Durée (s)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | lot | 2.66 | 4.82 | 5.51 | 2.79 |
| Lecture 100 derniers | 1er appel | 0.00158 | 0.00155 | 0.268 | 0.0163 |
| Lecture 100 derniers | répétitions (moy) | 0.00184 | 0.00163 | 0.37 | 0.0345 |
| Moyenne temp | 1er appel | 0.0379 | 0.0727 | 0.111 | 0.0543 |
| Moyenne temp | répétitions (moy) | 0.0463 | 0.0693 | 0.161 | 0.0605 |

**Énergie nette (J)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | lot | 12.3 | 42.1 | 21.9 | 35.6 |
| Lecture 100 derniers | 1er appel | 0 | 0 | 3.01 | 0.196 |
| Lecture 100 derniers | répétitions (moy) | 0 | 0.0095 | 1.37 | 0.171 |
| Moyenne temp | 1er appel | 0.078 | 0.944 | 0.136 | 0.135 |
| Moyenne temp | répétitions (moy) | 0.033 | 0.649 | 0.062 | 0.144 |

**CPU base (s)**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | lot | 1.37 | 2.31 | 8.63 | 1.06 |
| Lecture 100 derniers | 1er appel | 0.0007 | 0.0004 | 0.501 | 0.0157 |
| Lecture 100 derniers | répétitions (moy) | 0.00065 | 0.00055 | 0.703 | 0.0336 |
| Moyenne temp | 1er appel | 0.104 | 0.072 | 0.115 | 0.0535 |
| Moyenne temp | répétitions (moy) | 0.129 | 0.0688 | 0.294 | 0.0599 |

**Écrit disque**

| Action | Mode | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|---|
| Écriture | lot | 55.1 Mo | 20.5 Mo | 12.9 Mo | 12.4 Mo |
| Lecture 100 derniers | 1er appel | 0 o | 0 o | 0 o | 0 o |
| Lecture 100 derniers | répétitions (moy) | 0 o | 0 o | 0 o | 0 o |
| Moyenne temp | 1er appel | 0 o | 12.0 Ko | 0 o | 0 o |
| Moyenne temp | répétitions (moy) | 0 o | 0 o | 0 o | 0 o |

**Débit d'écriture (points/s) et taille sur disque**

| | postgresql | mongodb | influxdb | mongodb-timeseries |
|---|---|---|---|---|
| débit lot | 187 882 | 103 429 | 90 506 | 178 978 |
| taille données | 36.1 Mo | 24.9 Mo | 42.2 Mo | 640.0 Ko |

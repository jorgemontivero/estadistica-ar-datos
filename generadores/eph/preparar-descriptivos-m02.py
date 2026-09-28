#!/usr/bin/env python
"""
Estadísticos descriptivos de referencia para las entradas del módulo M02.

Ninguna entrada del sitio inventa números. Este script calcula, con la EPH real,
todo lo que las 30 entradas de Descriptiva necesitan citar: medidas de posición,
de dispersión, de forma, cuantiles, atípicos y coberturas.

Salida: datos/eph/descriptivos-m02.json

    python datos/eph/preparar-descriptivos-m02.py
"""

from __future__ import annotations

import os

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
SALIDA = Path(__file__).resolve().parent / "descriptivos-m02.json"


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def cuantil(x: np.ndarray, w: np.ndarray, q):
    o = np.argsort(x)
    xs, ws = x[o], w[o]
    p = (np.cumsum(ws) - 0.5 * ws) / ws.sum()
    return np.interp(q, p, xs)


def describir(x: np.ndarray, w: np.ndarray, *, geometrica=False) -> dict:
    W = w.sum()
    media = (w * x).sum() / W
    var = (w * (x - media) ** 2).sum() / W
    sd = np.sqrt(var)
    q1, q2, q3 = cuantil(x, w, [0.25, 0.50, 0.75])
    ric = q3 - q1
    lim_inf, lim_sup = q1 - 1.5 * ric, q3 + 1.5 * ric

    # Modo: el valor con más peso acumulado
    frec = pd.Series(w).groupby(x).sum()
    modo = float(frec.idxmax())

    d = {
        "n": int(len(x)),
        "poblacion": int(round(W)),
        "suma": float((w * x).sum()),
        "minimo": float(x.min()),
        "maximo": float(x.max()),
        "rango": float(x.max() - x.min()),
        "media": float(media),
        "mediana": float(q2),
        "modo": modo,
        "modo_pct": float(100 * frec.max() / W),
        "q1": float(q1),
        "q3": float(q3),
        "ric": float(ric),
        "varianza": float(var),
        "desvio": float(sd),
        "desvio_medio": float((w * np.abs(x - media)).sum() / W),
        "cv": float(sd / media),
        "asimetria": float((w * (x - media) ** 3).sum() / W / sd ** 3),
        "curtosis": float((w * (x - media) ** 4).sum() / W / sd ** 4 - 3),
        "limite_inferior": float(lim_inf),
        "limite_superior": float(lim_sup),
        "pct_atipicos": float(100 * w[(x < lim_inf) | (x > lim_sup)].sum() / W),
        "pct_bajo_la_media": float(100 * w[x < media].sum() / W),
        "deciles": {f"D{i}": float(cuantil(x, w, i / 10)) for i in range(1, 10)},
        "percentiles": {f"P{p}": float(cuantil(x, w, p / 100))
                        for p in (5, 90, 95, 99)},
        # Regla empírica: qué proporción cae dentro de 1, 2 y 3 desvíos
        "cobertura": {
            f"{k}s": float(100 * w[np.abs(x - media) <= k * sd].sum() / W)
            for k in (1, 2, 3)
        },
        # Cota de Chebyshev para los mismos k (1 − 1/k²)
        "chebyshev": {f"{k}s": float(100 * (1 - 1 / k ** 2)) for k in (2, 3)},
    }

    if geometrica:
        pos = x > 0
        d["media_geometrica"] = float(
            np.exp((w[pos] * np.log(x[pos])).sum() / w[pos].sum())
        )
        d["media_armonica"] = float(w[pos].sum() / (w[pos] / x[pos]).sum())

    return d


def main() -> None:
    ind = leer("usu_individual_T126.txt",
               ["ESTADO", "CH04", "CH06", "NIVEL_ED", "P21", "PONDIIO", "PONDERA"])
    hog = leer("usu_hogar_T126.txt", ["IX_TOT", "PONDERA"])

    # --- Ingreso de la ocupación principal ---
    oc = ind[(ind.ESTADO == 1) & (ind.P21 > 0) & (ind.PONDIIO > 0)]
    ingreso = describir(oc.P21.to_numpy(float), oc.PONDIIO.to_numpy(float),
                        geometrica=True)

    # --- Edad de los ocupados ---
    ed = ind[(ind.ESTADO == 1) & (ind.CH06 >= 15) & (ind.CH06 < 75)]
    edad = describir(ed.CH06.to_numpy(float), ed.PONDERA.to_numpy(float))

    # --- Personas por hogar ---
    hg = hog[hog.IX_TOT > 0]
    hogar = describir(hg.IX_TOT.to_numpy(float), hg.PONDERA.to_numpy(float))

    # --- Media ponderada: el promedio general sale de los promedios de grupo ---
    grupos = []
    for sexo, etiqueta in [(1, "Varones"), (2, "Mujeres")]:
        g = oc[oc.CH04 == sexo]
        w = g.PONDIIO.to_numpy(float)
        x = g.P21.to_numpy(float)
        grupos.append({
            "grupo": etiqueta,
            "n": int(len(x)),
            "poblacion": int(round(w.sum())),
            "media": float((w * x).sum() / w.sum()),
        })
    total_w = sum(g["poblacion"] for g in grupos)
    for g in grupos:
        g["peso"] = round(g["poblacion"] / total_w, 4)

    # --- Puntaje z de referencia ---
    z_ejemplos = [
        {"valor": v,
         "z_ingreso": round((v - ingreso["media"]) / ingreso["desvio"], 2)}
        for v in (500_000, 900_000, 2_000_000, 5_000_000)
    ]

    salida = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "nota": "Todo calculado con los ponderadores de la encuesta.",
        "ingreso": ingreso,
        "edad": edad,
        "personas_por_hogar": hogar,
        "ingreso_por_sexo": grupos,
        "z_ejemplos": z_ejemplos,
    }

    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    for clave in ("ingreso", "edad", "personas_por_hogar"):
        d = salida[clave]
        print(f"\n### {clave}  (n = {d['n']:,})")
        for k in ("media", "mediana", "modo", "q1", "q3", "ric", "desvio",
                  "desvio_medio", "cv", "asimetria", "curtosis",
                  "limite_superior", "pct_atipicos", "pct_bajo_la_media"):
            print(f"  {k:<18} {d[k]:>14,.3f}")
        print(f"  cobertura 1s/2s/3s   "
              f"{d['cobertura']['1s']:.1f} / {d['cobertura']['2s']:.1f} / "
              f"{d['cobertura']['3s']:.1f}")

    print("\n### ingreso: medias alternativas")
    print(f"  geométrica  {ingreso['media_geometrica']:>14,.0f}")
    print(f"  armónica    {ingreso['media_armonica']:>14,.0f}")
    print("\n### ingreso por sexo")
    for g in grupos:
        print(f"  {g['grupo']:<10} media {g['media']:>12,.0f}  peso {g['peso']}")
    print("\n### z", z_ejemplos)


if __name__ == "__main__":
    main()

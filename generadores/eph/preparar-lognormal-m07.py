#!/usr/bin/env python
"""
Ajuste lognormal al ingreso de la ocupación principal, para el módulo M07.

La entrada de la lognormal necesita responder una pregunta que casi ninguna
bibliografía contesta con datos: **¿el ingreso es realmente lognormal?** La
respuesta corta es que no, y este script deja el material para mostrarlo.

Calcula tres cosas:

  1. los momentos del ingreso y **los del logaritmo del ingreso**, que son los
     que tendrían que ser normales si la lognormal fuera el modelo correcto;

  2. los parámetros de la lognormal ajustada por momentos del logaritmo, y sus
     media, mediana y modo teóricos contra los observados;

  3. la comparación cuantil por cuantil, y de paso la de la normal ajustada,
     que sirve de referencia de cuánto mejora la lognormal.

Todo **ponderado con PONDIIO**, que es el ponderador de ingresos, para que las
cifras sean comparables con las del caso `ingresos-eph` —media 1.104.227,
asimetría 5,46—. El universo es el mismo que el de ese caso.

Ojo con la lectura: los cuantiles observados son números redondos —un millón,
ochocientos mil— porque la gente declara así. El amontonamiento se cuantifica
acá también, porque explica parte del desajuste y no es culpa del modelo.

Salida: datos/eph/lognormal-m07.json

    python datos/eph/preparar-lognormal-m07.py
"""

from __future__ import annotations

import os

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
SALIDA = Path(__file__).resolve().parent / "lognormal-m07.json"

CUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]


def leer() -> tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(EPH) as z:
        nombre = next(n for n in z.namelist() if "individual" in n.lower())
        with z.open(nombre) as f:
            d = pd.read_csv(
                f, sep=";", low_memory=False,
                usecols=["ESTADO", "P21", "PONDIIO"],
            )
    # Mismo universo que el caso ingresos-eph: ocupados con ingreso declarado
    # de la ocupación principal. P21 == -9 es no respuesta y viene con
    # PONDIIO == 0, así que el filtro del ponderador ya la excluye.
    u = d[(d.ESTADO == 1) & (d.P21 > 0) & (d.PONDIIO > 0)]
    return u.P21.to_numpy(float), u.PONDIIO.to_numpy(float)


def media(v: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * v) / w.sum())


def varianza(v: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * (v - media(v, w)) ** 2) / w.sum())


def momento(v: np.ndarray, w: np.ndarray, k: int) -> float:
    m, s = media(v, w), np.sqrt(varianza(v, w))
    return float(np.sum(w * ((v - m) / s) ** k) / w.sum())


def cuantil(v: np.ndarray, w: np.ndarray, q) -> np.ndarray:
    orden = np.argsort(v)
    v, w = v[orden], w[orden]
    # Definición de Hazen ponderada: acumulado menos medio peso, que es la que
    # deja la mediana en el lugar donde la acumulada cruza 0,5.
    c = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(q, c, v)


def main() -> None:
    x, w = leer()

    log = np.log(x)
    mu = media(log, w)
    sigma = float(np.sqrt(varianza(log, w)))
    s2 = sigma * sigma

    m_obs = media(x, w)
    sd_obs = float(np.sqrt(varianza(x, w)))
    med_obs = float(cuantil(x, w, 0.5))

    repetidos = pd.Series(x).value_counts()

    out = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "universo": (
            "Ocupados con ingreso declarado de la ocupación principal, "
            "total de 31 aglomerados urbanos"
        ),
        "advertencia": (
            "Ponderado con PONDIIO, igual que el caso ingresos-eph; "
            "el diseño real es por conglomerados."
        ),
        "n": int(len(x)),
        "poblacion": int(round(w.sum())),

        "ingreso": {
            "media": m_obs,
            "mediana": med_obs,
            "desvio": sd_obs,
            "cv": sd_obs / m_obs,
            "asimetria": momento(x, w, 3),
            "curtosis": momento(x, w, 4) - 3.0,
        },

        # Si la lognormal fuera el modelo correcto, estos dos tendrían que dar
        # cero. No dan: el logaritmo del ingreso queda asimétrico a izquierda.
        "log_ingreso": {
            "media": mu,
            "desvio": sigma,
            "asimetria": momento(log, w, 3),
            "curtosis": momento(log, w, 4) - 3.0,
        },

        "lognormal_ajustada": {
            "mu": mu,
            "sigma": sigma,
            "media": float(np.exp(mu + s2 / 2)),
            "mediana": float(np.exp(mu)),
            "modo": float(np.exp(mu - s2)),
            "cv": float(np.sqrt(np.exp(s2) - 1)),
            "asimetria": float((np.exp(s2) + 2) * np.sqrt(np.exp(s2) - 1)),
        },

        "normal_ajustada": {
            "media": m_obs,
            "desvio": sd_obs,
            "prob_bajo_cero": float(stats.norm.cdf(0, m_obs, sd_obs)),
            "p05": float(stats.norm.ppf(0.05, m_obs, sd_obs)),
        },

        "cuantiles": [
            {
                "q": q,
                "observado": float(cuantil(x, w, q)),
                "lognormal": float(np.exp(mu + sigma * stats.norm.ppf(q))),
                "normal": float(stats.norm.ppf(q, m_obs, sd_obs)),
            }
            for q in CUANTILES
        ],

        # Parte del desajuste no es del modelo: la gente declara números
        # redondos, y eso corre los cuantiles observados hacia esos valores.
        "amontonamiento": {
            "valores": [
                {"valor": float(v), "casos": int(c), "pct": 100.0 * c / len(x)}
                for v, c in repetidos.head(6).items()
            ],
            "pct_en_los_6_mas_repetidos": float(
                100.0 * repetidos.head(6).sum() / len(x)
            ),
        },
    }

    SALIDA.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ln = out["lognormal_ajustada"]
    print(f"n = {out['n']:,} · población {out['poblacion']:,}")
    print(f"\n== Ingreso ==")
    print(f"  media {m_obs:,.0f} · mediana {med_obs:,.0f} · "
          f"asimetría {out['ingreso']['asimetria']:.2f}")
    print(f"\n== Logaritmo del ingreso ==")
    print(f"  media {mu:.4f} · desvío {sigma:.4f} · "
          f"asimetría {out['log_ingreso']['asimetria']:.3f} · "
          f"curtosis {out['log_ingreso']['curtosis']:.3f}")
    print("  (si fuera lognormal, las dos últimas darían 0)")
    print(f"\n== Lognormal ajustada ==")
    print(f"  mediana {ln['mediana']:,.0f} (obs {med_obs:,.0f}) · "
          f"media {ln['media']:,.0f} (obs {m_obs:,.0f})")
    print(f"  modo {ln['modo']:,.0f} · CV {ln['cv']:.4f} "
          f"(obs {out['ingreso']['cv']:.4f})")
    print(f"\n== Amontonamiento ==")
    print(f"  {out['amontonamiento']['pct_en_los_6_mas_repetidos']:.1f} % "
          f"de la muestra en 6 valores")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

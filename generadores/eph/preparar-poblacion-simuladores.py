#!/usr/bin/env python
"""
La población de la que muestrean los simuladores del navegador.

Los simuladores del sitio no sortean de una normal teórica: sortean de la
distribución real de ingresos de la EPH, que tiene asimetría 5,5 y una cola
larguísima. Esa es toda la gracia —ver que la media de una población así
termina distribuyéndose normal es convincente; verlo partiendo de una normal no
demuestra nada—.

Como la base pesa demasiado para mandarla al navegador, se exporta una muestra
de la población YA EXPANDIDA por los ponderadores: cada caso se replica según su
factor de expansión y de ahí se sortea. El resultado es una población chica que
conserva la forma de la real, incluida la cola.

Salida: public/datos/poblacion-eph.json

    python datos/eph/preparar-poblacion-simuladores.py
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

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "public" / "datos" / "poblacion-eph.json"

SEMILLA = 1976
CUANTOS = 5000  # valores que viajan al navegador


def universo() -> tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(ESPEJO) as z, z.open("usu_individual_T126.txt") as f:
        d = pd.read_csv(
            f, sep=";", decimal=",", low_memory=False,
            usecols=["ESTADO", "P21", "PONDIIO", "CH06"],
        )
    u = d[(d.ESTADO == 1) & (d.P21 > 0) & (d.PONDIIO > 0)]
    return u, u.P21.to_numpy(float), u.PONDIIO.to_numpy(float)


def cobertura_real(poblacion: np.ndarray, rng) -> dict:
    """
    La cobertura que el intervalo del 95 % logra DE VERDAD sobre esta población.

    No es 95 %. El intervalo t supone que la media muestral se distribuye normal,
    y con una población tan asimétrica eso tarda en cumplirse: con n = 30 la
    cobertura real ronda el 90 %. Y los fallos no se reparten parejo —casi todos
    son intervalos que quedan CORTOS—, porque la cola larga hace que la mayoría
    de las muestras subestime la media y unas pocas la disparen.

    Es de los datos más útiles del sitio: dice con números cuánto vale en la
    práctica la promesa del 95 % cuando los datos no son de manual.
    """
    salida = {}
    mu = float(poblacion.mean())
    for n in (30, 50, 100, 200, 500):
        R = 20000
        m = rng.choice(poblacion, size=(R, n), replace=True)
        medias = m.mean(axis=1)
        desvios = m.std(axis=1, ddof=1)
        t = stats.t.ppf(0.975, n - 1)
        margen = t * desvios / np.sqrt(n)
        lo, hi = medias - margen, medias + margen
        salida[str(n)] = {
            "cobertura": round(100 * float(((lo <= mu) & (mu <= hi)).mean()), 1),
            "queda_corto": round(100 * float((hi < mu).mean()), 1),
            "se_pasa": round(100 * float((lo > mu).mean()), 1),
        }
    return salida


def main() -> None:
    u, ingresos, ponderadores = universo()
    rng = np.random.default_rng(SEMILLA)

    # Los parámetros poblacionales verdaderos, con ponderadores: son el valor
    # contra el que los simuladores comparan.
    p = ponderadores / ponderadores.sum()
    media = float(np.sum(ingresos * p))
    varianza = float(np.sum(p * (ingresos - media) ** 2))
    desvio = float(np.sqrt(varianza))
    asimetria = float(np.sum(p * ((ingresos - media) / desvio) ** 3))

    # La muestra que viaja: sorteada CON las probabilidades de expansión, así
    # que reproduce la población y no la base.
    idx = rng.choice(len(ingresos), size=CUANTOS, replace=True, p=p)
    poblacion = np.sort(ingresos[idx])

    # Los parámetros de lo que efectivamente viaja. Los simuladores usan ESTOS,
    # no los de arriba: si el navegador muestrea de esta lista, su "verdad"
    # poblacional es la de esta lista. Informar la otra sería mentir por unos
    # pesos de diferencia.
    media_exportada = float(poblacion.mean())
    desvio_exportado = float(poblacion.std(ddof=0))

    salida = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "variable": "Ingreso de la ocupación principal, ocupados con ingreso",
        "semilla": SEMILLA,
        "casos_en_la_base": int(len(ingresos)),
        "poblacion_expandida": int(round(ponderadores.sum())),
        "parametros_reales": {
            "media": round(media, 2),
            "desvio": round(desvio, 2),
            "asimetria": round(asimetria, 3),
        },
        "parametros_exportados": {
            "media": round(media_exportada, 2),
            "desvio": round(desvio_exportado, 2),
            "asimetria": round(float(stats.skew(poblacion)), 3),
            "mediana": round(float(np.median(poblacion)), 2),
            "minimo": float(poblacion.min()),
            "maximo": float(poblacion.max()),
        },
        "cobertura_real_del_95": cobertura_real(poblacion, rng),
        # Amontonamiento: la gente declara números redondos, y eso deja el
        # histograma dentado. No es ruido del muestreo, es cómo se mide.
        "amontonamiento": {
            "multiplos_de_100k": round(
                100 * float(np.mean(np.round(poblacion) % 100_000 == 0)), 1
            ),
            "valor_mas_declarado": int(
                pd.Series(poblacion).value_counts().idxmax()
            ),
            "porcentaje_del_mas_declarado": round(
                100 * float(pd.Series(poblacion).value_counts().max() / len(poblacion)), 1
            ),
            "valores_distintos": int(len(set(poblacion.tolist()))),
        },
        "n": CUANTOS,
        # Redondeados a la centena: no cambia nada estadísticamente y achica
        # bastante el archivo.
        "valores": [int(round(v, -2)) for v in poblacion],
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")

    peso = SALIDA.stat().st_size / 1024
    print(f"  {CUANTOS} valores exportados a public/datos/poblacion-eph.json ({peso:.0f} KB)")
    print(f"  población real:     media ${media:,.0f}  desvío ${desvio:,.0f}  asimetría {asimetria:.2f}")
    print(f"  la que viaja:       media ${media_exportada:,.0f}  desvío ${desvio_exportado:,.0f}")
    print(f"  diferencia en la media: {100 * abs(media_exportada - media) / media:.2f} %")
    print()
    print("  cobertura real del intervalo del 95 % sobre esta población:")
    for n, c in salida["cobertura_real_del_95"].items():
        print(f"    n={n:>4}  cubre {c['cobertura']:>5.1f} %   queda corto {c['queda_corto']:>4.1f} %   se pasa {c['se_pasa']:>4.1f} %")


if __name__ == "__main__":
    main()

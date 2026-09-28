#!/usr/bin/env python
"""
Qué significa realmente "95 % de confianza".

Toma la población de ingresos de la EPH, sortea 100 muestras, calcula el
intervalo de confianza del 95 % de cada una y dibuja los 100 intervalos contra
la media poblacional verdadera.

El resultado es la única forma de entender el concepto: la media poblacional es
fija y son los intervalos los que se mueven. Alrededor de 5 de cada 100 no la
contienen, y eso es exactamente lo que el 95 % promete.

Salida: src/figuras/cobertura-ic.svg  y  datos/eph/cobertura-ic.json

    python datos/eph/preparar-cobertura-ic.py
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
RAIZ = Path(__file__).resolve().parents[2]
SALIDA_SVG = RAIZ / "src" / "figuras" / "cobertura-ic.svg"
SALIDA_JSON = Path(__file__).resolve().parent / "cobertura-ic.json"

N_MUESTRA = 200
CUANTOS = 100
SEMILLA = 1976
Z = 1.959964


def universo() -> tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(ESPEJO) as z, z.open("usu_individual_T126.txt") as f:
        d = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                        usecols=["ESTADO", "P21", "PONDIIO"])
    u = d[(d.ESTADO == 1) & (d.P21 > 0) & (d.PONDIIO > 0)]
    return u.P21.to_numpy(float), u.PONDIIO.to_numpy(float)


def pesos(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def main() -> None:
    x, w = universo()
    prob = w / w.sum()
    mu = float((w * x).sum() / w.sum())

    rng = np.random.default_rng(SEMILLA)
    idx = rng.choice(len(x), size=(CUANTOS, N_MUESTRA), p=prob)
    muestras = x[idx]

    medias = muestras.mean(axis=1)
    ee = muestras.std(axis=1, ddof=1) / np.sqrt(N_MUESTRA)
    bajo = medias - Z * ee
    alto = medias + Z * ee
    contiene = (bajo <= mu) & (mu <= alto)

    # --- SVG ---
    AN, AL = 720, 300
    ML, MR, MT, MB = 12, 12, 26, 34
    gw, gh = AN - ML - MR, AL - MT - MB

    lo = float(min(bajo.min(), mu))
    hi = float(max(alto.max(), mu))
    pad = (hi - lo) * 0.04
    lo, hi = lo - pad, hi + pad

    def px(v):
        return ML + gw * (v - lo) / (hi - lo)

    def py(i):
        return MT + gh * (i + 0.5) / CUANTOS

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="Cien intervalos de confianza '
         f'del 95 % y la media poblacional">']

    # la media poblacional: la única línea fija del gráfico
    p.append(f'<line class="mediana" x1="{px(mu):.1f}" y1="{MT - 6}" '
             f'x2="{px(mu):.1f}" y2="{MT + gh + 4}"/>')
    p.append(f'<text class="rotulo-mediana" x="{px(mu):.1f}" y="{MT - 12}" '
             f'text-anchor="middle">μ = {pesos(mu)}</text>')

    for i in range(CUANTOS):
        clase = "bigote" if contiene[i] else "media"
        p.append(f'<line class="{clase}" x1="{px(bajo[i]):.1f}" y1="{py(i):.1f}" '
                 f'x2="{px(alto[i]):.1f}" y2="{py(i):.1f}" stroke-width="1.6"/>')

    p.append(f'<line class="eje" x1="{ML}" y1="{MT + gh + 10}" '
             f'x2="{ML + gw}" y2="{MT + gh + 10}"/>')
    for t in (0, 0.5, 1):
        v = lo + t * (hi - lo)
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{AL - 8}" '
                 f'text-anchor="{"start" if t == 0 else "end" if t == 1 else "middle"}">'
                 f'{pesos(v)}</text>')

    fallan = int((~contiene).sum())
    p.append(f'<text class="rotulo-media" x="{ML}" y="{MT - 12}">'
             f'{fallan} de {CUANTOS} no contienen a μ</text>')

    p.append("</svg>")
    SALIDA_SVG.write_text("\n".join(p), encoding="utf-8")

    salida = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "n_por_muestra": N_MUESTRA,
        "cantidad_de_muestras": CUANTOS,
        "semilla": SEMILLA,
        "media_poblacional": round(mu),
        "contienen": int(contiene.sum()),
        "no_contienen": fallan,
        "ancho_medio": round(float((alto - bajo).mean())),
    }
    SALIDA_JSON.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    print(f"μ = {pesos(mu)}   n por muestra = {N_MUESTRA}")
    print(f"{contiene.sum()} de {CUANTOS} intervalos contienen a μ")
    print(f"ancho medio del intervalo: {pesos((alto - bajo).mean())}")
    print(f"\nfigura: {SALIDA_SVG.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

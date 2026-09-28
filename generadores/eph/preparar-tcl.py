#!/usr/bin/env python
"""
Teorema central del límite, con la distribución de ingresos real.

Toma la distribución del ingreso de la ocupación principal de la EPH —que tiene
asimetría 5,46, o sea lo más lejos de una normal que se puede pedir— y simula la
distribución muestral de la media para varios tamaños de muestra.

El resultado muestra el TCL funcionando sobre datos argentinos de verdad: la
población está torcidísima y la distribución de las medias se vuelve simétrica
igual.

Salida: src/figuras/tcl-ingresos.svg  y  datos/eph/tcl.json

    python datos/eph/preparar-tcl.py
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
SALIDA_SVG = RAIZ / "src" / "figuras" / "tcl-ingresos.svg"
SALIDA_JSON = Path(__file__).resolve().parent / "tcl.json"

TAMANOS = [2, 10, 50]
REPETICIONES = 20_000
SEMILLA = 1976


def universo() -> tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(ESPEJO) as z, z.open("usu_individual_T126.txt") as f:
        d = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                        usecols=["ESTADO", "P21", "PONDIIO"])
    u = d[(d.ESTADO == 1) & (d.P21 > 0) & (d.PONDIIO > 0)]
    return u.P21.to_numpy(float), u.PONDIIO.to_numpy(float)


def pesos(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def millones(v: float) -> str:
    t = f"{v / 1_000_000:.1f}".replace(".", ",")
    return (t.rstrip("0").rstrip(",") or "0") + " M"


def histograma(ax_x0, ax_y0, an, al, datos, media_pob, titulo, subtitulo, corte):
    """Dibuja un panel y devuelve la lista de elementos SVG."""
    ML, MR, MT, MB = 8, 8, 26, 30
    gw, gh = an - ML - MR, al - MT - MB

    # Los valores por encima del corte se **excluyen**, no se apilan en la
    # última barra: apilarlos dibuja un pico que no existe.
    bordes = np.linspace(0, corte, 34)
    frec, _ = np.histogram(datos[datos <= corte], bins=bordes)
    frec = frec / frec.sum()
    ymax = frec.max() * 1.18

    def px(v):
        return ax_x0 + ML + gw * v / corte

    def py(v):
        return ax_y0 + MT + gh * (1 - v / ymax)

    p = [f'<text class="rotulo" x="{ax_x0 + ML}" y="{ax_y0 + 13}">{titulo}</text>',
         f'<text class="rotulo-chico" x="{ax_x0 + an - MR}" y="{ax_y0 + 13}" '
         f'text-anchor="end">{subtitulo}</text>']

    for (a, b), h in zip(zip(bordes[:-1], bordes[1:]), frec):
        if h <= 0:
            continue
        p.append(f'<rect class="barra" x="{px(a):.1f}" y="{py(h):.1f}" '
                 f'width="{max(px(b) - px(a) - 1, 0.8):.1f}" '
                 f'height="{ax_y0 + MT + gh - py(h):.1f}"/>')

    p.append(f'<line class="eje" x1="{ax_x0 + ML}" y1="{ax_y0 + MT + gh}" '
             f'x2="{ax_x0 + ML + gw}" y2="{ax_y0 + MT + gh}"/>')

    # la media poblacional, que es la misma en los cuatro paneles
    p.append(f'<line class="media" x1="{px(media_pob):.1f}" '
             f'y1="{ax_y0 + MT - 4}" x2="{px(media_pob):.1f}" '
             f'y2="{ax_y0 + MT + gh}"/>')

    for t in (0, 0.5, 1):
        v = t * corte
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" '
                 f'y="{ax_y0 + MT + gh + 16}" '
                 f'text-anchor="{"start" if t == 0 else "end" if t == 1 else "middle"}">'
                 f'{millones(v)}</text>')
    return p


def main() -> None:
    x, w = universo()
    prob = w / w.sum()
    media_pob = float((w * x).sum() / w.sum())
    sd_pob = float(np.sqrt((w * (x - media_pob) ** 2).sum() / w.sum()))

    rng = np.random.default_rng(SEMILLA)
    resultados = {}
    medias = {}
    for n in TAMANOS:
        idx = rng.choice(len(x), size=(REPETICIONES, n), p=prob)
        m = x[idx].mean(axis=1)
        medias[n] = m
        resultados[n] = {
            "media_de_las_medias": float(m.mean()),
            "desvio_observado": float(m.std(ddof=1)),
            "error_estandar_teorico": float(sd_pob / np.sqrt(n)),
            "asimetria": float(((m - m.mean()) ** 3).mean() / m.std() ** 3),
        }

    # --- SVG: 2 × 2 paneles ---
    AN, AL = 720, 400
    PAN_AN, PAN_AL = 360, 200
    CORTE = 3_000_000

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="El teorema central del límite '
         f'sobre la distribución del ingreso">']

    p += histograma(0, 0, PAN_AN, PAN_AL, x, media_pob,
                    "La población", f"asimetría 5,46", CORTE)
    for i, n in enumerate(TAMANOS, start=1):
        fila, col = divmod(i, 2)
        r = resultados[n]
        p += histograma(col * PAN_AN, fila * PAN_AL, PAN_AN, PAN_AL,
                        medias[n], media_pob,
                        f"Medias de muestras de n = {n}",
                        f"asimetría {r['asimetria']:.2f}".replace(".", ","),
                        CORTE)

    p.append("</svg>")
    SALIDA_SVG.write_text("\n".join(p), encoding="utf-8")

    salida = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "repeticiones": REPETICIONES,
        "semilla": SEMILLA,
        "media_poblacional": round(media_pob),
        "desvio_poblacional": round(sd_pob),
        "asimetria_poblacional": 5.46,
        "por_tamano": {str(n): {k: round(v, 3) for k, v in r.items()}
                       for n, r in resultados.items()},
    }
    SALIDA_JSON.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    print(f"población: media {pesos(media_pob)} · desvío {pesos(sd_pob)} · asimetría 5,46\n")
    print(f"{'n':>4} {'media de medias':>18} {'desvío observado':>18} "
          f"{'σ/√n teórico':>16} {'asimetría':>11}")
    for n in TAMANOS:
        r = resultados[n]
        print(f"{n:>4} {pesos(r['media_de_las_medias']):>18} "
              f"{pesos(r['desvio_observado']):>18} "
              f"{pesos(r['error_estandar_teorico']):>16} "
              f"{r['asimetria']:>11.2f}")
    print(f"\nfigura: {SALIDA_SVG.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

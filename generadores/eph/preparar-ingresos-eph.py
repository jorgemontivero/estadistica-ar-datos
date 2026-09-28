#!/usr/bin/env python
"""
Caso `ingresos-eph` — del microdato del INDEC a los artefactos del sitio.

Lee el ZIP del espejo local de la EPH, arma el universo, calcula los
estadísticos ponderados y escribe:

    public/datos/ingresos-eph.csv          extracto reducido, descargable
    src/figuras/ingresos-eph-*.svg         figuras temables (claro y oscuro)
    datos/eph/ingresos-eph.json            los números, para citar en el texto

Se vuelve a correr entero cuando el INDEC publica un trimestre nuevo:

    python datos/eph/preparar-ingresos-eph.py

Fuente: INDEC, Encuesta Permanente de Hogares, base usuario, 1º trimestre 2026.
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

# --- Parámetros -------------------------------------------------------------

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
INTERNO = "usu_individual_T126.txt"
PERIODO = "1º trimestre de 2026"
PERIODO_CORTO = "1T 2026"

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_CSV = RAIZ / "public" / "datos" / "ingresos-eph.csv"
SALIDA_FIG = RAIZ / "src" / "figuras"
SALIDA_JSON = Path(__file__).resolve().parent / "ingresos-eph.json"

# Corte del eje de los gráficos. La cola sigue: se declara en el pie.
CORTE = 3_000_000
ANCHO_CLASE = 200_000


# --- Utilidades estadísticas ------------------------------------------------


def cuantil_ponderado(x: np.ndarray, w: np.ndarray, q) -> np.ndarray:
    """Cuantiles con ponderadores, por interpolación sobre la acumulada."""
    orden = np.argsort(x)
    xs, ws = x[orden], w[orden]
    acum = np.cumsum(ws)
    p = (acum - 0.5 * ws) / ws.sum()
    return np.interp(q, p, xs)


# --- Lectura ----------------------------------------------------------------


def leer() -> pd.DataFrame:
    columnas = [
        "AGLOMERADO", "CH04", "CH06", "NIVEL_ED",
        "ESTADO", "CAT_OCUP", "P21", "PONDIIO", "PONDERA", "PP3E_TOT",
    ]
    with zipfile.ZipFile(ESPEJO) as z, z.open(INTERNO) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def universo(d: pd.DataFrame) -> pd.DataFrame:
    """
    Ocupados con ingreso declarado de la ocupación principal.

    P21 == -9 es no respuesta y va siempre con PONDIIO == 0: el INDEC ya
    redistribuye ese peso entre quienes sí respondieron. Excluirlos no
    subrepresenta a nadie; dejarlos entrar como "cero" sí.
    """
    return d[(d.ESTADO == 1) & (d.P21 > 0) & (d.PONDIIO > 0)].copy()


# --- SVG --------------------------------------------------------------------

# Los estilos viven en src/styles/global.css, bajo la clase `.grafico`.
# El SVG se inyecta en la página, así que hereda las variables del sitio y
# funciona igual en tema claro y oscuro.


def millones(v: float) -> str:
    if v == 0:
        return "0"
    return f"{v / 1_000_000:.1f}".replace(".", ",").rstrip("0").rstrip(",") + " M"


def pesos(v: float) -> str:
    return "$" + f"{v:,.0f}".replace(",", ".")


def histograma(x, w, est) -> str:
    AN, AL = 720, 340
    ML, MR, MT, MB = 56, 22, 26, 52
    gw, gh = AN - ML - MR, AL - MT - MB

    bordes = np.arange(0, CORTE + ANCHO_CLASE, ANCHO_CLASE)
    peso_total = w.sum()
    alturas = [
        100 * w[(x >= a) & (x < b)].sum() / peso_total
        for a, b in zip(bordes[:-1], bordes[1:])
    ]
    ymax = max(alturas) * 1.12

    def px(v):
        return ML + gw * v / CORTE

    def py(v):
        return MT + gh * (1 - v / ymax)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="Histograma del ingreso de '
         f'la ocupación principal">']

    # guías horizontales
    for v in np.arange(0, ymax, 2):
        if v == 0:
            continue
        p.append(f'<line class="guia" x1="{ML}" y1="{py(v):.1f}" '
                 f'x2="{ML + gw}" y2="{py(v):.1f}"/>')
        p.append(f'<text class="rotulo-chico" x="{ML - 8}" y="{py(v) + 4:.1f}" '
                 f'text-anchor="end">{v:.0f} %</text>')

    # barras
    for (a, b), h in zip(zip(bordes[:-1], bordes[1:]), alturas):
        x0, x1 = px(a), px(b)
        p.append(f'<rect class="barra" x="{x0 + 1:.1f}" y="{py(h):.1f}" '
                 f'width="{x1 - x0 - 2:.1f}" height="{MT + gh - py(h):.1f}"/>')

    # eje x
    p.append(f'<line class="eje" x1="{ML}" y1="{MT + gh}" '
             f'x2="{ML + gw}" y2="{MT + gh}"/>')
    for v in range(0, CORTE + 1, 500_000):
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" '
                 f'y="{MT + gh + 18}" text-anchor="middle">{millones(v)}</text>')
    p.append(f'<text class="rotulo" x="{ML + gw / 2:.0f}" y="{AL - 8}" '
             f'text-anchor="middle">Ingreso de la ocupación principal '
             f'(millones de pesos)</text>')

    # mediana y media
    xm, xp = px(est["mediana"]), px(est["media"])
    p.append(f'<line class="mediana" x1="{xm:.1f}" y1="{MT - 4}" '
             f'x2="{xm:.1f}" y2="{MT + gh}"/>')
    p.append(f'<text class="rotulo-mediana" x="{xm - 8:.1f}" y="{MT + 6}" '
             f'text-anchor="end">Mediana {pesos(est["mediana"])}</text>')
    p.append(f'<line class="media" x1="{xp:.1f}" y1="{MT - 4}" '
             f'x2="{xp:.1f}" y2="{MT + gh}"/>')
    p.append(f'<text class="rotulo-media" x="{xp + 8:.1f}" y="{MT + 6}">'
             f'Media {pesos(est["media"])}</text>')

    p.append("</svg>")
    return "\n".join(p)


def boxplot(x, w, est) -> str:
    AN, AL = 720, 190
    ML, MR, MT = 56, 22, 30
    gw = AN - ML - MR
    cy, alto = MT + 34, 46

    lim_sup = est["q3"] + 1.5 * est["ric"]

    def px(v):
        return ML + gw * min(v, CORTE) / CORTE

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="Diagrama de caja del '
         f'ingreso de la ocupación principal">']

    # bigotes
    p.append(f'<line class="bigote" x1="{px(est["minimo"]):.1f}" y1="{cy}" '
             f'x2="{px(est["q1"]):.1f}" y2="{cy}"/>')
    p.append(f'<line class="bigote" x1="{px(est["q3"]):.1f}" y1="{cy}" '
             f'x2="{px(lim_sup):.1f}" y2="{cy}"/>')
    for v in (est["minimo"], lim_sup):
        p.append(f'<line class="bigote" x1="{px(v):.1f}" y1="{cy - 11}" '
                 f'x2="{px(v):.1f}" y2="{cy + 11}"/>')

    # caja
    p.append(f'<rect class="caja" x="{px(est["q1"]):.1f}" y="{cy - alto / 2}" '
             f'width="{px(est["q3"]) - px(est["q1"]):.1f}" height="{alto}"/>')
    p.append(f'<line class="mediana" x1="{px(est["mediana"]):.1f}" '
             f'y1="{cy - alto / 2}" x2="{px(est["mediana"]):.1f}" '
             f'y2="{cy + alto / 2}"/>')

    # la media, que queda adentro de la caja pero corrida a la derecha
    p.append(f'<line class="media" x1="{px(est["media"]):.1f}" '
             f'y1="{cy - alto / 2 - 6}" x2="{px(est["media"]):.1f}" '
             f'y2="{cy + alto / 2 + 6}"/>')

    # rótulos de los cinco números
    for v, t, dy in [
        (est["q1"], f'Q1 {pesos(est["q1"])}', -alto / 2 - 10),
        (est["mediana"], f'Mediana {pesos(est["mediana"])}', alto / 2 + 20),
        (est["q3"], f'Q3 {pesos(est["q3"])}', -alto / 2 - 10),
    ]:
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{cy + dy:.0f}" '
                 f'text-anchor="middle">{t}</text>')

    p.append(f'<text class="rotulo-media" x="{px(est["media"]):.1f}" '
             f'y="{cy - alto / 2 - 24:.0f}" text-anchor="middle">'
             f'Media {pesos(est["media"])}</text>')

    # zona de atípicos: el rótulo va arriba a la derecha, anclado al margen,
    # porque el bigote llega casi al borde del lienzo
    p.append(f'<text class="rotulo-chico" x="{ML + gw}" y="{MT - 4}" '
             f'text-anchor="end">{est["pct_atipicos"]:.1f} % de los ocupados '
             f'supera los {pesos(est["limite_superior"])} →</text>')

    # eje
    p.append(f'<line class="eje" x1="{ML}" y1="{AL - 34}" '
             f'x2="{ML + gw}" y2="{AL - 34}"/>')
    for v in range(0, CORTE + 1, 500_000):
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{AL - 16}" '
                 f'text-anchor="middle">{millones(v)}</text>')

    p.append("</svg>")
    return "\n".join(p)


# --- Programa ---------------------------------------------------------------


def codificacion(d: pd.DataFrame) -> dict:
    """Cómo viene codificado P21 y qué pasa si se lo promedia sin leer el
    diccionario. Para la entrada del diccionario de variables."""
    ETIQ = {0: "Entrevista no realizada", 1: "Ocupado", 2: "Desocupado",
            3: "Inactivo", 4: "Menor de 10 años"}
    por_estado = [
        {"estado": int(k), "etiqueta": ETIQ[int(k)],
         "n": int((d["ESTADO"] == k).sum()),
         "p21_cero": int(((d["ESTADO"] == k) & (d["P21"] == 0)).sum()),
         "p21_menos9": int(((d["ESTADO"] == k) & (d["P21"] == -9)).sum()),
         "p21_positivo": int(((d["ESTADO"] == k) & (d["P21"] > 0)).sum())}
        for k in sorted(ETIQ)]
    ocupados = d[(d["ESTADO"] == 1) & (d["P21"] > 0)]["P21"]
    return {
        "n_filas": int(len(d)),
        "p21_sin_vacios": bool(d["P21"].isna().sum() == 0),
        "p21_valores_negativos": sorted(int(v) for v in d["P21"][d["P21"] < 0].unique()),
        "por_estado": por_estado,
        "estado_4_son_menores_de_10": bool(
            (d.loc[d["ESTADO"] == 4, "CH06"] < 10).all()
            and (d.loc[d["CH06"] < 10, "ESTADO"] == 4).all()),
        "ch06_negativos": {"valores": sorted(int(v) for v in d["CH06"][d["CH06"] < 0].unique()),
                           "n": int((d["CH06"] < 0).sum())},
        "promedios": {
            "toda_la_columna": float(d["P21"].mean()),
            "descartando_los_menos9": float(d["P21"][d["P21"] >= 0].mean()),
            "correcto_ocupados_con_ingreso": float(ocupados.mean()),
        },
    }


def no_respuesta(d: pd.DataFrame) -> dict:
    """Qué hace el INDEC con quien no declara su ingreso, y en qué se
    diferencian esos casos de los que sí responden."""
    o = d[d["ESTADO"] == 1]
    nr = o[o["P21"] == -9]
    si = o[o["P21"] > 0]

    def perfil(s):
        h = s["PP3E_TOT"] if "PP3E_TOT" in s else pd.Series(dtype=float)
        return {
            "n": int(len(s)),
            "edad_media": float(s["CH06"].mean()),
            "pct_mujeres": float(100 * (s["CH04"] == 2).mean()),
            "pct_superior": float(100 * s["NIVEL_ED"].isin([5, 6]).mean()),
            "pct_hasta_primario": float(100 * s["NIVEL_ED"].isin([1, 2]).mean()),
            "pct_asalariados": float(100 * (s["CAT_OCUP"] == 3).mean()),
            "pct_patrones": float(100 * (s["CAT_OCUP"] == 1).mean()),
            "pct_cuenta_propia": float(100 * (s["CAT_OCUP"] == 2).mean()),
        }

    return {
        "ocupados": int(len(o)),
        "no_respondieron": int(len(nr)),
        "pct_no_respuesta": float(100 * len(nr) / len(o)),
        "pondiio_de_los_que_no_responden_es_cero": bool((nr["PONDIIO"] == 0).all()),
        "poblacion": {
            "pondera_todos_los_ocupados": int(o["PONDERA"].sum()),
            "pondiio_todos_los_ocupados": int(o["PONDIIO"].sum()),
            "pondiio_de_los_que_responden": int(si["PONDIIO"].sum()),
            "pondera_de_los_que_responden": int(si["PONDERA"].sum()),
        },
        "perfil": {"no_respondieron": perfil(nr), "respondieron": perfil(si)},
        "no_respuesta_por_nivel_educativo": [
            {"nivel": int(k),
             "pct": float(100 * (o[o["NIVEL_ED"] == k]["P21"] == -9).mean()),
             "n": int((o["NIVEL_ED"] == k).sum())}
            for k in range(1, 7) if (o["NIVEL_ED"] == k).any()
        ],
    }


def main() -> None:
    d = leer()
    u = universo(d)
    x = u.P21.to_numpy(float)
    w = u.PONDIIO.to_numpy(float)

    W = w.sum()
    media = float((w * x).sum() / W)
    sd = float(np.sqrt((w * (x - media) ** 2).sum() / W))
    q1, mediana, q3 = (float(v) for v in cuantil_ponderado(x, w, [.25, .5, .75]))
    ric = q3 - q1
    lim_sup = q3 + 1.5 * ric
    masa = (w * x).sum()
    d9 = float(cuantil_ponderado(x, w, 0.9))

    est = {
        "periodo": PERIODO,
        "periodo_corto": PERIODO_CORTO,
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "codificacion": codificacion(d),
        "no_respuesta": no_respuesta(d),
        "universo": "Ocupados con ingreso declarado de la ocupación principal, "
                    "total de 31 aglomerados urbanos",
        "n": int(len(x)),
        "poblacion": int(round(W)),
        "media": round(media),
        "mediana": round(mediana),
        "q1": round(q1),
        "q3": round(q3),
        "ric": round(ric),
        "desvio": round(sd),
        "cv": round(sd / media, 3),
        "asimetria": round(float((w * (x - media) ** 3).sum() / W / sd ** 3), 2),
        "minimo": float(x.min()),
        "maximo": float(x.max()),
        "razon_media_mediana": round(media / mediana, 3),
        "pct_bajo_la_media": round(100 * w[x < media].sum() / W, 1),
        "limite_superior": round(lim_sup),
        "pct_atipicos": round(100 * w[x > lim_sup].sum() / W, 1),
        "masa_decil_10": round(100 * (w[x >= d9] * x[x >= d9]).sum() / masa, 1),
        "pct_fuera_del_grafico": round(100 * w[x > CORTE].sum() / W, 1),
        "deciles": {f"D{i}": round(float(cuantil_ponderado(x, w, i / 10)))
                    for i in range(1, 10)},
    }

    # --- extracto descargable ---
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    (u.rename(columns={
        "AGLOMERADO": "aglomerado", "CH04": "sexo", "CH06": "edad",
        "NIVEL_ED": "nivel_ed", "CAT_OCUP": "cat_ocup",
        "P21": "ingreso_ocup_principal", "PONDIIO": "ponderador",
    })[["aglomerado", "sexo", "edad", "nivel_ed", "cat_ocup",
        "ingreso_ocup_principal", "ponderador"]]
     .to_csv(SALIDA_CSV, index=False, encoding="utf-8"))

    # --- figuras ---
    SALIDA_FIG.mkdir(parents=True, exist_ok=True)
    (SALIDA_FIG / "ingresos-eph-histograma.svg").write_text(
        histograma(x, w, est), encoding="utf-8")
    (SALIDA_FIG / "ingresos-eph-boxplot.svg").write_text(
        boxplot(x, w, est), encoding="utf-8")

    SALIDA_JSON.write_text(
        json.dumps(est, ensure_ascii=False, indent=2), encoding="utf-8")

    cod = est["codificacion"]
    print("\nCodificación de P21 (para el diccionario de variables):")
    print("  %-24s %8s %9s %9s %9s" % ("ESTADO", "n", "P21=0", "P21=-9", "P21>0"))
    for f in cod["por_estado"]:
        print("  %-24s %8d %9d %9d %9d"
              % (f["etiqueta"], f["n"], f["p21_cero"], f["p21_menos9"],
                 f["p21_positivo"]))
    pr = cod["promedios"]
    print(f"  sin vacíos en P21: {cod['p21_sin_vacios']} · "
          f"negativos: {cod['p21_valores_negativos']}")
    print(f"  promedio de toda la columna {pesos(pr['toda_la_columna'])} · "
          f"sin los -9 {pesos(pr['descartando_los_menos9'])} · "
          f"correcto {pesos(pr['correcto_ocupados_con_ingreso'])}")
    nrp = est["no_respuesta"]
    pb = nrp["poblacion"]
    print(f"  no respuesta de ingreso: {nrp['no_respondieron']} de "
          f"{nrp['ocupados']} ({nrp['pct_no_respuesta']:.1f} %) · "
          f"PONDIIO cero: {nrp['pondiio_de_los_que_no_responden_es_cero']}")
    print(f"  población: PONDERA {pb['pondera_todos_los_ocupados']:,} · "
          f"PONDIIO {pb['pondiio_todos_los_ocupados']:,} · "
          f"razón {pb['pondiio_todos_los_ocupados'] / pb['pondera_todos_los_ocupados']:.4f}")
    a, b = nrp["perfil"]["no_respondieron"], nrp["perfil"]["respondieron"]
    for cl in ("pct_superior", "pct_asalariados", "pct_patrones", "pct_cuenta_propia"):
        print(f"    {cl:22} no respondió {a[cl]:5.1f} % · respondió {b[cl]:5.1f} %")
    print(f"  CH06 negativos: {cod['ch06_negativos']['valores']} "
          f"({cod['ch06_negativos']['n']} casos)")

    print(f"\nn = {est['n']:,} · población = {est['poblacion']:,}")
    print(f"media {pesos(est['media'])} · mediana {pesos(est['mediana'])}")
    print(f"{est['pct_bajo_la_media']} % gana menos que el promedio")
    print(f"\nCSV     {SALIDA_CSV.relative_to(RAIZ)} "
          f"({SALIDA_CSV.stat().st_size / 1024:.0f} KB)")
    print(f"figuras {SALIDA_FIG.relative_to(RAIZ)}")
    print(f"números {SALIDA_JSON.name}")


if __name__ == "__main__":
    main()

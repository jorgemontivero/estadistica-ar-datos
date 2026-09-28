#!/usr/bin/env python
"""
Índices y series de tiempo de referencia para el módulo M04.

Dos fuentes, dos mitades del módulo:

  IPC (INDEC, base diciembre 2016) · números índice, variaciones mensual,
      interanual y acumulada, cambio de base, empalme y deflactación del
      ingreso de la EPH a pesos constantes.

  EOH (Encuesta de Ocupación Hotelera) · pernoctaciones mensuales desde 2018:
      una serie con estacionalidad marcada y un shock enorme en 2020, ideal
      para medias móviles, descomposición y desestacionalización.

Salida: datos/series/indices-m04.json
        src/figuras/serie-pernoctes.svg
        src/figuras/ipc-variaciones.svg

    python datos/series/preparar-indices-m04.py
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

MACRO = Path(DATOS + r"\Macro_fiscal")
TURISMO = Path(DATOS + r"\Turismo"
               r"\encuesta-ocupacion-hotelera-parahotelera-eoh")
EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "indices-m04.json"
FIGURAS = AQUI.parent.parent / "src" / "figuras"

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def serie_svg(nombre, fechas, series, etiquetas, titulo_y,
              formato=lambda v: f"{v:,.0f}") -> None:
    """Gráfico de líneas simple, una o varias series."""
    W, H = 720, 320
    ML, MR, MT, MB = 74, 16, 26, 48
    todos = np.concatenate([s[~np.isnan(s)] for s in series])
    y0, y1 = float(todos.min()), float(todos.max())
    y0 -= (y1 - y0) * 0.06
    y1 += (y1 - y0) * 0.06
    n = len(fechas)

    def px(i):
        return ML + i / (n - 1) * (W - ML - MR)

    def py(v):
        return H - MB - (v - y0) / (y1 - y0) * (H - MT - MB)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" aria-label="{titulo_y}">']
    for frac in (0, 0.25, 0.5, 0.75, 1):
        v = y0 + frac * (y1 - y0)
        p.append(f'<line class="guia" x1="{ML}" y1="{py(v):.1f}" '
                 f'x2="{W-MR}" y2="{py(v):.1f}"/>')
        p.append(f'<text class="rotulo-chico" x="{ML-8}" y="{py(v)+4:.1f}" '
                 f'text-anchor="end">{formato(v)}</text>')
    clases = ["recta", "bigote", "mediana"]
    for k, s in enumerate(series):
        pts = " ".join(f"{px(i):.1f},{py(v):.1f}"
                       for i, v in enumerate(s) if not np.isnan(v))
        p.append(f'<polyline class="{clases[k % len(clases)]}" fill="none" '
                 f'points="{pts}"/>')
    p.append(f'<line class="eje" x1="{ML}" y1="{H-MB}" x2="{W-MR}" '
             f'y2="{H-MB}"/>')
    anios = sorted({f.year for f in fechas})
    for a in anios:
        idx = [i for i, f in enumerate(fechas) if f.year == a and f.month == 1]
        if idx:
            p.append(f'<text class="rotulo-chico" x="{px(idx[0]):.1f}" '
                     f'y="{H-MB+18}" text-anchor="middle">{a}</text>')
    for k, e in enumerate(etiquetas):
        p.append(f'<text class="rotulo" x="{ML + k*180}" y="{MT-8}">{e}</text>')
    p.append("</svg>")
    (FIGURAS / nombre).write_text("\n".join(p), encoding="utf-8")
    print(f"→ {FIGURAS / nombre}")


def main() -> None:
    out = {}

    # ---- 1 · IPC ----------------------------------------------------------
    ipc = pd.read_csv(
        MACRO / "indice-de-precios-al-consumidor-nacional-ipc-base-diciembre-2016"
        / "Indice_de_Precios_al_Consumidor._Nivel_Gener__indice-precios-al-consumidor-nivel-general-bas.csv",
        encoding="utf-8-sig")
    ipc["fecha"] = pd.to_datetime(ipc["indice_tiempo"])
    ipc = ipc.dropna(subset=["ipc_ng_nacional"]).sort_values("fecha")

    ipc["var_mensual"] = ipc["ipc_ng_nacional"].pct_change()
    ipc["var_interanual"] = ipc["ipc_ng_nacional"].pct_change(12)
    ipc["anio"] = ipc["fecha"].dt.year

    ult = ipc.iloc[-1]
    dic_anterior = ipc[(ipc["anio"] == ult["anio"] - 1)
                       & (ipc["fecha"].dt.month == 12)]
    acum = (ult["ipc_ng_nacional"] / dic_anterior["ipc_ng_nacional"].iloc[0] - 1
            if len(dic_anterior) else None)

    # Variación de diciembre a diciembre por año
    dics = ipc[ipc["fecha"].dt.month == 12].set_index("anio")["ipc_ng_nacional"]
    anual = (dics.pct_change().dropna() * 100).round(1)

    out["ipc"] = {
        "fuente": "IPC nacional, nivel general, base diciembre 2016 = 100. INDEC",
        "primer_dato": str(ipc["fecha"].iloc[0].date()),
        "ultimo_dato": str(ult["fecha"].date()),
        "indice_ultimo": float(ult["ipc_ng_nacional"]),
        "var_mensual_ultima": float(ult["var_mensual"]),
        "var_interanual_ultima": float(ult["var_interanual"]),
        "var_acumulada_anio": float(acum) if acum is not None else None,
        "variacion_anual_dic_dic": {int(k): float(v) for k, v in anual.items()},
        "por_region_ultimo": {
            c.replace("ipc_ng_", ""): float(ult[c])
            for c in ipc.columns
            if c.startswith("ipc_ng_") and "tasa" not in c
        },
    }

    # ---- 2 · Cambio de base y empalme --------------------------------------
    base_nueva = ipc[ipc["fecha"] == "2023-12-01"]["ipc_ng_nacional"]
    if len(base_nueva):
        factor = 100 / float(base_nueva.iloc[0])
        out["cambio_de_base"] = {
            "base_original": "diciembre 2016 = 100",
            "base_nueva": "diciembre 2023 = 100",
            "indice_dic_2023_en_base_vieja": float(base_nueva.iloc[0]),
            "factor": factor,
            "ejemplo_ultimo_en_base_nueva": float(ult["ipc_ng_nacional"] * factor),
        }

    # ---- 3 · Deflactación del ingreso de la EPH ---------------------------
    with zipfile.ZipFile(EPH) as z, z.open("usu_individual_T126.txt") as f:
        ind = pd.read_csv(f, sep=";", decimal=",",
                          usecols=["ESTADO", "P21", "PONDIIO"],
                          low_memory=False)
    oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)]
    media_nominal = float((oc["P21"] * oc["PONDIIO"]).sum()
                          / oc["PONDIIO"].sum())

    # Índice del trimestre de la EPH (promedio ene-mar 2026) y de un año antes
    def promedio_trimestre(anio, meses=(1, 2, 3)):
        m = ipc[(ipc["anio"] == anio) & (ipc["fecha"].dt.month.isin(meses))]
        return float(m["ipc_ng_nacional"].mean()) if len(m) else None

    i_actual = promedio_trimestre(2026)
    i_previo = promedio_trimestre(2025)
    out["deflactacion"] = {
        "media_nominal_1T2026": media_nominal,
        "ipc_promedio_1T2026": i_actual,
        "ipc_promedio_1T2025": i_previo,
        "factor": (i_actual / i_previo) if (i_actual and i_previo) else None,
        "media_a_precios_1T2025": (media_nominal * i_previo / i_actual
                                   if (i_actual and i_previo) else None),
    }

    # ---- 4 · Serie estacional: pernoctaciones -----------------------------
    per = pd.read_csv(
        TURISMO / "Pernoctes en hoteles y parahoteles según tipo de residencia.csv",
        encoding="utf-8-sig")
    # Formato largo: una fila por mes y tipo de residencia
    per["fecha"] = pd.to_datetime(per["indice_tiempo"])
    per["pernoctes"] = pd.to_numeric(per["pernoctes"], errors="coerce")
    s = (per.dropna(subset=["pernoctes"])
         .groupby("fecha")["pernoctes"].sum()
         .sort_index())
    s = s[s > 0]
    mm12 = s.rolling(12, center=True).mean()
    mm_centrada = mm12.rolling(2).mean().shift(-1)   # media móvil 2x12
    ratio = s / mm_centrada
    indices_est = ratio.groupby(ratio.index.month).median()
    indices_est = indices_est / indices_est.mean()
    desest = s / s.index.month.map(indices_est)

    out["pernoctes"] = {
        "fuente": "EOH, INDEC. Pernoctaciones en hoteles y parahoteles, total país",
        "primer_dato": str(s.index[0].date()),
        "ultimo_dato": str(s.index[-1].date()),
        "n_meses": int(len(s)),
        "maximo": {"fecha": str(s.idxmax().date()), "valor": float(s.max())},
        "minimo": {"fecha": str(s.idxmin().date()), "valor": float(s.min())},
        "indices_estacionales": {MESES[int(m) - 1]: float(v)
                                 for m, v in indices_est.items()},
        "razon_max_min_estacional": float(indices_est.max() / indices_est.min()),
        "enero_2020": float(s.get(pd.Timestamp("2020-01-01"), np.nan)),
        "abril_2020": float(s.get(pd.Timestamp("2020-04-01"), np.nan)),
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    fechas = list(s.index)
    serie_svg("serie-pernoctes.svg", fechas,
              [s.to_numpy(float), mm_centrada.to_numpy(float),
               desest.to_numpy(float)],
              ["Serie original", "Media móvil 12", "Desestacionalizada"],
              "Pernoctaciones mensuales",
              formato=lambda v: f"{v/1e6:.1f} M")

    f2 = list(ipc["fecha"])
    serie_svg("ipc-variaciones.svg", f2,
              [(ipc["var_mensual"] * 100).to_numpy(float),
               (ipc["var_interanual"] * 100 / 12).to_numpy(float)],
              ["Variación mensual (%)", "Interanual / 12"],
              "Variaciones del IPC",
              formato=lambda v: f"{v:.0f}%")

    # ---- Informe ----------------------------------------------------------
    i = out["ipc"]
    print(f"== IPC ({i['primer_dato']} a {i['ultimo_dato']}) ==")
    print(f"  índice último: {i['indice_ultimo']:,.2f}")
    print(f"  var mensual: {i['var_mensual_ultima']:.2%} · interanual: "
          f"{i['var_interanual_ultima']:.2%} · acumulada: "
          f"{i['var_acumulada_anio']:.2%}")
    print("  variación dic-dic por año:", i["variacion_anual_dic_dic"])
    if "cambio_de_base" in out:
        cb = out["cambio_de_base"]
        print(f"\n== Cambio de base ==\n  dic 2023 en base vieja: "
              f"{cb['indice_dic_2023_en_base_vieja']:,.2f} · factor "
              f"{cb['factor']:.6f}")
        print(f"  último índice en base nueva: "
              f"{cb['ejemplo_ultimo_en_base_nueva']:,.2f}")
    d = out["deflactacion"]
    print(f"\n== Deflactación ==")
    print(f"  media nominal 1T2026: ${d['media_nominal_1T2026']:,.0f}")
    print(f"  IPC 1T2026 {d['ipc_promedio_1T2026']:,.2f} · 1T2025 "
          f"{d['ipc_promedio_1T2025']:,.2f} · factor {d['factor']:.4f}")
    print(f"  a precios de 1T2025: ${d['media_a_precios_1T2025']:,.0f}")
    p_ = out["pernoctes"]
    print(f"\n== Pernoctaciones ({p_['primer_dato']} a {p_['ultimo_dato']}, "
          f"{p_['n_meses']} meses) ==")
    print(f"  máximo {p_['maximo']['fecha']}: {p_['maximo']['valor']:,.0f}")
    print(f"  mínimo {p_['minimo']['fecha']}: {p_['minimo']['valor']:,.0f}")
    print(f"  enero 2020: {p_['enero_2020']:,.0f} · abril 2020: "
          f"{p_['abril_2020']:,.0f}")
    print("  índices estacionales:")
    for m, v in p_["indices_estacionales"].items():
        print(f"    {m}  {v:.3f}")
    print(f"  razón max/min: {p_['razon_max_min_estacional']:.2f}")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

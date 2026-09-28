#!/usr/bin/env python
"""
Medidas bivariadas de referencia para el módulo M03.

Calcula con la EPH real todo lo que M03 necesita citar: covarianza, Pearson,
Spearman, la recta de mínimos cuadrados con su R², las medidas de asociación de
una tabla 2x2 (phi, V de Cramér, RR, OR) y una búsqueda de paradoja de Simpson
entre varios cruces candidatos.

El par principal es **ingreso contra horas trabajadas**, que es la relación
bivariada más nítida de la encuesta y la que permite mostrar una recta con
sentido. El contraejemplo es **ingreso contra edad**, donde la relación es débil
y no lineal.

Salida: datos/eph/bivariada-m03.json
        src/figuras/dispersion-ingreso-horas.svg

    python datos/eph/preparar-bivariada-m03.py
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
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "bivariada-m03.json"
FIGURAS = AQUI.parent.parent / "src" / "figuras"


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def describir_par(x, y, nombre) -> dict:
    r, pr = stats.pearsonr(x, y)
    rho, prho = stats.spearmanr(x, y)
    b1, b0, _, _, ee = stats.linregress(x, y)[:5]
    return {
        "nombre": nombre,
        "n": int(len(x)),
        "covarianza": float(np.cov(x, y, ddof=1)[0, 1]),
        "sx": float(x.std(ddof=1)), "sy": float(y.std(ddof=1)),
        "pearson": float(r), "p_pearson": float(pr),
        "spearman": float(rho), "p_spearman": float(prho),
        "r2": float(r ** 2),
        "b0": float(b0), "b1": float(b1), "ee_b1": float(ee),
    }


def dibujar_dispersion(hr: pd.DataFrame, res: dict) -> None:
    """Nube de puntos de horas contra ingreso, con la recta de mínimos cuadrados.

    Se recorta el eje vertical en $4.000.000 para que la nube sea legible; los
    casos por encima se dibujan sobre el borde y el pie de la figura lo aclara.
    """
    W, H = 720, 360
    ML, MR, MT, MB = 62, 18, 22, 52
    x0, x1 = 0, 80          # horas semanales
    y0, y1 = 0, 4_000_000   # pesos

    def px(v):
        return ML + (v - x0) / (x1 - x0) * (W - ML - MR)

    def py(v):
        return H - MB - (v - y0) / (y1 - y0) * (H - MT - MB)

    rng = np.random.default_rng(2026)
    m = hr[(hr["PP3E_TOT"] <= x1)].copy()
    if len(m) > 3500:
        m = m.iloc[rng.choice(len(m), 3500, replace=False)]

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" aria-label="Horas trabajadas e ingreso">']

    for v in range(0, 4_000_001, 1_000_000):
        p.append(f'<line class="guia" x1="{ML}" y1="{py(v):.1f}" '
                 f'x2="{W-MR}" y2="{py(v):.1f}"/>')
        p.append(f'<text class="rotulo-chico" x="{ML-8}" y="{py(v)+4:.1f}" '
                 f'text-anchor="end">${v//1_000_000} M</text>')

    for _, r in m.iterrows():
        yv = min(float(r["P21"]), y1)
        p.append(f'<circle class="punto" cx="{px(r["PP3E_TOT"]):.1f}" '
                 f'cy="{py(yv):.1f}" r="2.4"/>')

    b0, b1 = res["b0"], res["b1"]
    p.append(f'<line class="recta" x1="{px(x0):.1f}" y1="{py(b0):.1f}" '
             f'x2="{px(x1):.1f}" y2="{py(b0 + b1 * x1):.1f}"/>')

    p.append(f'<line class="eje" x1="{ML}" y1="{H-MB}" x2="{W-MR}" y2="{H-MB}"/>')
    for v in range(0, 81, 10):
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{H-MB+18}" '
                 f'text-anchor="middle">{v}</text>')
    p.append(f'<text class="rotulo" x="{(ML+W-MR)/2:.0f}" y="{H-12}" '
             f'text-anchor="middle">Horas trabajadas por semana</text>')
    p.append(f'<text class="rotulo" x="{ML}" y="{MT-4}" '
             f'text-anchor="start">Ingreso de la ocupación principal</text>')
    p.append("</svg>")

    destino = FIGURAS / "dispersion-ingreso-horas.svg"
    destino.write_text("\n".join(p), encoding="utf-8")
    print(f"\n→ {destino}  ({len(m):,} puntos de {len(hr):,})")


def main() -> None:
    ind = leer(
        "usu_individual_T126.txt",
        ["ESTADO", "CAT_OCUP", "NIVEL_ED", "PP07H", "CH04", "CH06",
         "P21", "PP3E_TOT", "PONDERA"],
    )

    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "advertencia": "Cálculos sin ponderar; el diseño real es por conglomerados.",
    }

    # ---- Pares cuantitativos ---------------------------------------------
    # PP3E_TOT = 999 es "no sabe"; se excluye junto con las horas nulas
    oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].copy()
    hr = oc[(oc["PP3E_TOT"] > 0) & (oc["PP3E_TOT"] < 999)].copy()

    out["ingreso_horas"] = describir_par(
        hr["PP3E_TOT"].to_numpy(float), hr["P21"].to_numpy(float),
        "Horas semanales trabajadas vs. ingreso de la ocupación principal")

    out["ingreso_edad"] = describir_par(
        oc["CH06"].to_numpy(float), oc["P21"].to_numpy(float),
        "Edad vs. ingreso de la ocupación principal")

    out["log_ingreso_horas"] = describir_par(
        hr["PP3E_TOT"].to_numpy(float), np.log(hr["P21"].to_numpy(float)),
        "Horas vs. logaritmo del ingreso")

    # Ingreso horario, para mostrar que la relación cambia de signo
    hr["ing_hora"] = hr["P21"] / (hr["PP3E_TOT"] * 4.33)
    out["ingreso_horario_horas"] = describir_par(
        hr["PP3E_TOT"].to_numpy(float), hr["ing_hora"].to_numpy(float),
        "Horas vs. ingreso por hora")

    # ---- Tabla 2x2: medidas de asociación ---------------------------------
    a = ind[
        (ind["ESTADO"] == 1) & (ind["CAT_OCUP"] == 3) & (ind["CH06"] >= 18)
        & (ind["PP07H"].isin([1, 2])) & (ind["NIVEL_ED"].between(1, 6))
    ].copy()
    a["sec"] = np.where(a["NIVEL_ED"].isin([4, 5, 6]), 1, 0)
    a["noreg"] = np.where(a["PP07H"] == 2, 1, 0)

    t = pd.crosstab(a["sec"], a["noreg"]).to_numpy()
    # filas: 0 = sin secundario, 1 = con secundario · cols: 0 = reg, 1 = no reg
    n = t.sum()
    chi2 = stats.chi2_contingency(t, correction=False)[0]
    r1 = t[0, 1] / t[0].sum()      # riesgo de no registro sin secundario
    r2 = t[1, 1] / t[1].sum()      # con secundario
    out["tabla_2x2"] = {
        "tabla": t.tolist(), "n": int(n),
        "riesgo_sin_secundario": float(r1),
        "riesgo_con_secundario": float(r2),
        "diferencia_riesgos": float(r1 - r2),
        "riesgo_relativo": float(r1 / r2),
        "odds_ratio": float((t[0, 1] * t[1, 0]) / (t[0, 0] * t[1, 1])),
        "chi2": float(chi2),
        "phi": float(np.sqrt(chi2 / n)),
        "v_cramer": float(np.sqrt(chi2 / (n * (min(t.shape) - 1)))),
    }

    # ---- Búsqueda de paradoja de Simpson ----------------------------------
    # Tasa de empleo no registrado por sexo, global y por nivel educativo
    simpson = {}
    glob = a.groupby("CH04")["noreg"].agg(["mean", "size"])
    simpson["global"] = {
        "varones": float(glob.loc[1, "mean"]), "n_varones": int(glob.loc[1, "size"]),
        "mujeres": float(glob.loc[2, "mean"]), "n_mujeres": int(glob.loc[2, "size"]),
    }
    por_ed = []
    for ed in sorted(a["NIVEL_ED"].unique()):
        sub = a[a["NIVEL_ED"] == ed]
        g = sub.groupby("CH04")["noreg"].agg(["mean", "size"])
        if 1 in g.index and 2 in g.index:
            por_ed.append({
                "nivel_ed": int(ed),
                "varones": float(g.loc[1, "mean"]), "n_varones": int(g.loc[1, "size"]),
                "mujeres": float(g.loc[2, "mean"]), "n_mujeres": int(g.loc[2, "size"]),
            })
    simpson["por_nivel_educativo"] = por_ed

    dif_glob = simpson["global"]["varones"] - simpson["global"]["mujeres"]
    difs = [e["varones"] - e["mujeres"] for e in por_ed]
    simpson["diferencia_global"] = float(dif_glob)
    simpson["diferencias_por_estrato"] = [float(d) for d in difs]
    simpson["hay_reversion_total"] = bool(
        all(np.sign(d) != np.sign(dif_glob) for d in difs if abs(d) > 0.005)
    )
    out["simpson_sexo_educacion"] = simpson

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    dibujar_dispersion(hr, out["ingreso_horas"])

    # ---- Informe por consola ---------------------------------------------
    for k in ("ingreso_horas", "ingreso_edad", "log_ingreso_horas",
              "ingreso_horario_horas"):
        d = out[k]
        print(f"\n--- {d['nombre']}  (n = {d['n']:,})")
        print(f"  cov      {d['covarianza']:,.1f}")
        print(f"  Pearson  {d['pearson']:.4f}   R² {d['r2']:.4f}")
        print(f"  Spearman {d['spearman']:.4f}")
        print(f"  recta    y = {d['b0']:,.1f} + {d['b1']:,.2f} x")

    print("\n--- Tabla 2x2 (sin secundario / secundario x no registrado)")
    for k, v in out["tabla_2x2"].items():
        print(f"  {k:22} {v}")

    print("\n--- Paradoja de Simpson: tasa de NO registro por sexo")
    g = simpson["global"]
    print(f"  GLOBAL   varones {g['varones']:.4f} (n={g['n_varones']})  "
          f"mujeres {g['mujeres']:.4f} (n={g['n_mujeres']})  "
          f"dif {dif_glob:+.4f}")
    for e in por_ed:
        print(f"  nivel {e['nivel_ed']}  varones {e['varones']:.4f} "
              f"(n={e['n_varones']})  mujeres {e['mujeres']:.4f} "
              f"(n={e['n_mujeres']})  dif {e['varones']-e['mujeres']:+.4f}")
    print(f"  ¿reversión en todos los estratos? "
          f"{simpson['hay_reversion_total']}")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Modelos de regresión de referencia para el módulo M13.

Ajusta sobre la EPH real los modelos que el módulo explica y guarda todo lo que
las entradas necesitan citar:

  1. Regresión simple: ingreso ~ horas.
  2. Regresión múltiple: ingreso ~ horas + edad + sexo + educación (dummies).
  3. La misma, sobre log(ingreso), que es la especificación correcta.
  4. Diagnóstico: residuos, Breusch-Pagan, VIF, distancia de Cook.
  5. Comparación de modelos: R², R² ajustado, AIC, BIC.
  6. Validación cruzada: R² dentro y fuera de la muestra.
  7. Regresión logística: registrado ~ educación + edad + sexo.

Salida: datos/eph/regresion-m13.json
        src/figuras/residuos-regresion.svg

    python datos/eph/preparar-regresion-m13.py
"""

from __future__ import annotations

import os

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "regresion-m13.json"
FIGURAS = AQUI.parent.parent / "src" / "figuras"
SEMILLA = 2026


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def coefs(modelo) -> list[dict]:
    return [
        {"termino": t, "b": float(modelo.params[t]),
         "ee": float(modelo.bse[t]), "t": float(modelo.tvalues[t]),
         "p": float(modelo.pvalues[t]),
         "ic_bajo": float(modelo.conf_int().loc[t, 0]),
         "ic_alto": float(modelo.conf_int().loc[t, 1])}
        for t in modelo.params.index
    ]


def dibujar_residuos(ajustados, residuos) -> None:
    """Residuos contra valores ajustados: el gráfico del embudo."""
    W, H = 720, 340
    ML, MR, MT, MB = 70, 18, 20, 50
    rng = np.random.default_rng(SEMILLA)
    if len(ajustados) > 3000:
        i = rng.choice(len(ajustados), 3000, replace=False)
        ajustados, residuos = ajustados[i], residuos[i]

    x0, x1 = float(np.min(ajustados)), float(np.percentile(ajustados, 99.5))
    y1 = float(np.percentile(np.abs(residuos), 99))
    y0 = -y1

    def px(v):
        return ML + (min(v, x1) - x0) / (x1 - x0) * (W - ML - MR)

    def py(v):
        return H - MB - (np.clip(v, y0, y1) - y0) / (y1 - y0) * (H - MT - MB)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" '
         f'aria-label="Residuos contra valores ajustados">']
    p.append(f'<line class="guia" x1="{ML}" y1="{py(0):.1f}" '
             f'x2="{W-MR}" y2="{py(0):.1f}"/>')
    for a, r in zip(ajustados, residuos):
        p.append(f'<circle class="punto" cx="{px(a):.1f}" cy="{py(r):.1f}" '
                 f'r="2.2"/>')
    p.append(f'<line class="eje" x1="{ML}" y1="{H-MB}" x2="{W-MR}" y2="{H-MB}"/>')
    for frac in (0, 0.25, 0.5, 0.75, 1):
        v = x0 + frac * (x1 - x0)
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{H-MB+18}" '
                 f'text-anchor="middle">${v/1e6:.1f} M</text>')
    for v in (y0, y0 / 2, 0, y1 / 2, y1):
        p.append(f'<text class="rotulo-chico" x="{ML-8}" y="{py(v)+4:.1f}" '
                 f'text-anchor="end">{v/1e6:+.1f} M</text>')
    p.append(f'<text class="rotulo" x="{(ML+W-MR)/2:.0f}" y="{H-10}" '
             f'text-anchor="middle">Ingreso predicho por el modelo</text>')
    p.append(f'<text class="rotulo" x="{ML}" y="{MT-2}" '
             f'text-anchor="start">Residuo</text>')
    p.append("</svg>")
    destino = FIGURAS / "residuos-regresion.svg"
    destino.write_text("\n".join(p), encoding="utf-8")
    print(f"\n→ {destino}")


def main() -> None:
    ind = leer("usu_individual_T126.txt",
               ["ESTADO", "CAT_OCUP", "NIVEL_ED", "PP07H", "CH04", "CH06",
                "P21", "PP3E_TOT", "AGLOMERADO", "REGION", "PP04B_COD",
                "PP04D_COD", "CH07", "CH08"])

    d = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0) & (ind["CH06"] >= 18)
            & (ind["PP3E_TOT"].between(1, 998))
            & (ind["NIVEL_ED"].between(1, 6))].copy()
    d["horas"] = d["PP3E_TOT"].astype(float)
    d["edad"] = d["CH06"].astype(float)
    d["mujer"] = (d["CH04"] == 2).astype(int)
    d["superior"] = d["NIVEL_ED"].isin([5, 6]).astype(int)
    d["secundario"] = d["NIVEL_ED"].isin([3, 4]).astype(int)
    d["ingreso"] = d["P21"].astype(float)
    d["log_ingreso"] = np.log(d["ingreso"])

    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "advertencia": "Sin ponderar; el diseño real es por conglomerados.",
        "n": int(len(d)),
        "semilla": SEMILLA,
    }

    # ---- 1 · Simple --------------------------------------------------------
    m1 = smf.ols("ingreso ~ horas", data=d).fit()
    out["simple"] = {"coeficientes": coefs(m1), "r2": float(m1.rsquared),
                     "ee_residual": float(np.sqrt(m1.mse_resid)),
                     "aic": float(m1.aic), "bic": float(m1.bic)}

    # ---- 2 · Múltiple ------------------------------------------------------
    f2 = "ingreso ~ horas + edad + mujer + secundario + superior"
    m2 = smf.ols(f2, data=d).fit()
    out["multiple"] = {
        "formula": f2, "coeficientes": coefs(m2),
        "r2": float(m2.rsquared), "r2_ajustado": float(m2.rsquared_adj),
        "ee_residual": float(np.sqrt(m2.mse_resid)),
        "F": float(m2.fvalue), "p_F": float(m2.f_pvalue),
        "aic": float(m2.aic), "bic": float(m2.bic),
        "gl_residual": int(m2.df_resid),
    }

    # ---- 3 · Sobre el logaritmo -------------------------------------------
    f3 = "log_ingreso ~ horas + edad + mujer + secundario + superior"
    m3 = smf.ols(f3, data=d).fit()
    out["log"] = {
        "formula": f3, "coeficientes": coefs(m3),
        "r2": float(m3.rsquared), "r2_ajustado": float(m3.rsquared_adj),
        "efectos_porcentuales": {
            t: float((np.exp(m3.params[t]) - 1) * 100)
            for t in m3.params.index if t != "Intercept"
        },
        "aic": float(m3.aic), "bic": float(m3.bic),
    }

    # ---- 4 · Diagnóstico ---------------------------------------------------
    bp = het_breuschpagan(m2.resid, m2.model.exog)
    bp_log = het_breuschpagan(m3.resid, m3.model.exog)
    X = d[["horas", "edad", "mujer", "secundario", "superior"]].assign(const=1)
    vifs = {X.columns[i]: float(variance_inflation_factor(X.values, i))
            for i in range(X.shape[1] - 1)}
    infl = m2.get_influence()
    cook = infl.cooks_distance[0]
    out["diagnostico"] = {
        "breusch_pagan_LM": float(bp[0]), "breusch_pagan_p": float(bp[1]),
        "breusch_pagan_p_log": float(bp_log[1]),
        "asimetria_residuos": float(pd.Series(m2.resid).skew()),
        "asimetria_residuos_log": float(pd.Series(m3.resid).skew()),
        "vif": vifs,
        "cook_max": float(cook.max()),
        "cook_sobre_4n": int((cook > 4 / len(d)).sum()),
        "prop_cook_sobre_4n": float((cook > 4 / len(d)).mean()),
    }

    # ---- 5 · Comparación de modelos ---------------------------------------
    modelos = {
        "solo horas": smf.ols("ingreso ~ horas", data=d).fit(),
        "+ edad": smf.ols("ingreso ~ horas + edad", data=d).fit(),
        "+ sexo": smf.ols("ingreso ~ horas + edad + mujer", data=d).fit(),
        "+ educación": m2,
    }
    rng = np.random.default_rng(SEMILLA)
    d["ruido1"] = rng.normal(size=len(d))
    d["ruido2"] = rng.normal(size=len(d))
    d["ruido3"] = rng.normal(size=len(d))
    modelos["+ 3 variables de ruido"] = smf.ols(
        f2 + " + ruido1 + ruido2 + ruido3", data=d).fit()

    out["comparacion"] = [
        {"modelo": k, "k": int(v.df_model), "r2": float(v.rsquared),
         "r2_ajustado": float(v.rsquared_adj), "aic": float(v.aic),
         "bic": float(v.bic)}
        for k, v in modelos.items()
    ]

    # ---- 6 · Validación cruzada -------------------------------------------
    idx = rng.permutation(len(d))
    corte = int(0.7 * len(d))
    ent, prue = d.iloc[idx[:corte]], d.iloc[idx[corte:]]
    m_ent = smf.ols(f2, data=ent).fit()
    pred = m_ent.predict(prue)
    ss_res = float(((prue["ingreso"] - pred) ** 2).sum())
    ss_tot = float(((prue["ingreso"] - ent["ingreso"].mean()) ** 2).sum())
    out["validacion"] = {
        "n_entrenamiento": int(corte), "n_prueba": int(len(d) - corte),
        "r2_entrenamiento": float(m_ent.rsquared),
        "r2_prueba": float(1 - ss_res / ss_tot),
    }

    # ---- 7 · Logística -----------------------------------------------------
    a = ind[(ind["ESTADO"] == 1) & (ind["CAT_OCUP"] == 3) & (ind["CH06"] >= 18)
            & (ind["PP07H"].isin([1, 2]))
            & (ind["NIVEL_ED"].between(1, 6))].copy()
    a["registrado"] = (a["PP07H"] == 1).astype(int)
    a["edad"] = a["CH06"].astype(float)
    a["mujer"] = (a["CH04"] == 2).astype(int)
    a["superior"] = a["NIVEL_ED"].isin([5, 6]).astype(int)
    a["secundario"] = a["NIVEL_ED"].isin([3, 4]).astype(int)

    fl = "registrado ~ edad + mujer + secundario + superior"
    ml = smf.logit(fl, data=a).fit(disp=0)
    pred_l = (ml.predict(a) > 0.5).astype(int)
    out["logistica"] = {
        "formula": fl, "n": int(len(a)),
        "prop_registrados": float(a["registrado"].mean()),
        "coeficientes": [
            {**c, "odds_ratio": float(np.exp(c["b"])),
             "or_ic_bajo": float(np.exp(c["ic_bajo"])),
             "or_ic_alto": float(np.exp(c["ic_alto"]))}
            for c in coefs(ml)
        ],
        "pseudo_r2_mcfadden": float(ml.prsquared),
        "acierto": float((pred_l == a["registrado"]).mean()),
        "acierto_trivial": float(max(a["registrado"].mean(),
                                     1 - a["registrado"].mean())),
    }

    # ---- 8 · El mismo modelo por análisis discriminante --------------------
    # Tres de las cuatro predictoras son binarias: el caso donde se supone
    # que el discriminante anda mal. Sirve para la entrada del módulo 14.
    from sklearn.discriminant_analysis import (
        LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis)
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from scipy.stats import chi2 as _chi2

    Xd = a[["edad", "mujer", "secundario", "superior"]].to_numpy(float)
    yd = a["registrado"].to_numpy()
    cv = StratifiedKFold(5, shuffle=True, random_state=SEMILLA)
    metodos = {
        "lda": LinearDiscriminantAnalysis(),
        "qda": QuadraticDiscriminantAnalysis(reg_param=0.01),
        "logistica": LogisticRegression(max_iter=3000),
        "logistica_sin_penalizar": LogisticRegression(penalty=None, max_iter=3000),
    }

    def box_m(grupos):
        """M de Box con la corrección y la aproximación chi-cuadrado."""
        gg = len(grupos)
        pp = grupos[0].shape[1]
        ns = np.array([len(x) for x in grupos])
        N = int(ns.sum())
        Ss = [np.cov(x.T) for x in grupos]
        Sp = sum((k - 1) * S for k, S in zip(ns, Ss)) / (N - gg)
        M = ((N - gg) * np.log(np.linalg.det(Sp))
             - sum((k - 1) * np.log(np.linalg.det(S)) for k, S in zip(ns, Ss)))
        corr = ((sum(1 / (k - 1) for k in ns) - 1 / (N - gg))
                * (2 * pp * pp + 3 * pp - 1) / (6 * (pp + 1) * (gg - 1)))
        gl = (gg - 1) * pp * (pp + 1) / 2
        chi = float(M * (1 - corr))
        return {"chi2": chi, "gl": float(gl), "p": float(_chi2.sf(chi, gl))}

    out["discriminante"] = {
        "nota": ("Mismo modelo que la logística, evaluado por validación "
                 "cruzada de 5 pliegues."),
        "n": int(len(a)),
        "predictoras": ["edad", "mujer", "secundario", "superior"],
        "predictoras_binarias": 3,
        "acierto": {k: float(cross_val_score(m, Xd, yd, cv=cv).mean())
                    for k, m in metodos.items()},
        "acierto_trivial": float(max(yd.mean(), 1 - yd.mean())),
        "box_m": box_m([Xd[yd == 0], Xd[yd == 1]]),
    }

    # ---- 9 · Interpretable contra caja negra ------------------------------
    # ¿Cuánto acierto se gana con un método que no se puede leer? Y ¿pesa más
    # cambiar de método o agregar variables? Para la entrada del módulo 14.
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

    BASE_V = ["CH06", "CH04", "NIVEL_ED"]
    CTX_V = [c for c in ["AGLOMERADO", "REGION", "PP04B_COD", "PP04D_COD",
                         "PP3E_TOT", "CH07", "CH08"] if c in a.columns]
    conjuntos = {
        "edad, sexo y educación": BASE_V,
        "+ contexto del puesto": BASE_V + CTX_V,
        "+ ingreso": BASE_V + CTX_V + ["P21"],
    }
    modelos = {
        "logistica": LogisticRegression(max_iter=4000),
        "bosque_aleatorio": RandomForestClassifier(300, random_state=SEMILLA,
                                                   n_jobs=-1),
        "boosting": HistGradientBoostingClassifier(random_state=SEMILLA),
    }
    out["caja_negra"] = {
        "nota": ("Mismo conjunto y misma validación cruzada; cambia el método "
                 "y cambia cuántas variables entran."),
        "n": int(len(a)),
        "acierto_trivial": float(max(yd.mean(), 1 - yd.mean())),
        "conjuntos": [
            {"nombre": nom_c, "variables": len(cols),
             "acierto": {k: float(cross_val_score(
                 m, a[cols].apply(pd.to_numeric, errors="coerce")
                 .fillna(-1).to_numpy(float), yd, cv=cv, n_jobs=-1).mean())
                 for k, m in modelos.items()}}
            for nom_c, cols in conjuntos.items()
        ],
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    def tabla(titulo, cs, extra=""):
        print(f"\n--- {titulo} {extra}")
        print(f"  {'término':14} {'b':>14} {'EE':>12} {'t':>9} {'p':>11}")
        for c in cs:
            print(f"  {c['termino']:14} {c['b']:14,.4f} {c['ee']:12,.4f} "
                  f"{c['t']:9.2f} {c['p']:11.3e}")

    print(f"n = {out['n']:,}")
    tabla("Simple", out["simple"]["coeficientes"],
          f"· R² {out['simple']['r2']:.4f}")
    tabla("Múltiple", out["multiple"]["coeficientes"],
          f"· R² {out['multiple']['r2']:.4f} · ajustado "
          f"{out['multiple']['r2_ajustado']:.4f}")
    print(f"  EE residual: {out['multiple']['ee_residual']:,.0f}")
    tabla("Log", out["log"]["coeficientes"], f"· R² {out['log']['r2']:.4f}")
    print("  efectos porcentuales:",
          {k: round(v, 2) for k, v in out["log"]["efectos_porcentuales"].items()})

    print("\n--- Diagnóstico")
    dg = out["diagnostico"]
    print(f"  Breusch-Pagan p = {dg['breusch_pagan_p']:.3e}  "
          f"(en log: {dg['breusch_pagan_p_log']:.3e})")
    print(f"  asimetría residuos {dg['asimetria_residuos']:.2f}  "
          f"(en log: {dg['asimetria_residuos_log']:.2f})")
    print(f"  VIF: { {k: round(v,3) for k,v in dg['vif'].items()} }")
    print(f"  Cook máx {dg['cook_max']:.4f} · sobre 4/n: "
          f"{dg['cook_sobre_4n']:,} ({dg['prop_cook_sobre_4n']:.1%})")

    print("\n--- Comparación de modelos")
    print(f"  {'modelo':26} {'k':>3} {'R²':>8} {'R² aj':>8} {'AIC':>12} {'BIC':>12}")
    for c in out["comparacion"]:
        print(f"  {c['modelo']:26} {c['k']:3} {c['r2']:8.5f} "
              f"{c['r2_ajustado']:8.5f} {c['aic']:12,.0f} {c['bic']:12,.0f}")

    print("\n--- Validación cruzada")
    vc = out["validacion"]
    print(f"  R² entrenamiento {vc['r2_entrenamiento']:.4f} · "
          f"R² prueba {vc['r2_prueba']:.4f}")

    print("\n--- Logística")
    lg = out["logistica"]
    print(f"  n = {lg['n']:,} · registrados {lg['prop_registrados']:.1%}")
    print(f"  {'término':14} {'b':>10} {'OR':>8} {'IC 95% del OR':>22}")
    for c in lg["coeficientes"]:
        print(f"  {c['termino']:14} {c['b']:10.4f} {c['odds_ratio']:8.3f} "
              f"  [{c['or_ic_bajo']:.3f} ; {c['or_ic_alto']:.3f}]")
    print(f"  pseudo R² McFadden {lg['pseudo_r2_mcfadden']:.4f}")
    print(f"  acierto {lg['acierto']:.1%} vs trivial {lg['acierto_trivial']:.1%}")

    dibujar_residuos(m2.fittedvalues.to_numpy(), m2.resid.to_numpy())
    print(f"→ {SALIDA}")


if __name__ == "__main__":
    main()

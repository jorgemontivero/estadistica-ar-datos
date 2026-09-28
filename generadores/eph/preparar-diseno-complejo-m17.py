#!/usr/bin/env python
"""
Efecto de diseño de la EPH, para el módulo M17.

Todo el sitio viene advirtiendo que la EPH es una encuesta **por conglomerados**
y que las fórmulas simples subestiman sus errores estándar. Este script pone un
número a esa advertencia.

Compara, para varios indicadores:

  · el error estándar bajo el supuesto de **muestreo aleatorio simple**,
  · el error estándar estimado por **bootstrap de conglomerados**, que respeta
    la estructura del diseño remuestreando viviendas completas,

y calcula el **efecto de diseño** (deff) como el cociente de sus varianzas, más
el tamaño de muestra efectivo que implica.

El conglomerado se aproxima con CODUSU, el identificador de vivienda: las
personas de una misma vivienda son la unidad que la encuesta selecciona junta.
Es una aproximación por lo bajo —el diseño real agrupa además por radio censal—
así que el deff verdadero es todavía mayor que el que sale acá.

Salida: datos/eph/diseno-complejo-m17.json

    python datos/eph/preparar-diseno-complejo-m17.py
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

EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
SALIDA = Path(__file__).resolve().parent / "diseno-complejo-m17.json"
SEMILLA = 2026
B = 2000


def main() -> None:
    with zipfile.ZipFile(EPH) as z, z.open("usu_individual_T126.txt") as f:
        ind = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                          usecols=["CODUSU", "AGLOMERADO", "ESTADO",
                                   "CH06", "NIVEL_ED", "P21", "PONDERA",
                                   "PONDIIO", "PONDIH"])

    rng = np.random.default_rng(SEMILLA)
    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, INDEC",
        "semilla": SEMILLA, "B": B,
        "conglomerado": "CODUSU (vivienda)",
        "nota": ("Aproximación por lo bajo: el diseño real agrupa además por "
                 "radio censal, así que el deff verdadero es mayor."),
    }

    def analizar(nombre, d, valor, ponderar=True):
        """Compara EE simple contra EE por bootstrap de conglomerados."""
        d = d.dropna(subset=[valor, "CODUSU"]).copy()
        y = d[valor].to_numpy(float)
        w = d["PONDERA"].to_numpy(float) if ponderar else np.ones(len(d))
        n = len(y)

        est = float((w * y).sum() / w.sum())
        # EE bajo muestreo aleatorio simple, sin ponderar
        ee_simple = float(y.std(ddof=1) / np.sqrt(n))

        # Bootstrap de conglomerados: se remuestrean viviendas completas
        codigos = d["CODUSU"].to_numpy()
        unicos, inverso = np.unique(codigos, return_inverse=True)
        m = len(unicos)
        por_cong = [np.flatnonzero(inverso == i) for i in range(m)]

        reps = np.empty(B)
        for b in range(B):
            elegidos = rng.integers(0, m, m)
            idx = np.concatenate([por_cong[i] for i in elegidos])
            yb, wb = y[idx], w[idx]
            reps[b] = (wb * yb).sum() / wb.sum()
        ee_cong = float(reps.std(ddof=1))

        deff = (ee_cong / ee_simple) ** 2
        return {
            "indicador": nombre, "n": int(n), "conglomerados": int(m),
            "tamano_medio_conglomerado": float(n / m),
            "estimacion": est,
            "ee_simple": ee_simple, "ee_conglomerados": ee_cong,
            "razon_ee": float(ee_cong / ee_simple),
            "deff": float(deff),
            "n_efectivo": float(n / deff),
            "ic95_simple": [est - 1.96 * ee_simple, est + 1.96 * ee_simple],
            "ic95_complejo": [est - 1.96 * ee_cong, est + 1.96 * ee_cong],
        }

    resultados = []

    oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].copy()
    resultados.append(analizar("Ingreso medio de la ocupación principal",
                               oc, "P21"))

    # >= -1 y no >= 0: en la EPH, CH06 = -1 es "menos de un año", y esos
    # casos son justamente menores de 15.
    d2 = ind[ind["CH06"] >= -1].copy()
    d2["es_menor"] = (d2["CH06"] < 15).astype(float)
    resultados.append(analizar("Proporción de menores de 15 años",
                               d2, "es_menor"))

    pea = ind[ind["ESTADO"].isin([1, 2]) & (ind["CH06"] >= 15)].copy()
    pea["desoc"] = (pea["ESTADO"] == 2).astype(float)
    resultados.append(analizar("Tasa de desocupación", pea, "desoc"))

    ad = ind[ind["CH06"] >= 18].copy()
    ad["sec"] = ad["NIVEL_ED"].isin([4, 5, 6]).astype(float)
    resultados.append(analizar("Proporción con secundario completo o más",
                               ad, "sec"))

    # Idem: dejar afuera a los menores de un año sube la edad media.
    d3 = ind[ind["CH06"] >= -1].copy()
    resultados.append(analizar("Edad media", d3, "CH06"))

    out["resultados"] = resultados

    # ------------------------------------------------------------------
    # Declarar el estrato, o no
    #
    # El bootstrap de arriba sortea viviendas de toda la muestra, o sea que
    # ignora la estratificación por aglomerado. Eso es exactamente el error
    # que la entrada llama "declarar el conglomerado y omitir el estrato".
    # Acá se mide cuánto infla: el bootstrap estratificado sortea viviendas
    # DENTRO de cada aglomerado, que es lo que hace el diseño real.
    # ------------------------------------------------------------------

    def ee_bootstrap(d, valor, estratificar):
        y = d[valor].to_numpy(float)
        w = d["PONDERA"].to_numpy(float)
        cod = d["CODUSU"].to_numpy()
        unicos, inverso = np.unique(cod, return_inverse=True)
        por_cong = [np.flatnonzero(inverso == i) for i in range(len(unicos))]

        if estratificar:
            # a qué aglomerado pertenece cada vivienda
            agl_de_cong = d["AGLOMERADO"].to_numpy()[
                [p[0] for p in por_cong]]
            grupos = [np.flatnonzero(agl_de_cong == a)
                      for a in np.unique(agl_de_cong)]
        else:
            grupos = [np.arange(len(unicos))]

        reps = np.empty(B)
        for b in range(B):
            elegidos = np.concatenate(
                [g[rng.integers(0, len(g), len(g))] for g in grupos])
            idx = np.concatenate([por_cong[i] for i in elegidos])
            reps[b] = (w[idx] * y[idx]).sum() / w[idx].sum()
        return float(reps.std(ddof=1))

    estrato = []
    for nombre, d, valor in [
        ("Ingreso medio de la ocupación principal",
         ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)], "P21"),
        ("Edad media", ind[ind["CH06"] >= -1], "CH06"),
    ]:
        d = d.dropna(subset=[valor, "CODUSU"]).copy()
        y = d[valor].to_numpy(float)
        ee_s = float(y.std(ddof=1) / np.sqrt(len(y)))
        sin = ee_bootstrap(d, valor, False)
        con = ee_bootstrap(d, valor, True)
        estrato.append({
            "indicador": nombre, "n": int(len(y)),
            "ee_simple": ee_s,
            "ee_solo_conglomerado": sin, "ee_con_estrato": con,
            "deff_solo_conglomerado": (sin / ee_s) ** 2,
            "deff_con_estrato": (con / ee_s) ** 2,
            "exceso": float(sin / con - 1),
        })
    out["estratificacion"] = estrato

    # ------------------------------------------------------------------
    # Qué cambia si se ponderan las estimaciones puntuales
    # ------------------------------------------------------------------

    punt = []
    for nombre, d, valor in [
        ("Ingreso medio de la ocupación principal",
         ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)], "P21"),
        ("Edad media", ind[ind["CH06"] >= -1], "CH06"),
        ("Proporción con secundario completo o más",
         ind[ind["CH06"] >= 18].assign(
             sec=lambda x: x["NIVEL_ED"].isin([4, 5, 6]).astype(float)),
         "sec"),
    ]:
        d = d.dropna(subset=[valor]).copy()
        y = d[valor].to_numpy(float)
        w = d["PONDERA"].to_numpy(float)
        sin, con = float(y.mean()), float((w * y).sum() / w.sum())
        punt.append({"indicador": nombre,
                     "sin_ponderar": sin, "con_ponderar": con,
                     "dif_relativa": float(con / sin - 1)})
    out["estimacion_puntual"] = punt

    # ------------------------------------------------------------------
    # El ponderador equivocado
    #
    # Para el ingreso de la ocupación principal corresponde PONDIIO, que
    # además reparte el peso de los que no declararon ingreso. Usar PONDERA
    # es el error que lista la entrada.
    # ------------------------------------------------------------------

    oc2 = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].dropna(
        subset=["P21"]).copy()
    y = oc2["P21"].to_numpy(float)
    pesos = {}
    for nom, col in [("sin ponderar", None), ("PONDERA", "PONDERA"),
                     ("PONDIIO", "PONDIIO"), ("PONDIH", "PONDIH")]:
        w = np.ones(len(y)) if col is None else oc2[col].to_numpy(float)
        pesos[nom] = {
            "media": float((w * y).sum() / w.sum()),
            "poblacion": float(w.sum()),
        }
    ref = pesos["PONDIIO"]["media"]
    for nom in pesos:
        pesos[nom]["dif_con_pondiio"] = float(pesos[nom]["media"] / ref - 1)
    out["ponderador"] = pesos

    # ------------------------------------------------------------------
    # Filtrar antes de declarar el diseño
    #
    # Al filtrar primero, el remuestreo sortea sólo entre las viviendas que
    # sobrevivieron al filtro, y pierde la variabilidad de CUÁNTAS caen
    # dentro del subgrupo. Declarando primero, se sortean todas las
    # viviendas y recién después se filtra.
    # ------------------------------------------------------------------

    base = ind[ind["CH06"] >= -1].dropna(subset=["CH06"]).copy()
    base["dentro"] = (base["ESTADO"] == 2) & (base["CH06"] >= 15)
    cod = base["CODUSU"].to_numpy()
    unicos, inverso = np.unique(cod, return_inverse=True)
    por_cong = [np.flatnonzero(inverso == i) for i in range(len(unicos))]
    edad = base["CH06"].to_numpy(float)
    peso = base["PONDERA"].to_numpy(float)
    dentro = base["dentro"].to_numpy()

    # a · declarar primero: se sortean TODAS las viviendas, después se filtra
    reps_a = np.empty(B)
    for b in range(B):
        el = rng.integers(0, len(unicos), len(unicos))
        idx = np.concatenate([por_cong[i] for i in el])
        idx = idx[dentro[idx]]
        reps_a[b] = (peso[idx] * edad[idx]).sum() / peso[idx].sum()

    # b · filtrar primero: sólo se sortean las viviendas del subgrupo
    sub = base[base["dentro"]].copy()
    cods = sub["CODUSU"].to_numpy()
    us, inv = np.unique(cods, return_inverse=True)
    pc = [np.flatnonzero(inv == i) for i in range(len(us))]
    es, ps = sub["CH06"].to_numpy(float), sub["PONDERA"].to_numpy(float)
    reps_b = np.empty(B)
    for b in range(B):
        el = rng.integers(0, len(us), len(us))
        idx = np.concatenate([pc[i] for i in el])
        reps_b[b] = (ps[idx] * es[idx]).sum() / ps[idx].sum()

    out["subpoblacion"] = {
        "indicador": "Edad media de los desocupados",
        "n": int(dentro.sum()),
        "viviendas_totales": int(len(unicos)),
        "viviendas_con_el_subgrupo": int(len(us)),
        "estimacion": float((ps * es).sum() / ps.sum()),
        "ee_declarando_primero": float(reps_a.std(ddof=1)),
        "ee_filtrando_primero": float(reps_b.std(ddof=1)),
        "subestimacion": float(1 - reps_b.std(ddof=1) / reps_a.std(ddof=1)),
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"Bootstrap de conglomerados, B = {B}, semilla {SEMILLA}")
    print(f"Conglomerado: vivienda (CODUSU)\n")
    for r in resultados:
        print(f"--- {r['indicador']}")
        print(f"    n = {r['n']:,} personas en {r['conglomerados']:,} viviendas "
              f"({r['tamano_medio_conglomerado']:.2f} por vivienda)")
        print(f"    estimación      {r['estimacion']:>14,.4f}")
        print(f"    EE simple       {r['ee_simple']:>14,.4f}")
        print(f"    EE conglomerado {r['ee_conglomerados']:>14,.4f}"
              f"   ({r['razon_ee']:.2f} veces)")
        print(f"    deff {r['deff']:.2f}  ·  n efectivo "
              f"{r['n_efectivo']:,.0f} de {r['n']:,}")
        print()

    print("--- declarar el estrato, o no")
    for e in estrato:
        print(f"    {e['indicador']}")
        print(f"      EE simple              {e['ee_simple']:>12,.4f}")
        print(f"      sólo conglomerado      {e['ee_solo_conglomerado']:>12,.4f}"
              f"   deff {e['deff_solo_conglomerado']:.2f}")
        print(f"      conglomerado + estrato {e['ee_con_estrato']:>12,.4f}"
              f"   deff {e['deff_con_estrato']:.2f}")
        print(f"      omitir el estrato infla el EE un "
              f"{e['exceso'] * 100:.1f} %")
    print()

    print("--- ponderar o no la estimación puntual")
    for p in punt:
        print(f"    {p['indicador'][:44]:<44} "
              f"{p['sin_ponderar']:>12,.3f} → {p['con_ponderar']:>12,.3f}"
              f"   ({p['dif_relativa'] * 100:+.2f} %)")
    print()

    print("--- el ponderador, para el ingreso de la ocupación principal")
    for nom, v in pesos.items():
        print(f"    {nom:<14} media {v['media']:>12,.0f}   población "
              f"{v['poblacion']:>14,.0f}   ({v['dif_con_pondiio'] * 100:+.2f} %)")
    print()

    s = out["subpoblacion"]
    print("--- filtrar antes o después de declarar el diseño")
    print(f"    {s['indicador']}: {s['estimacion']:,.2f} años, n = {s['n']:,}")
    print(f"      declarando primero  EE {s['ee_declarando_primero']:.4f}")
    print(f"      filtrando primero   EE {s['ee_filtrando_primero']:.4f}"
          f"   ({s['subestimacion'] * 100:+.1f} %)")
    print()

    print(f"→ {SALIDA}")


if __name__ == "__main__":
    main()

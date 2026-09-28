#!/usr/bin/env python
"""
Tasas e indicadores de referencia para el módulo M05.

Usa dos fuentes públicas, cada una para lo que puede sostener:

  DEIS  · tasas de natalidad y de mortalidad infantil por provincia, ya
          calculadas por el organismo, y defunciones 2023 por provincia,
          sexo y grupo de edad.

  EPH   · estructura por edad y los indicadores del mercado de trabajo, que
          permiten hacer una **estandarización directa completa con una sola
          fuente**: tasa de desocupación por aglomerado, cruda y estandarizada.

La estandarización se ejemplifica con desocupación y no con mortalidad porque
el DEIS no publica la población por provincia y edad: cruzar sus defunciones
con una población de otra fuente daría tasas que no se pueden verificar. La
técnica es idéntica.

Salida: datos/demografia/tasas-m05.json
        src/figuras/piramide-poblacion.svg
        src/figuras/lorenz-ingresos.svg

    python datos/demografia/preparar-tasas-m05.py
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

DEIS = Path(DATOS + r"\Salud\DEIS")
CENSO = Path(DATOS + r"\INDEC\Censos\Censo_2022")
EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "tasas-m05.json"
FIGURAS = AQUI.parent.parent / "src" / "figuras"

CARTO = Path(
    DATOS + r"\INDEC\EPH\04_cartografia_eph"
    r"\aglomerados_eph_json.zip"
)

GRUPOS = [(0, 14), (15, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 120)]
ETIQ = ["0-14", "15-24", "25-34", "35-44", "45-54", "55-64", "65+"]


def nombres_aglomerados() -> dict[int, str]:
    """Nombres oficiales, leídos de la cartografía de la propia EPH."""
    import io as _io
    with zipfile.ZipFile(CARTO) as z:
        nombre = [n for n in z.namelist() if n.endswith(".json")][0]
        g = json.load(_io.TextIOWrapper(z.open(nombre), encoding="utf-8"))
    feats = g["features"] if isinstance(g, dict) and "features" in g else g
    return {int(f["properties"]["eph_codagl"]): f["properties"]["eph_aglome"]
            for f in feats if f["properties"].get("eph_codagl")}


def dibujar_piramide(varones, mujeres) -> None:
    """Pirámide de población: barras horizontales enfrentadas."""
    W, H = 720, 330
    MT, MB, CENTRO = 34, 42, 62
    alto = (H - MT - MB) / len(ETIQ)
    total = sum(varones) + sum(mujeres)
    maxp = max(max(varones), max(mujeres)) / total
    ancho = (W / 2) - CENTRO - 16

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" aria-label="Pirámide de población">']
    for i, g in enumerate(reversed(ETIQ)):
        j = len(ETIQ) - 1 - i
        y = MT + i * alto + 2
        h = alto - 4
        pv, pm = varones[j] / total, mujeres[j] / total
        p.append(f'<rect class="barra" x="{W/2 - CENTRO - pv/maxp*ancho:.1f}" '
                 f'y="{y:.1f}" width="{pv/maxp*ancho:.1f}" height="{h:.1f}"/>')
        p.append(f'<rect class="barra" style="opacity:0.45" '
                 f'x="{W/2 + CENTRO:.1f}" y="{y:.1f}" '
                 f'width="{pm/maxp*ancho:.1f}" height="{h:.1f}"/>')
        p.append(f'<text class="rotulo-chico" x="{W/2:.0f}" y="{y+h/2+4:.1f}" '
                 f'text-anchor="middle">{g}</text>')
        p.append(f'<text class="rotulo-chico" '
                 f'x="{W/2 - CENTRO - pv/maxp*ancho - 6:.1f}" '
                 f'y="{y+h/2+4:.1f}" text-anchor="end">{pv*100:.1f}%</text>')
        p.append(f'<text class="rotulo-chico" '
                 f'x="{W/2 + CENTRO + pm/maxp*ancho + 6:.1f}" '
                 f'y="{y+h/2+4:.1f}" text-anchor="start">{pm*100:.1f}%</text>')
    p.append(f'<text class="rotulo" x="{W/2 - CENTRO - 20:.0f}" y="{MT-12}" '
             f'text-anchor="end">Varones</text>')
    p.append(f'<text class="rotulo" x="{W/2 + CENTRO + 20:.0f}" y="{MT-12}" '
             f'text-anchor="start">Mujeres</text>')
    p.append(f'<text class="rotulo" x="{W/2:.0f}" y="{H-12}" '
             f'text-anchor="middle">Porcentaje de la población total</text>')
    p.append("</svg>")
    destino = FIGURAS / "piramide-poblacion.svg"
    destino.write_text("\n".join(p), encoding="utf-8")
    print(f"\n→ {destino}")


def dibujar_lorenz(pp, qq, gini) -> None:
    """Curva de Lorenz con la diagonal de igualdad."""
    W, H = 460, 400
    ML, MR, MT, MB = 62, 20, 24, 52
    lado_x, lado_y = W - ML - MR, H - MT - MB

    def px(v):
        return ML + v * lado_x

    def py(v):
        return H - MB - v * lado_y

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" aria-label="Curva de Lorenz">']
    for v in (0.25, 0.5, 0.75):
        p.append(f'<line class="guia" x1="{px(0):.1f}" y1="{py(v):.1f}" '
                 f'x2="{px(1):.1f}" y2="{py(v):.1f}"/>')
    p.append(f'<line class="media" x1="{px(0):.1f}" y1="{py(0):.1f}" '
             f'x2="{px(1):.1f}" y2="{py(1):.1f}"/>')
    pts = " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in zip(pp, qq))
    p.append(f'<polyline class="recta" points="{pts}"/>')
    p.append(f'<line class="eje" x1="{px(0):.1f}" y1="{py(0):.1f}" '
             f'x2="{px(1):.1f}" y2="{py(0):.1f}"/>')
    p.append(f'<line class="eje" x1="{px(0):.1f}" y1="{py(0):.1f}" '
             f'x2="{px(0):.1f}" y2="{py(1):.1f}"/>')
    for v in (0, 0.25, 0.5, 0.75, 1):
        p.append(f'<text class="rotulo-chico" x="{px(v):.1f}" y="{py(0)+18:.1f}" '
                 f'text-anchor="middle">{v*100:.0f}%</text>')
        p.append(f'<text class="rotulo-chico" x="{px(0)-8:.1f}" '
                 f'y="{py(v)+4:.1f}" text-anchor="end">{v*100:.0f}%</text>')
    p.append(f'<text class="rotulo" x="{(px(0)+px(1))/2:.0f}" y="{H-12}" '
             f'text-anchor="middle">Población acumulada</text>')
    p.append(f'<text class="rotulo" x="{px(0):.0f}" y="{MT-6}" '
             f'text-anchor="start">Ingreso acumulado</text>')
    p.append(f'<text class="rotulo-media" x="{px(0.58):.0f}" y="{py(0.30):.0f}">'
             f'Gini = {gini:.3f}</text>')
    p.append("</svg>")
    destino = FIGURAS / "lorenz-ingresos.svg"
    destino.write_text("\n".join(p), encoding="utf-8")
    print(f"→ {destino}")


def leer_eph(columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(EPH) as z, z.open("usu_individual_T126.txt") as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def grupo_edad(edad: pd.Series) -> pd.Series:
    # El corte de abajo va en -2 y no en -1 porque `pd.cut` deja abierto el
    # extremo inferior: con -1 el primer intervalo sería (-1, 14] y los
    # CH06 = -1 —«menos de un año» en la EPH— quedarían fuera de todo grupo.
    # Son unos 225.000 chicos ponderados, y sin ellos la pirámide no tiene
    # base y el índice de envejecimiento sale dos puntos más alto.
    cortes = [-2] + [g[1] for g in GRUPOS]
    return pd.cut(edad, cortes, labels=ETIQ)


def main() -> None:
    NOM = nombres_aglomerados()
    out = {"fuentes": {
        "deis": "DEIS, Ministerio de Salud de la Nación",
        "eph": "EPH continua, 1er trimestre de 2026, INDEC",
    }}

    # ---- 1 · Tasas del DEIS, ya calculadas por el organismo ---------------
    tmi = pd.read_csv(DEIS / "datos_abiertos/tasa-de-mortalidad-infantil"
                      / "tasa-mortalidad-infantil-deis-1990-2024.csv",
                      encoding="utf-8-sig")
    nat = pd.read_csv(DEIS / "datos_abiertos/tasa-de-natalidad"
                      / "tasa-natalidad-deis-2000-2024.csv",
                      encoding="utf-8-sig")
    tmi["anio"] = pd.to_datetime(tmi["indice_tiempo"], format="%d-%m-%Y").dt.year
    nat["anio"] = pd.to_datetime(nat["indice_tiempo"], format="%d-%m-%Y").dt.year

    ult_tmi = int(tmi["anio"].max())
    ult_nat = int(nat["anio"].max())
    f_tmi = tmi[tmi["anio"] == ult_tmi].iloc[0]
    f_nat = nat[nat["anio"] == ult_nat].iloc[0]

    provs_tmi = {c.replace("mortalidad_infantil_", ""): float(f_tmi[c])
                 for c in tmi.columns if c.startswith("mortalidad_infantil_")}
    provs_nat = {c.replace("natalidad_", ""): float(f_nat[c])
                 for c in nat.columns if c.startswith("natalidad_")}

    serie_arg = tmi[["anio", "mortalidad_infantil_argentina",
                     "mortalidad_infantil_catamarca"]].dropna()
    out["deis"] = {
        "anio_tmi": ult_tmi, "anio_natalidad": ult_nat,
        "tmi_por_provincia": dict(sorted(provs_tmi.items(),
                                         key=lambda kv: kv[1])),
        "natalidad_por_provincia": dict(sorted(provs_nat.items(),
                                               key=lambda kv: kv[1])),
        "tmi_serie_argentina": {
            int(r.anio): float(r.mortalidad_infantil_argentina)
            for r in serie_arg.itertuples()
            if int(r.anio) in (1990, 2000, 2010, 2020, ult_tmi)
        },
        "tmi_serie_catamarca": {
            int(r.anio): float(r.mortalidad_infantil_catamarca)
            for r in serie_arg.itertuples()
            if int(r.anio) in (1990, 2000, 2010, 2020, ult_tmi)
        },
    }

    # ---- 2 · Defunciones 2023 por edad -------------------------------------
    dd = pd.read_csv(DEIS / "microdatos/defunciones/defweb23.csv",
                     sep=";", encoding="utf-8-sig")
    por_edad = dd.groupby("GRUPEDAD")["CUENTA"].sum()
    total_def = int(dd["CUENTA"].sum())
    out["defunciones_2023"] = {
        "total": total_def,
        "por_grupo_edad": {k: int(v) for k, v in por_edad.items()},
        "prop_65_y_mas": float(
            por_edad[[i for i in por_edad.index
                      if i.startswith(("14_", "15_", "16_", "17_"))]].sum()
            / total_def),
        "menores_de_1": int(por_edad.get("01_Menor de 1 año", 0)),
    }

    # ---- 2b · Absolutos contra tasas por jurisdicción ---------------------
    # Un mapa de conteos es un mapa de población: acá está el número.
    dj = pd.read_csv(
        DEIS / "datos_abiertos"
             / "defunciones-ocurridas-y-registradas-en-la-republica-argentin"
             / "defuncion2024.csv",
        sep=";", encoding="utf-8", low_memory=False)
    porjur = dj.groupby("jurisdiccion_de_residencia_id")["cantidad"].sum()
    pobj = pd.read_csv(
        CENSO / "metadatos" / "Control de universos" / "control_poblacion.csv",
        sep=None, engine="python", encoding="utf-8")
    mj = (pobj.set_index("codigo").join(porjur.rename("defunciones"))
          .dropna(subset=["defunciones"]))
    mj["tasa"] = mj["defunciones"] / mj["total_poblacion"] * 1000
    mj["r_abs"] = mj["defunciones"].rank(ascending=False).astype(int)
    mj["r_tasa"] = mj["tasa"].rank(ascending=False).astype(int)
    out["absolutos_vs_tasas"] = {
        "anio": 2024,
        "jurisdicciones": int(len(mj)),
        "defunciones": int(mj["defunciones"].sum()),
        "poblacion": int(mj["total_poblacion"].sum()),
        "correlacion_poblacion_absolutos": float(
            np.corrcoef(mj["total_poblacion"], mj["defunciones"])[0, 1]),
        "correlacion_poblacion_tasa": float(
            np.corrcoef(mj["total_poblacion"], mj["tasa"])[0, 1]),
        "cambio_medio_de_puesto": float((mj["r_abs"] - mj["r_tasa"]).abs().mean()),
        "top5_por_absolutos": [
            {"jurisdiccion": r.jurisdiccion, "defunciones": int(r.defunciones),
             "tasa": float(r.tasa), "puesto_absolutos": int(r.r_abs),
             "puesto_tasa": int(r.r_tasa)}
            for r in mj.sort_values("defunciones", ascending=False).head(5).itertuples()],
    }

    # ---- 3 · EPH: estructura por edad y mercado de trabajo ----------------
    ind = leer_eph(["AGLOMERADO", "CH04", "CH06", "ESTADO", "P21",
                    "PONDERA", "PONDIIO"])
    ind["grupo"] = grupo_edad(ind["CH06"])

    # Pirámide nacional (total aglomerados)
    pir = (ind.groupby(["grupo", "CH04"], observed=True)["PONDERA"].sum()
           .unstack(fill_value=0))
    total_pob = float(pir.values.sum())
    out["piramide"] = {
        "poblacion_total": total_pob,
        "grupos": ETIQ,
        "varones": [float(pir.loc[g, 1]) for g in ETIQ],
        "mujeres": [float(pir.loc[g, 2]) for g in ETIQ],
        "prop_0_14": float(pir.loc["0-14"].sum() / total_pob),
        "prop_65_mas": float(pir.loc["65+"].sum() / total_pob),
        "indice_envejecimiento": float(
            pir.loc["65+"].sum() / pir.loc["0-14"].sum() * 100),
        "razon_dependencia": float(
            (pir.loc["0-14"].sum() + pir.loc["65+"].sum())
            / pir.loc[["15-24", "25-34", "35-44", "45-54", "55-64"]].values.sum()
            * 100),
    }

    # ---- 4 · Estandarización directa: desocupación por aglomerado ---------
    # PEA = ocupados (1) + desocupados (2); tasa = desocupados / PEA
    pea = ind[ind["ESTADO"].isin([1, 2]) & (ind["CH06"] >= 15)].copy()
    pea["desoc"] = (pea["ESTADO"] == 2).astype(int)

    def tasas(df):
        w = df["PONDERA"]
        return float((w * df["desoc"]).sum() / w.sum())

    # Los dos aglomerados grandes con estructuras etarias más distintas
    grandes = (pea.groupby("AGLOMERADO")["PONDERA"].sum()
               .sort_values(ascending=False).head(12).index)
    cand = pea[pea["AGLOMERADO"].isin(grandes)]

    est = {}
    for ag, sub in cand.groupby("AGLOMERADO"):
        w = sub.groupby("grupo", observed=True)["PONDERA"].sum()
        est[int(ag)] = (w / w.sum()).reindex(ETIQ[1:]).fillna(0).to_dict()

    # Referencia: el total de aglomerados
    ref = (cand.groupby("grupo", observed=True)["PONDERA"].sum())
    ref = (ref / ref.sum()).reindex(ETIQ[1:]).fillna(0)

    detalle = []
    for ag, sub in cand.groupby("AGLOMERADO"):
        especificas, pesos, n = {}, {}, {}
        for g in ETIQ[1:]:
            s = sub[sub["grupo"] == g]
            if len(s) == 0:
                continue
            especificas[g] = tasas(s)
            pesos[g] = float(s["PONDERA"].sum())
            n[g] = int(len(s))
        w_tot = sum(pesos.values())
        cruda = sum(especificas[g] * pesos[g] for g in especificas) / w_tot
        estand = sum(especificas[g] * float(ref[g]) for g in especificas)
        detalle.append({
            "aglomerado": int(ag), "nombre": NOM.get(int(ag), str(ag)),
            "n": int(len(sub)),
            "poblacion": w_tot,
            "tasa_cruda": cruda, "tasa_estandarizada": estand,
            "especificas": especificas,
            "estructura": {g: pesos[g] / w_tot for g in pesos},
        })

    detalle.sort(key=lambda d: d["tasa_cruda"], reverse=True)
    out["estandarizacion"] = {
        "indicador": "Tasa de desocupación abierta, población de 15 años y más",
        "referencia": "Estructura por edad del total de los 12 aglomerados más grandes",
        "estructura_referencia": {g: float(ref[g]) for g in ETIQ[1:]},
        "aglomerados": detalle,
    }

    # Los dos que más cambian de posición al estandarizar
    orden_crudo = sorted(detalle, key=lambda d: -d["tasa_cruda"])
    orden_est = sorted(detalle, key=lambda d: -d["tasa_estandarizada"])
    cambios = []
    for d in detalle:
        p1 = orden_crudo.index(d) + 1
        p2 = orden_est.index(d) + 1
        cambios.append({"aglomerado": d["aglomerado"], "nombre": d["nombre"],
                        "puesto_crudo": p1,
                        "puesto_estandarizado": p2, "cambio": p1 - p2})
    out["estandarizacion"]["cambios_de_posicion"] = sorted(
        cambios, key=lambda c: -abs(c["cambio"]))

    # ---- 5 · Indicadores del mercado de trabajo ----------------------------
    # >= -1 y no >= 0: -1 es «menos de un año», y las tasas de actividad y de
    # empleo se calculan sobre la población total, bebés incluidos.
    pob = ind[ind["CH06"] >= -1]
    w_tot = float(pob["PONDERA"].sum())
    ocup = float(pob.loc[pob["ESTADO"] == 1, "PONDERA"].sum())
    desoc = float(pob.loc[pob["ESTADO"] == 2, "PONDERA"].sum())
    out["mercado_trabajo"] = {
        "poblacion_total": w_tot,
        "ocupados": ocup, "desocupados": desoc,
        "pea": ocup + desoc,
        "tasa_actividad": (ocup + desoc) / w_tot,
        "tasa_empleo": ocup / w_tot,
        "tasa_desocupacion": desoc / (ocup + desoc),
    }

    # ---- 6 · Gini y Lorenz ------------------------------------------------
    # El ponderador del ingreso de la ocupación principal es PONDIIO, no
    # PONDERA: es el que el INDEC calibra para esa variable. La diferencia en
    # el Gini es de 0,004, dentro del intervalo, pero no hay razón para usar
    # el ponderador equivocado.
    oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].copy()
    x = oc["P21"].to_numpy(float)
    w = oc["PONDIIO"].to_numpy(float)
    o = np.argsort(x)
    x, w = x[o], w[o]
    wx = w * x
    # La curva de Lorenz arranca en el origen: sin ese punto, el primer
    # trapecio queda fuera del Gini y los deciles no llegan a sumar 1.
    p = np.r_[0.0, np.cumsum(w) / w.sum()]
    q = np.r_[0.0, np.cumsum(wx) / wx.sum()]
    gini = 1 - np.sum((q[1:] + q[:-1]) * np.diff(p))
    deciles = [float(np.interp(i / 10, p, q)) for i in range(11)]
    grilla = np.linspace(0, 1, 101)
    out["gini"] = {
        "gini": float(gini),
        "n": int(len(x)),
        "curva_p": [float(v) for v in grilla],
        "curva_q": [float(v) for v in np.interp(grilla, p, q)],
        "acumulado_por_decil": deciles,
        "share_decil_1": deciles[1],
        "share_decil_10": 1 - deciles[9],
        "razon_10_1": (1 - deciles[9]) / deciles[1] if deciles[1] > 0 else None,
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    dibujar_piramide(out["piramide"]["varones"], out["piramide"]["mujeres"])
    dibujar_lorenz(out["gini"]["curva_p"], out["gini"]["curva_q"],
                   out["gini"]["gini"])

    # ---- Informe ----------------------------------------------------------
    print(f"== DEIS · tasas {ult_tmi} ==")
    print("  Mortalidad infantil por mil, menores y mayores:")
    tm = list(out["deis"]["tmi_por_provincia"].items())
    for k, v in tm[:3] + [("...", 0)] + tm[-3:]:
        print(f"    {k:26} {v}")
    print(f"  Argentina: {provs_tmi['argentina']} · "
          f"Catamarca: {provs_tmi['catamarca']}")
    print("  Serie Argentina:", out["deis"]["tmi_serie_argentina"])
    print("  Serie Catamarca:", out["deis"]["tmi_serie_catamarca"])

    print(f"\n== Defunciones 2023: {total_def:,} ==")
    print(f"  65 años y más: {out['defunciones_2023']['prop_65_y_mas']:.1%}")
    print(f"  menores de 1 año: {out['defunciones_2023']['menores_de_1']:,}")

    print("\n== Pirámide (EPH, población expandida) ==")
    pr = out["piramide"]
    print(f"  0-14: {pr['prop_0_14']:.1%} · 65+: {pr['prop_65_mas']:.1%}")
    print(f"  índice de envejecimiento: {pr['indice_envejecimiento']:.1f}")
    print(f"  razón de dependencia: {pr['razon_dependencia']:.1f}")

    print("\n== Estandarización directa: desocupación por aglomerado ==")
    print(f"  {'aglomerado':30} {'n':>6} {'cruda':>8} {'estand.':>8} {'dif':>8}")
    for d in detalle:
        print(f"  {d['nombre'][:30]:30} {d['n']:6,} {d['tasa_cruda']:8.4f} "
              f"{d['tasa_estandarizada']:8.4f} "
              f"{(d['tasa_estandarizada']-d['tasa_cruda'])*100:+7.2f}pp")
    print("  cambios de posición:")
    for c in out["estandarizacion"]["cambios_de_posicion"][:4]:
        print(f"    {c['nombre'][:30]:30} puesto {c['puesto_crudo']} -> "
              f"{c['puesto_estandarizado']}")

    print("\n== Mercado de trabajo ==")
    mt = out["mercado_trabajo"]
    print(f"  actividad {mt['tasa_actividad']:.1%} · empleo "
          f"{mt['tasa_empleo']:.1%} · desocupación "
          f"{mt['tasa_desocupacion']:.1%}")

    print("\n== Desigualdad ==")
    g = out["gini"]
    print(f"  Gini {g['gini']:.4f}")
    print(f"  decil 1: {g['share_decil_1']:.2%} · decil 10: "
          f"{g['share_decil_10']:.2%} · razón {g['razon_10_1']:.1f}")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. La regla es que ningún número aparezca acá si
no está también en un CSV, y que ninguna conclusión se escriba más fuerte de
lo que la tabla la sostiene.
"""

from comun import numero_limpio, numero_texto, p_texto


def valor_p(p) -> str:
    texto = p_texto(p)
    return "" if texto == "" else ("p " if texto.startswith("<") else "p = ") + texto


def enumerar(cosas: list[str]) -> str:
    if not cosas:
        return ""
    if len(cosas) == 1:
        return cosas[0]
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def redactar(parametros, supuestos, anova, post_hoc, celdas, casos):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    uf = anova["un_factor"]
    lineas = ["# ANOVA", ""]

    diseno = f"`{parametros['respuesta']} ~ {parametros['factor']}"
    if parametros["factor_2"]:
        diseno += f" * {parametros['factor_2']}"
    diseno += "`"
    lineas.append(f"Diseño: {diseno}. Casos en la base: {casos}; usados: {uf['n']}.")
    if casos - uf["n"] > 0:
        faltan = casos - uf["n"]
        lineas.append(f"Se {'descartó' if faltan == 1 else 'descartaron'} {faltan} "
                      f"{'caso' if faltan == 1 else 'casos'} sin respuesta o sin factor.")
    lineas.append("")

    # Lo primero es la advertencia, si hace falta, porque cambia cómo se lee
    # todo lo que sigue.
    if anova["interaccion_significativa"]:
        interaccion = anova["dos_factores"]["tipo_iii"][2]
        principal = anova["tipos"][1]
        lineas += [
            f"> **La interacción manda.** {interaccion['termino']} da "
            f"F({numero_limpio(interaccion['gl'], 0)}; "
            f"{numero_limpio(anova['dos_factores']['gl_error'], 0)}) = "
            f"{numero_texto(interaccion['f'], 2)}, {valor_p(interaccion['p'])}. Con la "
            f"interacción significativa, el efecto principal de "
            f"{principal['termino']} —{valor_p(principal['p_tipo_iii'])}— es el promedio "
            f"de efectos que apuntan para lados distintos: no describe a ningún grupo. "
            f"Lo que hay que leer son los efectos simples.", ""]

    lineas += ["## Las celdas", ""]
    for c in celdas:
        lineas.append(f"- **{c['celda']}.** n = {c['n']}, media "
                      f"{numero_texto(c['media'], 1)}, DE {numero_texto(c['desvio'], 1)}.")
    lineas.append("")

    lineas += ["## Los supuestos", ""]
    con_veredicto = [f for f in supuestos["normalidad"] if f["normal"] is not None]
    no_normales = [f["celda"] for f in con_veredicto if not f["normal"]]
    if con_veredicto:
        lineas.append(f"- **Normalidad por celda.** Shapiro-Wilk rechaza en "
                      f"{len(no_normales)} de {len(con_veredicto)} celdas"
                      + (f": {enumerar(no_normales)}." if no_normales else "."))
    h = supuestos["homogeneidad"]
    if h:
        lineas.append(f"- **Igualdad de varianzas.** Levene con centro en la mediana: "
                      f"F({numero_limpio(h['gl1'], 0)}; {numero_limpio(h['gl2'], 0)}) = "
                      f"{numero_texto(h['w'], 3)}, {valor_p(h['p'])}.")
    lineas.append("")

    lineas += [f"## ANOVA de un factor: {parametros['factor']}", ""]
    lineas.append(f"F({numero_limpio(uf['gl_entre'], 0)}; "
                  f"{numero_limpio(uf['gl_dentro'], 0)}) = {numero_texto(uf['f'], 3)}, "
                  f"{valor_p(uf['p'])}. η² = {numero_texto(uf['eta_cuadrado'], 3)}, "
                  f"ω² = {numero_texto(uf['omega_cuadrado'], 3)}.")
    lineas.append("")
    lineas.append(f"El factor explica el {numero_texto(uf['eta_cuadrado'] * 100, 1)} % de "
                  f"la variación. El ω², que descuenta el sesgo del η², da "
                  f"{numero_texto(uf['omega_cuadrado'] * 100, 1)} %: esa es la cifra que "
                  f"conviene informar.")
    if anova["welch"]:
        w = anova["welch"]
        lineas += ["", f"Sin suponer varianzas iguales, la versión de Welch da "
                       f"F({numero_limpio(w['gl1'], 0)}; {numero_texto(w['gl2'], 1)}) = "
                       f"{numero_texto(w['f'], 3)}, {valor_p(w['p'])}."]
    lineas.append("")

    if anova["dos_factores"]:
        m = anova["dos_factores"]
        lineas += ["## ANOVA de dos factores", "",
                   "Sumas de cuadrados de tipo III, que no dependen del orden:", ""]
        for f in m["tipo_iii"]:
            lineas.append(f"- **{f['termino']}.** SC = {numero_texto(f['sc'], 2)}, "
                          f"F({numero_limpio(f['gl'], 0)}; "
                          f"{numero_limpio(m['gl_error'], 0)}) = "
                          f"{numero_texto(f['f'], 3)}, {valor_p(f['p'])}.")
        cambian = [t for t in anova["tipos"] if t["cambia_la_conclusion"]]
        lineas += ["", f"Con celdas desbalanceadas el tipo I y el tipo III no dan lo mismo. "
                       f"En este caso "
                   + ("la conclusión de " + enumerar([f"**{t['termino']}**" for t in cambian])
                      + " cambia según cuál se use, y eso hay que declararlo."
                      if cambian else
                      "ninguna conclusión cambia, aunque las sumas de cuadrados difieran; "
                      "está todo en `tipos-de-suma.csv`."), ""]

    if anova["efectos_simples"]:
        lineas += [f"## Efectos simples: {parametros['factor_2']} dentro de cada "
                   f"{parametros['factor']}", ""]
        for e in anova["efectos_simples"]:
            partes = [f"- **{e['nivel']}.** F({numero_limpio(e['gl'], 0)}; "
                      f"{numero_limpio(anova['dos_factores']['gl_error'], 0)}) = "
                      f"{numero_texto(e['f'], 3)}, {valor_p(e['p'])}"]
            if e["diferencia"] is not None:
                partes.append(f"{e['entre']} = {numero_texto(e['diferencia'], 2)} "
                              f"(IC {conf} [{numero_texto(e['inferior'], 2)}; "
                              f"{numero_texto(e['superior'], 2)}])")
            lineas.append(", ".join(partes) + ".")
        con_efecto = [e for e in anova["efectos_simples"] if e["significativo"]]
        if len(con_efecto) > 1 and all(e["diferencia"] is not None for e in con_efecto):
            signos = {e["diferencia"] > 0 for e in con_efecto}
            if len(signos) > 1:
                lineas += ["", "Los efectos simples significativos **apuntan para lados "
                               "distintos**. Por eso el efecto principal da chico: los dos "
                               "se cancelan al promediarlos. Informar solo el promedio "
                               "sería esconder el resultado."]
        lineas.append("")

    if post_hoc["pares"]:
        lineas += [f"## Comparaciones de a pares ({post_hoc['sobre']})", "",
                   f"{post_hoc['cuantas']} comparaciones, con los cuatro métodos. Con Tukey:",
                   ""]
        significativas = [f for f in post_hoc["pares"]
                          if f["metodo"] == "tukey" and f["significativa"]]
        if significativas:
            for f in significativas:
                lineas.append(f"- **{f['a']} vs {f['b']}.** Diferencia "
                              f"{numero_texto(f['diferencia'], 2)} "
                              f"(IC {conf} [{numero_texto(f['inferior'], 2)}; "
                              f"{numero_texto(f['superior'], 2)}]), "
                              f"{valor_p(f['p'])}.")
        else:
            lineas.append("- Ninguna comparación queda significativa.")
        discrepan = [f for f in post_hoc["pares"]
                     if f["metodo"] == "tukey" and f["cambia_entre_correcciones"]]
        if discrepan:
            lineas += ["", f"**Ojo:** en "
                           + enumerar([f"{f['a']} vs {f['b']}" for f in discrepan])
                           + " los cuatro métodos no coinciden. Ahí la conclusión la "
                             "decide la corrección elegida, no los datos."]
        lineas.append("")

    return lineas

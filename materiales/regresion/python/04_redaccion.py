"""Paso 4: el informe en Markdown, listo para pegar.

Cada coeficiente se informa como corresponde: la estimación, su intervalo de
confianza y el valor p. Nunca el p solo, que no dice ni cuánto ni en qué
dirección.

Arriba de todo va lo único que hay que leer antes que nada: si algún resultado
depende de un solo caso.
"""

from comun import decimales_de, numero_limpio, numero_texto, p_texto


def valor_p(p) -> str:
    """«p = 0,032» o «p < 0,001»: con el «< 0,001» no va el signo igual."""
    texto = p_texto(p)
    return f"p {texto}" if texto.startswith("<") else f"p = {texto}"


def enumerar(cosas: list[str]) -> str:
    if len(cosas) == 1:
        return cosas[0]
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def cifra(v, decimales=3) -> str:
    """Los coeficientes de un modelo cambian de escala según la variable: el de
    una edad anda por las décimas y el de un ingreso por las millonésimas. Se
    usan más decimales cuando el número es muy chico."""
    if v is None:
        return ""
    a = abs(v)
    if a != 0 and a < 0.001:
        return numero_texto(v, 9)
    if a != 0 and a < 0.1:
        return numero_texto(v, 5)
    return numero_texto(v, decimales)


def redactar(parametros, modelo, diagnostico, logistica, casos):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    lineas = ["# Regresión", ""]
    formula = f"{parametros['respuesta']} ~ " + " + ".join(parametros["predictores"])
    lineas.append(f"Modelo: `{formula}`. Casos en la base: {casos}; usados en el ajuste: "
                  f"{modelo['n']}.")
    if modelo["descartados"]:
        cuantos = modelo["descartados"]
        lineas.append(f"Se descartó {cuantos} caso al que le faltaba alguna variable del "
                      f"modelo." if cuantos == 1 else
                      f"Se descartaron {cuantos} casos a los que les faltaba alguna variable "
                      f"del modelo.")

    reajuste = diagnostico["reajuste"]
    if reajuste and reajuste["cuantos_cambian"]:
        cuales = enumerate_terminos(reajuste)
        lineas += [
            "",
            f"> **Un solo caso decide parte de este modelo.** Sacar el caso "
            f"{reajuste['caso']} —el de mayor distancia de Cook, "
            f"{numero_texto(reajuste['cook'], 3)}— cambia la conclusión de {cuales}. Un "
            f"resultado que depende de una observación entre {modelo['n']} no es un "
            f"resultado sobre la población: es un resultado sobre esa observación.",
        ]

    lineas += ["", "## El modelo lineal", ""]
    for f in modelo["coeficientes"]:
        if f["termino"] == "(ordenada)":
            continue
        partes = [f"**{f['termino']}.** b = {cifra(f['estimacion'])}",
                  f"IC {conf} [{cifra(f['inferior'])}; {cifra(f['superior'])}]",
                  f"t({numero_limpio(f['gl'], 0)}) = {numero_texto(f['t'], 2)}",
                  valor_p(f["p"])]
        if f["vif"] is not None:
            partes.append(f"VIF = {numero_texto(f['vif'], 2)}")
        lineas.append("- " + ", ".join(partes) + ".")

    lineas += [
        "",
        f"El modelo explica el {numero_texto(modelo['r2'] * 100, 1)} % de la variación "
        f"({numero_texto(modelo['r2_ajustado'] * 100, 1)} % ajustado por la cantidad de "
        f"predictores), con un error estándar residual de "
        f"{cifra(modelo['ee_residual'], 3)}.",
    ]
    if modelo["f"] is not None:
        lineas.append(f"La prueba F del modelo completo da "
                      f"F({numero_limpio(modelo['gl_modelo'], 0)}; "
                      f"{numero_limpio(modelo['gl'], 0)}) = {numero_texto(modelo['f'], 2)}, "
                      f"{valor_p(modelo['p_f'])}.")

    lineas += ["", "## El diagnóstico", ""]
    s = diagnostico["shapiro"]
    if s["p"] is not None:
        lineas.append(f"- **Normalidad de los residuos.** Shapiro-Wilk W = "
                      f"{numero_texto(s['w'], 4)}, {valor_p(s['p'])}.")
    bp = diagnostico["breusch_pagan"]
    if bp:
        lineas.append(f"- **Homocedasticidad.** Breusch-Pagan LM = {numero_texto(bp['lm'], 3)} "
                      f"con {bp['gl']} gl, {valor_p(bp['p'])}.")
    lineas.append(f"- **Independencia.** Durbin-Watson = "
                  f"{numero_texto(diagnostico['durbin_watson'], 3)}. Solo significa algo si las "
                  f"filas tienen un orden.")
    altas = sum(1 for f in diagnostico["influencia"] if f["palanca_alta"])
    grandes = sum(1 for f in diagnostico["influencia"] if f["residuo_grande"])
    lineas.append(f"- **Influencia.** {altas} casos con palanca alta y {grandes} con residuo "
                  f"estandarizado mayor que 2 en valor absoluto.")

    if reajuste:
        lineas += ["", "## Qué pasa sin el caso más influyente", ""]
        lineas.append(f"El caso {reajuste['caso']} tiene una distancia de Cook de "
                      f"{numero_texto(reajuste['cook'], 3)} y una palanca de "
                      f"{numero_texto(reajuste['palanca'], 3)}. Sacándolo:")
        lineas.append("")
        for c in reajuste["comparacion"]:
            if c["termino"] == "(ordenada)":
                continue
            marca = " ←" if c["cambia_la_conclusion"] else ""
            lineas.append(f"- **{c['termino']}.** b pasa de {cifra(c['con_el_caso'])} "
                          f"({valor_p(c['p_con'])}) a {cifra(c['sin_el_caso'])} "
                          f"({valor_p(c['p_sin'])}).{marca}")

    if logistica:
        lineas += ["", "## La regresión logística", ""]
        lineas.append(f"Respuesta: `{logistica['respuesta']}`, con «{logistica['exito']}» como "
                      f"resultado de interés ({logistica['positivos']} casos de "
                      f"{logistica['modelo']['n']}).")
        lineas.append("")
        if not logistica["convergio"]:
            lineas.append("**El ajuste no convergió, así que no hay coeficientes que "
                          "informar.** Lo que sigue es la clasificación, que es la que deja "
                          "ver el problema.")
            lineas.append("")
        for f in logistica["coeficientes"]:
            if f["termino"] == "(ordenada)":
                continue
            lineas.append(f"- **{f['termino']}.** OR = {numero_texto(f['odds_ratio'], 3)} "
                          f"(IC {conf} [{numero_texto(f['or_inferior'], 3)}; "
                          f"{numero_texto(f['or_superior'], 3)}]), {valor_p(f['p'])}.")
        c = logistica["clasificacion"]
        if c["auc"] is not None:
            lineas += [
                "",
                f"Clasificando al corte de 0,5: exactitud "
                f"{numero_texto(c['exactitud'] * 100, 1)} %, sensibilidad "
                f"{numero_texto(c['sensibilidad'] * 100, 1)} %, especificidad "
                f"{numero_texto(c['especificidad'] * 100, 1)} %. El AUC es "
                f"{numero_texto(c['auc'], 3)}.",
                "",
                f"Conviene comparar la exactitud contra la del modelo que siempre contesta la "
                f"clase más frecuente, que acá sería "
                f"{numero_texto(c['exactitud_trivial'] * 100, 1)} %. Una exactitud alta con "
                f"clases desbalanceadas no dice nada por sí sola.",
            ]

    return lineas


def enumerate_terminos(reajuste) -> str:
    cambian = [c["termino"] for c in reajuste["comparacion"] if c["cambia_la_conclusion"]]
    return enumerar([f"**{t}**" for t in cambian])

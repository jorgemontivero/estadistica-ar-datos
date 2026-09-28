"""Paso 3: el informe en Markdown, listo para pegar.

Cada prueba se informa como se debe informar: el estadístico con sus grados de
libertad, el valor p exacto y el tamaño del efecto. Nunca «p < 0,05» a secas,
que no dice ni cuánto ni en qué dirección.

Arriba de todo va lo único que hay que leer antes que nada: en qué
comparaciones el supuesto decidió la conclusión y no solo la prueba.
"""

from comun import decimales_de, numero_limpio, numero_texto, p_texto

SIN_POTENCIA = "sin-potencia"


def valor_p(nombre: str, p) -> str:
    """«p = 0,032» o «p < 0,001»: con el «< 0,001» no va el signo igual."""
    texto = p_texto(p)
    return f"{nombre} {texto}" if texto.startswith("<") else f"{nombre} = {texto}"


def enumerar(cosas: list[str]) -> str:
    """«a», «a y b», «a, b y c»: como se enumera en castellano."""
    if len(cosas) == 1:
        return cosas[0]
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def redactar(supuestos, pruebas, parametros, variables, casos):
    alfa = parametros["alfa"]
    etiqueta_de = {v["nombre"]: v["etiqueta"] for v in variables}
    lineas = ["# Pruebas de hipótesis", ""]
    lineas.append(f"Nivel de significación: α = {numero_texto(alfa, 2)}. "
                  f"Casos en la base: {casos}.")
    lineas += [
        "",
        "Cada prueba se eligió mirando los supuestos, no al revés. Al lado de cada "
        "una está la que se habría corrido con el otro supuesto, para que se vea "
        "cuándo la decisión importó.",
        "",
    ]

    cambian = [f"{f['etiqueta']} según {etiqueta_de.get(f['factor'], f['factor']).lower()}"
               for f in pruebas["pruebas"] if f["cambia_la_conclusion"]]
    if cambian:
        lineas += [
            f"> **Acá el supuesto decide la conclusión.** En {enumerar(cambian)} la prueba que "
            f"corresponde y la alternativa no coinciden en rechazar. En el resto de las "
            f"comparaciones, discutir el supuesto no cambia lo que hay que escribir.",
            "",
        ]

    lineas += ["## Las pruebas", ""]
    for f in pruebas["pruebas"]:
        factor = etiqueta_de.get(f["factor"], f["factor"]).lower()
        partes = [f"**{f['etiqueta']} según {factor}.** {f['prueba']}"]
        if f["estadistico"] is not None and f["simbolo"]:
            gl = ""
            if f["gl"] is not None and f["gl2"] is not None:
                gl = (f"({numero_limpio(f['gl'], 0)}; "
                      f"{numero_limpio(f['gl2'], decimales_de(f['gl2']))})")
            elif f["gl"] is not None:
                gl = f"({numero_limpio(f['gl'], decimales_de(f['gl']))})"
            partes.append(f"{f['simbolo']}{gl} = {numero_limpio(f['estadistico'], 3)}")
        partes.append(valor_p("p", f["p"]))
        if f["efecto"] is not None:
            partes.append(f"{f['medida']} = {numero_texto(f['efecto'], 3)} "
                          f"({f['calificacion']})")
        lineas.append("- " + ", ".join(partes) + ".")
        lineas.append(f"  Se eligió porque {f['motivo']}. "
                      f"La alternativa daba {valor_p('p', f['p_alternativa'])}."
                      if f["p_alternativa"] is not None
                      else f"  Se eligió porque {f['motivo']}.")

    sin_potencia = [f for f in supuestos["supuestos"] if f["veredicto"] == SIN_POTENCIA]
    if sin_potencia:
        cuales = enumerar(sorted({f"{f['etiqueta']} en «{f['grupo']}»" for f in sin_potencia}))
        lineas += [
            "",
            "## Dónde el supuesto no se pudo probar",
            "",
            f"En {cuales} hay menos de quince datos. Con tan pocos, Shapiro-Wilk no tiene "
            f"potencia para detectar nada: que no rechace no es evidencia de normalidad. Ahí "
            f"la decisión hay que tomarla por lo que se sabe de cómo se generan los datos.",
        ]

    return lineas

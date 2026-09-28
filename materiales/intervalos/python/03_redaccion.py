"""Paso 3: el informe en Markdown, listo para pegar.

Un intervalo no se informa como dos números sueltos. Se informa con la
estimación adelante, el nivel de confianza dicho, y la unidad puesta: «media
de 41,0 años (IC 95 % [39,1; 43,0])». Este paso escribe eso, una línea por
variable, para que copiar y pegar sea más rápido que escribirlo a mano y para
que nadie se olvide de aclarar el nivel de confianza.

Las proporciones se informan con el método de Wilson, que es el que hay que
usar salvo que haya una razón para otro. Los otros dos quedan en el CSV.
"""

from comun import decimales_de, intervalo_texto, numero_texto

WILSON = "wilson"


def enumerar(cosas: list[str]) -> str:
    """«a», «a y b», «a, b y c»: como se enumera en castellano."""
    if len(cosas) == 1:
        return cosas[0]
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def confianza_texto(confianza: float) -> str:
    pct = confianza * 100
    decimales = 0 if abs(pct - round(pct)) < 1e-9 else 1
    return numero_texto(pct, decimales) + " %"


def redactar(calculado, diferencias, parametros, casos):
    conf = confianza_texto(parametros["confianza"])
    lineas = ["# Intervalos de confianza", ""]
    lineas.append(f"Nivel de confianza: {conf}. Casos en la base: {casos}.")
    if parametros["poblacion"] is not None:
        lineas.append(f"Población: {numero_texto(parametros['poblacion'], 0)}. Los intervalos "
                      f"de una muestra llevan corrección por población finita.")
    lineas += [
        "",
        f"Un intervalo del {conf} no dice que el parámetro esté ahí adentro con probabilidad "
        f"{conf}. Dice que, si se repitiera el muestreo muchas veces, {conf} de los intervalos "
        f"construidos así contendrían al parámetro. El que tenés en la mano lo contiene o no lo "
        f"contiene.",
        "",
        "## Medias",
        "",
    ]

    for f in calculado["medias"]:
        if f["ambito"] != "Total":
            continue
        d = decimales_de(f["media"])
        lineas.append(f"- **{f['etiqueta']}.** Media de {numero_texto(f['media'], d)} "
                      f"(IC {conf} {intervalo_texto(f['inferior'], f['superior'], d)}), "
                      f"n = {f['n']}.")

    lineas += ["", "## Proporciones", ""]
    for f in calculado["proporciones"]:
        if f["ambito"] != "Total" or f["metodo"] != WILSON:
            continue
        lineas.append(f"- **{f['etiqueta']} — {f['categoria']}.** "
                      f"{numero_texto(f['proporcion'] * 100, 1)} % "
                      f"(IC {conf} [{numero_texto(f['inferior'] * 100, 1)} %; "
                      f"{numero_texto(f['superior'] * 100, 1)} %]), "
                      f"{f['exitos']} de {f['n']}.")

    if diferencias["diferencias"]:
        lineas += ["", "## Diferencias entre grupos", ""]
        # El aviso va una sola vez y arriba, no repetido debajo de cada fila:
        # es la misma advertencia y se lee mejor junta.
        enganosas = [f["etiqueta"] if f["categoria"] == "" else f"{f['etiqueta']} — {f['categoria']}"
                     for f in diferencias["diferencias"] if f["conclusion_distinta"]]
        if enganosas:
            lineas += [
                f"> **Acá no alcanza con mirar los intervalos por separado.** En "
                f"{enumerar(enganosas)} los intervalos de los dos grupos se pisan y, sin "
                f"embargo, el de la diferencia no contiene al cero: mirarlos por separado "
                f"llevaría a la conclusión contraria. Lo que hay que informar es el intervalo "
                f"de la diferencia.",
                "",
            ]
        for f in diferencias["diferencias"]:
            que = f["etiqueta"] if f["categoria"] == "" else f"{f['etiqueta']} — {f['categoria']}"
            if f["que"] == "media":
                d = decimales_de(f["diferencia"])
                valor = numero_texto(f["diferencia"], d)
                rango = intervalo_texto(f["inferior"], f["superior"], d)
            else:
                valor = numero_texto(f["diferencia"] * 100, 1) + " puntos"
                rango = (f"[{numero_texto(f['inferior'] * 100, 1)}; "
                         f"{numero_texto(f['superior'] * 100, 1)}]")
            marca = " ←" if f["conclusion_distinta"] else ""
            lineas.append(f"- **{que}.** {f['grupo_1']} menos {f['grupo_2']}: {valor} "
                          f"(IC {conf} {rango}).{marca}")

        if len(diferencias["niveles"]) > 2:
            lineas += [
                "",
                f"Hay {len(diferencias['niveles'])} grupos, así que cada variable se compara de "
                f"a pares. Cada uno de esos intervalos es del {conf} por separado: mirados en "
                f"conjunto, la confianza es menor. Si la conclusión depende de compararlos "
                f"todos, corresponde un método que lo tenga en cuenta.",
            ]

    return lineas

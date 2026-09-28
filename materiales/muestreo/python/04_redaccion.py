"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. Ningún número aparece acá si no está también en
un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
sostiene.
"""

from comun import decimales_de, numero_texto

QUE = {"media": "la media", "total": "el total", "proporcion": "la proporción"}


def cifra(v, decimales=None) -> str:
    if decimales is None:
        decimales = decimales_de(v)
    return numero_texto(v, decimales)


def porcentaje(v) -> str:
    return numero_texto(v * 100, 1) + " %"


def redactar(parametros, seleccion, ponderadores, estimaciones, por_estrato, cobertura,
             poblacion):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    lineas = ["# Muestreo", ""]
    lineas.append(f"Marco: {cifra(poblacion, 0)} unidades. Muestra: {seleccion['n']} "
                  f"en cada uno de los {len(seleccion['disenos'])} diseños. Semilla "
                  f"{parametros['semilla']}.")
    lineas.append("")

    # El caso que el proyecto quiere mostrar: cuando el intervalo ingenuo se
    # equivoca y el del diseño no.
    fallados = [e for e in estimaciones
                if e["diseno"] == "bietápico" and e["contiene_al_verdadero"]
                and not e["contiene_ingenuo"]]
    if fallados:
        e = fallados[0]
        lineas += [
            f"> **El intervalo que ignora el diseño no contiene al valor verdadero.** Para "
            f"{QUE[e['que']]} de `{e['variable']}`, el valor de la población es "
            f"{cifra(e['verdadero'])}. El intervalo {conf} calculado con el diseño va de "
            f"{cifra(e['inferior'])} a {cifra(e['superior'])} y lo contiene. El que sale de "
            f"tratar la muestra como si fuera aleatoria simple va de "
            f"{cifra(e['inferior_ingenuo'])} a {cifra(e['superior_ingenuo'])} y no. Es la "
            f"misma muestra y la misma estimación: lo único que cambia es la fórmula del "
            f"error estándar.", ""]

    lineas += ["## Cómo se sacó la muestra", ""]
    lineas.append(f"El diseño principal es bietápico: "
                  f"{parametros['conglomerados_por_estrato']} conglomerados por estrato y "
                  f"{parametros['hogares_por_conglomerado']} unidades por conglomerado.")
    lineas.append("")
    for d in seleccion["detalle_bietapico"]:
        lineas.append(f"- **{d['estrato']}.** {d['conglomerados_elegidos']} de "
                      f"{d['conglomerados_en_el_marco']} conglomerados.")
    lineas += ["", f"El sistemático usó un intervalo de "
                   f"{cifra(seleccion['intervalo'], 4)} con arranque en "
                   f"{cifra(seleccion['arranque'], 4)}.", ""]

    p = ponderadores["despues"]
    lineas += ["## Los ponderadores", ""]
    lineas.append(f"Suman {cifra(p['suma'], 0)} sobre una población de "
                  f"{cifra(p['poblacion'], 0)}. Van de {cifra(p['minimo'])} a "
                  f"{cifra(p['maximo'])}, con un coeficiente de variación de "
                  f"{numero_texto(p['coeficiente_de_variacion'], 3)}.")
    lineas.append("")
    lineas.append(f"El efecto de Kish —lo que cuestan los pesos desiguales por sí solos— es "
                  f"{numero_texto(p['deff_de_kish'], 3)}, o sea que la muestra de "
                  f"{p['n']} vale como una de {cifra(p['n_efectivo_de_kish'], 0)} "
                  f"antes de contar lo que cuesta el conglomerado.")
    lineas.append("")

    lineas += ["## Las estimaciones, diseño por diseño", ""]
    variables = []
    for e in estimaciones:
        if e["variable"] not in variables:
            variables.append(e["variable"])
    for variable in variables:
        del_grupo = [e for e in estimaciones if e["variable"] == variable]
        lineas.append(f"**{QUE[del_grupo[0]['que']].capitalize()} de `{variable}`** "
                      f"(verdadera: {cifra(del_grupo[0]['verdadero'])})")
        lineas.append("")
        for e in del_grupo:
            lineas.append(f"- **{e['diseno']}.** {cifra(e['estimacion'])}, IC {conf} "
                          f"[{cifra(e['inferior'])}; {cifra(e['superior'])}], deff "
                          f"{numero_texto(e['deff'], 2)}, n efectivo "
                          f"{cifra(e['n_efectivo'], 0)}.")
        lineas.append("")

    if por_estrato:
        lineas += [f"## La media de `{parametros['variable']}` dentro de cada estrato", ""]
        for e in por_estrato:
            lineas.append(f"- **{e['estrato']}.** n = {e['n']} en "
                          f"{e['unidades_primarias']} conglomerados. "
                          f"{cifra(e['estimacion'])}, IC {conf} [{cifra(e['inferior'])}; "
                          f"{cifra(e['superior'])}]. Verdadera: {cifra(e['verdadero'])}.")
        lineas.append("")

    if cobertura:
        lineas += ["## Cuántas veces le acierta cada intervalo", ""]
        lineas.append(f"Sacando la muestra {cobertura['replicas']} veces y armando los dos "
                      f"intervalos cada vez:")
        lineas += ["",
                   f"- **Con el diseño:** cubre el valor verdadero el "
                   f"{porcentaje(cobertura['cobertura_del_diseno'])} de las veces, contra el "
                   f"{porcentaje(cobertura['nominal'])} que promete.",
                   f"- **Ignorando el diseño:** cubre el "
                   f"{porcentaje(cobertura['cobertura_ingenua'])}.",
                   "",
                   f"El intervalo ingenuo es en promedio "
                   f"{numero_texto(cobertura['ancho_medio_del_diseno'] / cobertura['ancho_medio_ingenuo'], 1)} "
                   f"veces más angosto, y esa es exactamente la precisión que no tiene.", ""]

    return lineas

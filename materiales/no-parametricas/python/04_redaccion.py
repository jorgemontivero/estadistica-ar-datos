"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. Ningún número aparece acá si no está también en
un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
sostiene.
"""

from comun import decimales_de, numero_texto, p_texto

NOMBRES = {
    "mediana": "la mediana", "media": "la media", "ric": "el rango intercuartílico",
    "desvio": "el desvío estándar",
    "diferencia_de_medianas": "la diferencia de medianas",
    "diferencia_de_medias": "la diferencia de medias",
}


def valor_p(p) -> str:
    texto = p_texto(p)
    return "" if texto == "" else ("p " if texto.startswith("<") else "p = ") + texto


def cifra(v) -> str:
    return numero_texto(v, decimales_de(v))


def redactar(parametros, apareadas, independientes, bootstrap, casos):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    lineas = ["# Pruebas no paramétricas", ""]
    lineas.append(f"Casos en la base: {casos}.")
    lineas.append("")

    if apareadas:
        w = apareadas["wilcoxon"]
        s = apareadas["signos"]
        mal = apareadas["como_independientes"]
        if apareadas["cambia_la_conclusion"]:
            lineas += [
                f"> **El apareamiento decide el resultado.** Tomando los datos como lo que "
                f"son —{apareadas['n_pares']} personas medidas dos veces— Wilcoxon da "
                f"{valor_p(w['p'])}. Tratándolos como dos muestras independientes, "
                f"Mann-Whitney da {valor_p(mal['mann_whitney_p'])}. Es la misma tabla: lo "
                f"único que cambia es si se usa la información de quién es quién.", ""]

        lineas += [f"## Antes y después: `{parametros['antes']}` contra "
                   f"`{parametros['despues']}`", ""]
        lineas.append(f"{apareadas['n_pares']} pares completos"
                      + (f", {apareadas['descartados']} descartados por falta de alguna de "
                         f"las dos mediciones." if apareadas["descartados"] else "."))
        lineas.append("")
        if w:
            lineas.append(f"- **Wilcoxon de rangos con signo.** W = {cifra(w['w'])}, "
                          f"z = {numero_texto(w['z'], 3)}, {valor_p(w['p'])}. El "
                          f"desplazamiento estimado (Hodges-Lehmann) es "
                          f"{cifra(w['hodges_lehmann'])}.")
        if s:
            lineas.append(f"- **Prueba de los signos.** Subieron {s['subieron']} y bajaron "
                          f"{s['bajaron']} de {s['n']}, {valor_p(s['p'])}.")
        lineas.append(f"- **Lo mismo sin aparear.** Mann-Whitney "
                      f"{valor_p(mal['mann_whitney_p'])}, t de Welch "
                      f"{valor_p(mal['t_de_welch_p'])}.")
        if w:
            lineas += ["", f"El cambio típico es de {cifra(w['mediana_del_cambio'])} y su "
                           f"desvío es {cifra(w['desvio_del_cambio'])}. Esa es la razón "
                           f"aritmética de todo lo anterior: lo que separa a una persona de "
                           f"otra es mucho más grande que lo que cada una cambió, así que "
                           f"la comparación sin aparear tiene que buscar el efecto adentro "
                           f"de un ruido que la apareada ni ve."]
        lineas.append("")

    u = independientes.get("mann_whitney") if independientes else None
    kw = independientes.get("kruskal") if independientes else None
    if u:
        nombres = independientes["nombres"]
        lineas += [f"## Dos muestras: `{parametros['respuesta']}` por "
                   f"`{parametros['grupo']}`", ""]
        lineas.append(f"- **Mann-Whitney.** U = {cifra(u['u'])}, {valor_p(u['p'])}.")
        lineas.append(f"- **P(X > Y) = "
                      f"{numero_texto(u['probabilidad_de_superar'], 3)}**: esa es la "
                      f"probabilidad de que un caso de «{nombres[0]}» supere a uno de "
                      f"«{nombres[1]}» tomados al azar. Es lo que la prueba contrasta, y no "
                      f"la igualdad de medianas.")
        lineas.append(f"- Medianas: {cifra(u['mediana_a'])} y {cifra(u['mediana_b'])}. "
                      f"Desplazamiento de Hodges-Lehmann: {cifra(u['hodges_lehmann'])}.")
        t = independientes.get("t_de_welch")
        if t:
            lineas.append(f"- **t de Welch**, para comparar: t = {numero_texto(t['t'], 3)}, "
                          f"{valor_p(t['p'])}.")
        lineas.append("")

    if kw:
        lineas += ["## Más de dos muestras", ""]
        lineas.append(f"Kruskal-Wallis: H = {numero_texto(kw['h'], 3)} con {kw['gl']} gl, "
                      f"{valor_p(kw['p'])}. ε² = {numero_texto(kw['epsilon_cuadrado'], 3)}.")
        lineas.append("")
        for g in kw["grupos"]:
            lineas.append(f"- **{g['grupo']}.** n = {g['n']}, mediana "
                          f"{cifra(g['mediana'])}, rango promedio "
                          f"{numero_texto(g['rango_promedio'], 1)}.")
        lineas.append("")

    if bootstrap and bootstrap["intervalos"]:
        lineas += [f"## Intervalos por bootstrap ({bootstrap['replicas']} réplicas)", ""]
        for fila in bootstrap["intervalos"]:
            nombre = NOMBRES.get(fila["estadistico"], fila["estadistico"])
            partes = [f"- **{nombre.capitalize()}**: {cifra(fila['observado'])}",
                      f"percentil [{cifra(fila['percentil_inferior'])}; "
                      f"{cifra(fila['percentil_superior'])}]"]
            if fila["bca_inferior"] is not None:
                partes.append(f"BCa [{cifra(fila['bca_inferior'])}; "
                              f"{cifra(fila['bca_superior'])}]")
            lineas.append(", ".join(partes) + ".")
        lineas.append("")
        p = bootstrap["permutacion"]
        if p:
            lineas.append(f"Prueba de permutación sobre la diferencia de medianas: "
                          f"observada {cifra(p['observada'])}, {valor_p(p['p'])} con "
                          f"{p['replicas']} reordenamientos.")
            lineas.append("")

    return lineas

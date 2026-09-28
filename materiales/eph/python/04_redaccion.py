"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. Ningún número aparece acá si no está también en
un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
sostiene.
"""

from comun import numero_texto, pesos_texto, porcentaje


def por_nombre(filas, clave, valor):
    for f in filas:
        if f.get(clave) == valor:
            return f
    return None


def redactar(parametros, base, tasas, identidad_, contraste_, ingresos, deciles,
             ingresos_grupo, informal, avisos):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    periodo = base["periodo"] or "el período del archivo"
    lineas = [f"# Mercado de trabajo, {periodo}", ""]

    lineas.append(
        f"Fuente: `{parametros['archivo']}`, {base['columnas_del_archivo']} columnas. "
        f"Quedaron {numero_texto(len(base['registros']), 0)} personas en "
        f"{numero_texto(base['hogares'], 0)} hogares de {base['aglomerados']} "
        f"aglomerados, que representan a "
        f"{numero_texto(base['peso_total'], 0)} habitantes.")
    lineas.append("")

    # Lo primero que hay que leer, porque es lo que se hace mal.
    correcto = contraste_[0] if contraste_ else None
    los_dos = por_nombre(
        contraste_, "caso", "Con el ponderador general y los que no declaran adentro")
    solo_peso = por_nombre(contraste_, "caso", "Con el ponderador general")
    if correcto and los_dos and solo_peso:
        lineas += [
            f"> **El mismo ingreso medio, tres veces.** Con "
            f"`{correcto['ponderador']}` y sacando a los que no declaran da "
            f"{pesos_texto(correcto['media'])}. Cambiando nada más que el ponderador da "
            f"{pesos_texto(solo_peso['media'])}, un "
            f"{porcentaje(abs(solo_peso['diferencia_relativa']), 1)} menos. Cambiando "
            f"además el filtro —dejando adentro al −9, que en la EPH quiere decir «no "
            f"responde» y no «menos nueve pesos»— da {pesos_texto(los_dos['media'])}, un "
            f"{porcentaje(abs(los_dos['diferencia_relativa']), 1)} menos. Son los mismos "
            f"datos y las mismas personas.", ""]

    # ------------------------------------------------------------- las tasas
    lineas += ["## Las cuatro tasas", ""]
    lineas.append("Cada una tiene su propio denominador, y no es un detalle de "
                  "presentación: la desocupación se calcula sobre la población "
                  "económicamente activa y no sobre la población.")
    lineas.append("")
    for t in tasas:
        lineas.append(
            f"- **Tasa de {t['tasa']}:** {porcentaje(t['valor'], 2)}, IC {conf} "
            f"[{porcentaje(t['inferior'], 2)}; {porcentaje(t['superior'], 2)}]. "
            f"{t['numerador']} sobre {t['denominador'].lower()}, "
            f"{numero_texto(t['n_denominador'], 0)} casos.")
    lineas.append("")

    if identidad_:
        lineas.append(
            f"Las tres primeras tienen que cerrar entre sí: empleo = actividad × (1 − "
            f"desocupación). Da "
            f"{porcentaje(identidad_['empleo_por_la_identidad'], 4)} contra el "
            f"{porcentaje(identidad_['empleo_observado'], 4)} calculado aparte. Es la "
            f"única comprobación que no depende de tener razón sobre nada más.")
        lineas.append("")

    sin_ponderar = [t for t in tasas if t["sin_ponderar"] is not None]
    if sin_ponderar:
        peor = max(sin_ponderar, key=lambda t: abs(t["diferencia_con_la_ponderada"]))
        lineas.append(
            f"Contar casos en vez de ponderar cambia las tasas. Donde más cambia es en "
            f"la de {peor['tasa']}: {porcentaje(peor['sin_ponderar'], 2)} sin ponderar "
            f"contra {porcentaje(peor['valor'], 2)} ponderando. La EPH no es una muestra "
            f"autoponderada, y un caso de un aglomerado chico no vale lo mismo que uno "
            f"del conurbano.")
        lineas.append("")

    con_deff = [t for t in tasas if t["deff"]]
    if con_deff:
        peor = max(con_deff, key=lambda t: t["deff"])
        lineas.append(
            f"El efecto de diseño más alto es el de la tasa de {peor['tasa']}: "
            f"{numero_texto(peor['deff'], 2)}. Los "
            f"{numero_texto(peor['n_denominador'], 0)} casos de su denominador valen como "
            f"{numero_texto(peor['n_efectivo'], 0)}. Y está calculado con el hogar como "
            f"unidad primaria, que es lo más fino que trae el archivo público: el "
            f"conglomerado de verdad es el radio censal, así que el efecto real es "
            f"todavía mayor y estos intervalos son una cota optimista.")
        lineas.append("")

    # ---------------------------------------------------------- los ingresos
    lineas += ["## Los ingresos de la ocupación principal", ""]
    valor = {f["estadistico"]: f["valor"] for f in ingresos}
    if valor:
        lineas.append(
            f"Sobre {numero_texto(valor['casos'], 0)} ocupados con ingreso declarado, "
            f"que representan a {numero_texto(valor['población representada'], 0)} "
            f"personas. La media es {pesos_texto(valor['media'])}, IC {conf} "
            f"[{pesos_texto(valor['límite inferior'])}; {pesos_texto(valor['límite superior'])}]. "
            f"La mediana es {pesos_texto(valor['mediana'])}.")
        lineas.append("")
        lineas.append(
            f"El décimo decil gana "
            f"{numero_texto(valor['razón entre el décimo y el primer decil'], 1)} veces "
            f"lo que el primero. El primer decil corta en "
            f"{pesos_texto(valor['primer decil'])} y el noveno en "
            f"{pesos_texto(valor['noveno decil'])}.")
        lineas.append("")

    if deciles:
        lineas.append("| Decil | Corte superior | Ingreso medio | Participación |")
        lineas.append("| --- | --- | --- | --- |")
        for d in deciles:
            corte = pesos_texto(d["corte_superior"]) if d["corte_superior"] is not None else "—"
            lineas.append(f"| {d['decil']} | {corte} | {pesos_texto(d['ingreso_medio'])} | "
                          f"{porcentaje(d['participacion'], 1)} |")
        lineas.append("")

    # ------------------------------------------------- el contraste, en tabla
    if contraste_:
        lineas += ["## El mismo promedio, de cinco maneras", ""]
        lineas.append("| Cómo se calculó | Ponderador | El −9 | El 0 | Media | "
                      "Diferencia |")
        lineas.append("| --- | --- | --- | --- | --- | --- |")
        for i, c in enumerate(contraste_):
            # La primera fila es la referencia. Que la segunda diga «la misma»
            # es el hallazgo, así que se escribe con todas las letras en vez de
            # dejar un guion que se confunda con el de arriba.
            if i == 0:
                dif = "referencia"
            elif abs(c["diferencia"]) < 1e-9:
                dif = "**exactamente la misma**"
            else:
                dif = porcentaje(c["diferencia_relativa"], 1)
            lineas.append(
                f"| {c['caso']} | `{c['ponderador']}` | "
                f"{c['que_hace_con_el_menos_nueve']} | {c['que_hace_con_el_cero']} | "
                f"{pesos_texto(c['media'])} | {dif} |")
        lineas.append("")
        lineas.append(
            "Las dos primeras filas dan lo mismo, y eso es lo importante: con el "
            "ponderador de ingreso, el −9 ya está sacado, porque el INDEC le pone el "
            "peso en cero. El filtro que nunca se escribió no hace falta… hasta que el "
            "ponderador no está.")
        lineas.append("")

    # ------------------------------------------------------- por grupo
    sexos = [f for f in ingresos_grupo if f["corte"] == "Sexo"]
    if len(sexos) == 2:
        varon = por_nombre(sexos, "grupo", "Varón")
        mujer = por_nombre(sexos, "grupo", "Mujer")
        if varon and mujer:
            lineas += ["### Por sexo", ""]
            lineas.append(
                f"Los varones ocupados declaran en promedio {pesos_texto(varon['media'])} y "
                f"las mujeres {pesos_texto(mujer['media'])}: ellas ganan el "
                f"{porcentaje(mujer['media'] / varon['media'], 1)} de lo que ganan "
                f"ellos. Es una diferencia de ingresos entre ocupados, no una diferencia "
                f"de salario a igual tarea: la EPH no alcanza para lo segundo.")
            lineas.append("")

    # ---------------------------------------------------------- informalidad
    total_informal = next((f for f in informal if f["corte"] == "Total"), None)
    if total_informal:
        lineas += ["## Informalidad", ""]
        lineas.append(
            f"El {porcentaje(total_informal['tasa'], 2)} de los asalariados no tiene "
            f"descuento jubilatorio, IC {conf} "
            f"[{porcentaje(total_informal['inferior'], 2)}; "
            f"{porcentaje(total_informal['superior'], 2)}]. Son "
            f"{numero_texto(total_informal['sin_descuento'], 0)} personas sobre "
            f"{numero_texto(total_informal['asalariados'], 0)} asalariados.")
        lineas.append("")
        otros = [f for f in informal if f["corte"] != "Total"]
        if otros:
            peor = max(otros, key=lambda f: f["tasa"])
            mejor = min(otros, key=lambda f: f["tasa"])
            lineas.append(
                f"El grupo con más informalidad es «{peor['grupo']}» "
                f"({peor['corte'].lower()}), con {porcentaje(peor['tasa'], 1)}; el que "
                f"menos, «{mejor['grupo']}» ({mejor['corte'].lower()}), con "
                f"{porcentaje(mejor['tasa'], 1)}.")
            lineas.append("")

    # --------------------------------------------------------------- avisos
    if avisos:
        lineas += ["## Qué revisar antes de publicar esto", ""]
        for a in avisos:
            lineas.append(f"- **{a['donde'].capitalize()}.** {a['aviso']}")
        lineas.append("")

    return lineas

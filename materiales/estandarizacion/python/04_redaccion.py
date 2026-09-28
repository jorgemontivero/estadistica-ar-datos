"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. Ningún número aparece acá si no está también en
un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
sostiene.
"""

from comun import numero_texto, porcentaje, tasa_texto


def redactar(parametros, tasas, indirectas, referencia, sensibles, niveles,
             comparaciones, avisos, grupos):
    conf = numero_texto(parametros["confianza"] * 100, 0) + " %"
    por = numero_texto(parametros["multiplicador"], 0)
    lineas = ["# Tasas estandarizadas por edad", ""]

    casos = sum(f["casos"] for f in tasas)
    expuestos = sum(f["expuestos"] for f in tasas)
    lineas.append(
        f"{len(tasas)} poblaciones, {len(grupos)} grupos de edad, "
        f"{numero_texto(casos, 0)} casos sobre {numero_texto(expuestos, 0)} personas. "
        f"Estándar: «{parametros['estandar']}». Las tasas van por {por}.")
    lineas.append("")

    # Lo primero que hay que leer: el vuelco.
    vuelco = max(tasas, key=lambda f: abs(f["cambio_de_rango"]))
    if abs(vuelco["cambio_de_rango"]) >= 3:
        lineas += [
            f"> **La tasa cruda y la ajustada no ordenan igual.** «{vuelco['poblacion']}» "
            f"está en el puesto {vuelco['rango_crudo']} de {len(tasas)} por su tasa cruda "
            f"—{tasa_texto(vuelco['cruda'])} por {por}— y en el "
            f"{vuelco['rango_estandarizado']} por la ajustada, que es "
            f"{tasa_texto(vuelco['estandarizada'])}. No cambió ningún dato: cambió la "
            f"estructura de edad con la que se los pesa. El "
            f"{porcentaje(vuelco['proporcion_en_el_grupo_mayor'])} de su población está en "
            f"el grupo de «{grupos[-1]}», contra el "
            f"{porcentaje(sum(f['proporcion_en_el_grupo_mayor'] for f in tasas) / len(tasas))} "
            f"del promedio de las poblaciones.", ""]

    # ------------------------------------------------------------ el ranking
    lineas += ["## Las tasas ajustadas, de mayor a menor", ""]
    lineas.append(f"| Población | Cruda | Ajustada | IC {conf} | Puesto crudo → ajustado |")
    lineas.append("| --- | --- | --- | --- | --- |")
    for f in tasas:
        flecha = f"{f['rango_crudo']} → {f['rango_estandarizado']}"
        if f["cambio_de_rango"] != 0:
            flecha += f" ({f['cambio_de_rango']:+d})"
        lineas.append(
            f"| {f['poblacion']} | {tasa_texto(f['cruda'])} | "
            f"{tasa_texto(f['estandarizada'])} | "
            f"{tasa_texto(f['estandarizada_inferior'])} a "
            f"{tasa_texto(f['estandarizada_superior'])} | {flecha} |")
    lineas.append("")

    mas_alta, mas_baja = tasas[0], tasas[-1]
    lineas.append(
        f"De {tasa_texto(mas_alta['estandarizada'])} en «{mas_alta['poblacion']}» a "
        f"{tasa_texto(mas_baja['estandarizada'])} en «{mas_baja['poblacion']}»: "
        f"{numero_texto(mas_alta['estandarizada'] / mas_baja['estandarizada'], 2)} veces. "
        f"Con las tasas crudas la distancia entre esas dos es de "
        f"{numero_texto(mas_alta['cruda'] / mas_baja['cruda'], 2)} veces.")
    lineas.append("")

    # ------------------------------------------------------ el estándar
    if sensibles or niveles:
        lineas += ["## Cuánto depende del estándar elegido", ""]
        peor = max(niveles, key=lambda f: f["razon_entre_niveles"] or 0)
        lineas.append(
            f"Mucho, en el nivel. La tasa de «{peor['poblacion']}» va de "
            f"{tasa_texto(peor['menor'])} con el estándar «{peor['estandar_del_menor']}» a "
            f"{tasa_texto(peor['mayor'])} con «{peor['estandar_del_mayor']}»: "
            f"{numero_texto(peor['razon_entre_niveles'], 2)} veces, con los mismos datos y "
            f"el mismo método. **Una tasa ajustada sin el nombre de su estándar al lado no "
            f"quiere decir nada.**")
        lineas.append("")
        if sensibles:
            pisados = sum(1 for f in sensibles if f["se_pisan_con_los_dos"])
            lineas.append(
                f"Y algo, en el orden. Se dan vuelta {len(sensibles)} pares de "
                f"poblaciones según con qué estándar se los mire, y en {pisados} de esos "
                f"{len(sensibles)} los intervalos se pisan con los dos estándares: ahí el "
                f"estándar decide un orden que no estaba decidido, y no se pierde nada. "
                f"Los otros {len(sensibles) - pisados} son el caso incómodo: con uno de "
                f"los dos estándares los intervalos **no** se pisan, así que la diferencia "
                f"parecía establecida y con el otro estándar se da vuelta. Están par por "
                f"par en `sensibilidad.csv`.")
        else:
            lineas.append(
                "Y nada, en el orden: con estos datos ningún par se da vuelta al cambiar "
                "de estándar. No es una garantía —puede pasar, y pasa cuando las curvas de "
                "tasas por edad se cruzan— pero acá no pasó.")
        lineas.append("")

    # ------------------------------------------------------------ la indirecta
    lineas += ["## La razón estandarizada", ""]
    lineas.append(
        f"Referencia: {referencia['nombre']}, con una tasa cruda de "
        f"{tasa_texto(referencia['cruda'] * parametros['multiplicador'])} por {por}. La "
        f"razón compara los casos observados con los que habría si esta población tuviera "
        f"las tasas de la referencia a cada edad.")
    lineas.append("")
    distintas = [f for f in indirectas if f["distinta_de_uno"]]
    lineas.append(
        f"En {len(distintas)} de {len(indirectas)} poblaciones el intervalo de la razón no "
        f"contiene al uno. En las otras {len(indirectas) - len(distintas)}, la mortalidad "
        f"no se distingue de la que la estructura de edad hacía esperar.")
    lineas.append("")
    if indirectas:
        arriba, abajo = indirectas[0], indirectas[-1]
        lineas.append(
            f"La más alta es «{arriba['poblacion']}», con "
            f"{numero_texto(arriba['razon'], 3)} "
            f"[{numero_texto(arriba['razon_inferior'], 3)}; "
            f"{numero_texto(arriba['razon_superior'], 3)}]: "
            f"{numero_texto(arriba['observados'], 0)} casos contra "
            f"{numero_texto(arriba['esperados'], 0)} esperados. La más baja es "
            f"«{abajo['poblacion']}», con {numero_texto(abajo['razon'], 3)}.")
        lineas.append("")

    # ------------------------------------------------------- las comparaciones
    if comparaciones:
        lineas += ["## Los pares comparados", ""]
        for c in comparaciones:
            lineas.append(f"### {c['poblacion_a']} contra {c['poblacion_b']}")
            lineas.append("")
            lineas.append(
                f"Tasas crudas: {tasa_texto(c['cruda_a'])} y {tasa_texto(c['cruda_b'])}, "
                f"una diferencia de {tasa_texto(c['diferencia_cruda'])}. "
                f"Ajustadas: {tasa_texto(c['estandarizada_a'])} y "
                f"{tasa_texto(c['estandarizada_b'])}"
                + (", que van para el lado contrario." if c["se_dan_vuelta"]
                   else ", que van para el mismo lado."))
            lineas.append("")
            lineas.append(
                f"De esa diferencia cruda, {tasa_texto(c['efecto_estructura'])} "
                f"({porcentaje(c['parte_estructura'])}) es **estructura** —las dos "
                f"poblaciones tienen edades distintas— y "
                f"{tasa_texto(c['efecto_tasas'])} es **riesgo**: lo que cambia a cada "
                f"edad. Los dos sumandos suman exactamente la diferencia, y ese es el "
                f"control de la cuenta.")
            lineas.append("")
            if c["razon"] is not None:
                lineas.append(
                    f"La razón entre las dos tasas ajustadas es "
                    f"{numero_texto(c['razon'], 3)}, IC {conf} "
                    f"[{numero_texto(c['razon_inferior'], 3)}; "
                    f"{numero_texto(c['razon_superior'], 3)}]"
                    + ("." if c["la_razon_excluye_al_uno"]
                       else ", que contiene al uno: la diferencia no está establecida."))
                lineas.append("")

    # --------------------------------------------------------------- avisos
    if avisos:
        lineas += ["## Qué revisar antes de publicar esto", ""]
        for a in avisos:
            lineas.append(f"- **{a['donde'].capitalize()}.** {a['aviso']}")
        lineas.append("")

    return lineas

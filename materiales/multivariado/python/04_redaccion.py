"""Paso 4: el informe, escrito en castellano.

Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
calculó, redactado para pegar. Ningún número aparece acá si no está también en
un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
sostiene.
"""

import math

from comun import numero_texto, porcentaje, p_texto


def cifra(v, decimales=3):
    return numero_texto(v, decimales)


def redactar(parametros, unidades, columnas, filas_componentes, filas_cargas,
             filas_contraste, filas_siluetas, filas_grupos, nulo, ca, filas_ejes,
             filas_puntos, avisos, columnas_tabla):
    lineas = ["# Análisis multivariado", ""]
    lineas.append(f"{len(unidades)} unidades y {len(columnas)} variables. "
                  f"Enlace: «{parametros['enlace']}», "
                  f"{parametros['conglomerados']} conglomerados.")
    lineas.append("")

    tipificada = filas_contraste[0]
    cruda = filas_contraste[1]
    lineas += [
        f"> **Tipificar o no tipificar no es un detalle del preprocesamiento: es el "
        f"análisis.** Sin tipificar, el primer componente explica el "
        f"{porcentaje(cruda['proporcion_1'])} de la varianza y su correlación con "
        f"«{cruda['variable_mas_pegada']}» es de {cifra(cruda['correlacion_con_esa'])}: "
        f"no resume nada, es esa variable con otro nombre. Tipificando, el primero "
        f"explica el {porcentaje(tipificada['proporcion_1'])} y hacen falta "
        f"{tipificada['variables_hasta_el_90']} componentes para llegar al 90 %.", ""]

    # ------------------------------------------------------- los componentes
    lineas += ["## Los componentes", ""]
    lineas.append("| Componente | Autovalor | Explica | Acumulado |")
    lineas.append("| --- | --- | --- | --- |")
    for f in filas_componentes:
        lineas.append(f"| {f['componente']} | {cifra(f['autovalor'])} | "
                      f"{porcentaje(f['proporcion'])} | {porcentaje(f['acumulado'])} |")
    lineas.append("")

    cuantos = sum(1 for f in filas_componentes if f["supera_el_promedio"])
    lineas.append(
        f"Con el criterio de quedarse con los que superan el autovalor promedio —que "
        f"con datos tipificados es uno— quedan {cuantos}. Es una regla, no un "
        f"resultado: no hay nada en los datos que diga que {cuantos} es el número.")
    lineas.append("")

    # Las cargas del primer componente, ordenadas.
    primeras = sorted(filas_cargas, key=lambda f: -abs(f.get("componente_1") or 0.0))
    lineas.append("Lo que pesa en el primer componente, de mayor a menor:")
    lineas.append("")
    for f in primeras:
        carga = f.get("componente_1")
        if carga is None:
            continue
        lineas.append(f"- **{f['variable']}:** {cifra(carga)}")
    lineas.append("")

    flojas = [f for f in filas_cargas if f["representada"] < 0.5]
    if flojas:
        cuales = ", ".join(f"«{f['variable']}»" for f in flojas)
        lineas.append(
            f"Con los componentes elegidos, {cuales} queda(n) representada(s) a menos de "
            f"la mitad. En un gráfico de los dos primeros ejes esas variables se ven "
            f"igual que las demás y su posición no dice nada.")
        lineas.append("")

    # ------------------------------------------------------ los conglomerados
    lineas += ["## Los conglomerados", ""]
    elegido = parametros["enlace"]
    lineas.append("| Enlace | Grupos | El mayor | Silueta | Negativas | Acuerdo |")
    lineas.append("| --- | --- | --- | --- | --- | --- |")
    for f in filas_siluetas:
        lineas.append(f"| {f['enlace']} | {f['grupos']} | {f['mayor']} | "
                      f"{cifra(f['silueta'])} | {f['negativas']} | "
                      f"{cifra(f['acuerdo_con_el_elegido'])} |")
    lineas.append("")
    lineas.append(
        f"La última columna es el índice de Rand ajustado contra «{elegido}», que es el "
        f"enlace elegido: vale uno cuando las dos particiones son la misma. Los cuatro "
        f"árboles salen de la misma matriz de distancias, y lo único que cambia entre "
        f"ellos es cómo se mide la distancia entre dos grupos ya armados.")
    lineas.append("")

    lineas += ["### Contra el azar", ""]
    lineas.append(
        f"Agrupar siempre devuelve grupos. Para saber si estos dicen algo, el proyecto "
        f"desordena cada variable por separado —cada columna conserva exactamente sus "
        f"valores y se rompe la relación entre ellas—, vuelve a agrupar y mira la "
        f"silueta. Con {nulo['replicas']} corrimientos:")
    lineas.append("")
    lineas.append(f"- **Datos de verdad:** {cifra(nulo['silueta_real'])}")
    lineas.append(f"- **Desordenados:** de {cifra(nulo['menor'])} a "
                  f"{cifra(nulo['mayor'])}, con mediana {cifra(nulo['mediana'])}")
    lineas.append(f"- **Cuántos igualan o superan al real:** "
                  f"{nulo['nulos_que_igualan_o_superan']} de {nulo['replicas']}")
    lineas.append("")
    if nulo["nulos_que_igualan_o_superan"] == 0:
        lineas.append(
            "Ninguno lo alcanza, así que hay estructura. Eso **no** dice que los grupos "
            "sean los correctos ni que sean los que hay: dice que no son un invento del "
            "método.")
    else:
        lineas.append(
            "Los datos desordenados llegan igual de lejos. Los grupos que salen son del "
            "método y no de los datos.")
    lineas.append("")

    grupos = {}
    for f in filas_grupos:
        grupos.setdefault(f[elegido], []).append(f["unidad"])
    lineas.append(f"Los {len(grupos)} grupos con «{elegido}»:")
    lineas.append("")
    for numero in sorted(grupos):
        lineas.append(f"- **Grupo {numero}** ({len(grupos[numero])}): "
                      + ", ".join(grupos[numero]))
    lineas.append("")

    # --------------------------------------------------- las correspondencias
    lineas += ["## Las correspondencias", ""]
    lineas.append(
        f"La tabla cruza {len(unidades)} filas con {len(columnas_tabla)} columnas y suma "
        f"{numero_texto(ca['total'], 0)} casos. El χ² de independencia es "
        f"{numero_texto(ca['chi2'], 1)} con {ca['gl']} grados de libertad, "
        f"p {p_texto(ca['p'])}, y la inercia total —que es ese χ² dividido por el "
        f"total— es {cifra(ca['inercia_total'], 4)}.")
    lineas.append("")
    lineas.append("| Eje | Inercia | Explica | Acumulado |")
    lineas.append("| --- | --- | --- | --- |")
    for f in filas_ejes:
        lineas.append(f"| {f['eje']} | {cifra(f['inercia'], 4)} | "
                      f"{porcentaje(f['proporcion'])} | {porcentaje(f['acumulado'])} |")
    lineas.append("")

    columnas_ca = [p for p in filas_puntos if p["tipo"] == "columna"]
    if columnas_ca and "eje_1" in columnas_ca[0]:
        orden = sorted(columnas_ca, key=lambda p: p["eje_1"])
        lineas.append(
            f"Sobre el primer eje, las columnas se ordenan de «{orden[0]['punto']}» "
            f"({cifra(orden[0]['eje_1'])}) a «{orden[-1]['punto']}» "
            f"({cifra(orden[-1]['eje_1'])}). Un punto lejos del centro no es «mucho»: es "
            f"**distinto del perfil promedio**, y una fila con el reparto exactamente "
            f"igual al del total cae en el origen por grande que sea.")
        lineas.append("")
        filas_ca = [p for p in filas_puntos if p["tipo"] == "fila"]
        extremos = sorted(filas_ca, key=lambda p: p["eje_1"])
        lineas.append(
            f"Del lado de «{orden[0]['punto']}» queda «{extremos[0]['punto']}» "
            f"({cifra(extremos[0]['eje_1'])}); del otro, «{extremos[-1]['punto']}» "
            f"({cifra(extremos[-1]['eje_1'])}).")
        lineas.append("")

    # --------------------------------------------------------------- avisos
    if avisos:
        lineas += ["## Qué revisar antes de publicar esto", ""]
        for a in avisos:
            lineas.append(f"- **{a['donde'].capitalize()}.** {a['aviso']}")
        lineas.append("")

    return lineas

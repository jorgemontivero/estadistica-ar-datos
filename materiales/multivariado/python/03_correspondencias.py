"""Paso 3: análisis de correspondencias.

Es el PCA de una tabla de contingencia. En vez de variables numéricas hay
conteos, y en vez de varianza hay **inercia**: exactamente el chi cuadrado
dividido por el total de casos.

    inercia total = χ² / n

Eso es lo que lo hace distinto de dibujar la tabla. Cada eje se lleva una parte
de esa inercia, y lo que el mapa muestra es de dónde sale el χ²: qué filas y
qué columnas se apartan de lo que habría si fueran independientes.

**Lo que hay que tener presente al leerlo.** Un punto lejos del centro no es
«mucho»: es **distinto del perfil promedio**. Una jurisdicción con el reparto
educativo exactamente igual al del país cae en el origen aunque sea la más
grande o la más chica. Y las distancias entre una fila y una columna no se leen
directamente: lo que se lee es la dirección.
"""

import math

from comun import chi2_cola, suma
from jacobi import descomponer


def calcular(tabla, filas_nombres, columnas_nombres, parametros):
    """Los ejes, con los perfiles de fila y de columna proyectados.

    La cuenta es una descomposición en valores singulares de los residuos
    tipificados de la tabla:

        S = D_r^(-1/2) · (P − r·cᵀ) · D_c^(-1/2)

    Como la tabla tiene muchas más filas que columnas, se descompone `SᵀS`, que
    es de cinco por cinco: los autovalores de esa matriz son los cuadrados de
    los valores singulares, y de sus autovectores salen las columnas. Las filas
    se obtienen proyectando.
    """
    nf = len(filas_nombres)
    nc = len(columnas_nombres)
    total = suma([tabla[i][j] for i in range(nf) for j in range(nc)])
    if not total > 0:
        raise SystemExit("La tabla de contingencia suma cero.")

    p = [[tabla[i][j] / total for j in range(nc)] for i in range(nf)]
    masa_fila = [suma(p[i]) for i in range(nf)]
    masa_columna = [suma([p[i][j] for i in range(nf)]) for j in range(nc)]
    for i, m in enumerate(masa_fila):
        if not m > 0:
            raise SystemExit(f"La fila «{filas_nombres[i]}» está toda en cero.")
    for j, m in enumerate(masa_columna):
        if not m > 0:
            raise SystemExit(f"La columna «{columnas_nombres[j]}» está toda en cero.")

    s = [[(p[i][j] - masa_fila[i] * masa_columna[j])
          / math.sqrt(masa_fila[i] * masa_columna[j])
          for j in range(nc)] for i in range(nf)]

    # SᵀS, que es chiquita y simétrica.
    gram = [[0.0] * nc for _ in range(nc)]
    for a in range(nc):
        for b in range(a, nc):
            v = suma([s[i][a] * s[i][b] for i in range(nf)])
            gram[a][b] = v
            gram[b][a] = v
    autovalores, autovectores, barridos = descomponer(gram)

    # El último autovalor de una tabla de contingencia es cero por
    # construcción: los perfiles viven en un espacio de una dimensión menos.
    inercias = [max(0.0, v) for v in autovalores]
    inercia_total = suma(inercias)
    ejes_posibles = min(nf, nc) - 1

    # Las coordenadas de columna: el autovector dividido por la raíz de su masa
    # y multiplicado por el valor singular. Las de fila salen proyectando S.
    columnas = []
    filas = []
    for j in range(nc):
        singular = math.sqrt(inercias[j]) if inercias[j] > 0 else 0.0
        vector = autovectores[j]
        columnas.append([vector[k] / math.sqrt(masa_columna[k]) * singular
                         for k in range(nc)])
        if singular > 0:
            proyeccion = []
            for i in range(nf):
                acumulado = suma([s[i][k] * vector[k] for k in range(nc)])
                proyeccion.append(acumulado / math.sqrt(masa_fila[i]))
            filas.append(proyeccion)
        else:
            filas.append([0.0] * nf)

    chi2 = inercia_total * total
    gl = (nf - 1) * (nc - 1)
    return {
        "total": total, "inercias": inercias, "inercia_total": inercia_total,
        "ejes_posibles": ejes_posibles, "masa_fila": masa_fila,
        "masa_columna": masa_columna, "coordenadas_fila": filas,
        "coordenadas_columna": columnas, "chi2": chi2, "gl": gl,
        "p": chi2_cola(chi2, gl), "barridos": barridos, "perfiles": p,
    }


def tabla_de_ejes(salida):
    filas = []
    acumulado = 0.0
    for j in range(salida["ejes_posibles"]):
        inercia = salida["inercias"][j]
        proporcion = inercia / salida["inercia_total"] if salida["inercia_total"] > 0 else None
        acumulado += proporcion if proporcion is not None else 0.0
        filas.append({
            "eje": j + 1,
            "valor_singular": math.sqrt(inercia),
            "inercia": inercia,
            "proporcion": proporcion,
            "acumulado": acumulado,
            "chi2_del_eje": inercia * salida["total"],
        })
    return filas


def tabla_de_puntos(salida, filas_nombres, columnas_nombres, parametros):
    """Filas y columnas en la misma tabla, con su masa, su aporte y su calidad.

    Las tres columnas del final son las que evitan leer mal un mapa. **El
    aporte** dice cuánto de ese eje lo construyó este punto: un eje puede estar
    definido por una sola jurisdicción. **La calidad** dice cuánto de ese punto
    se ve en los ejes elegidos: un punto con calidad baja está dibujado donde
    está por casualidad de la proyección.
    """
    ejes = min(parametros["ejes"], salida["ejes_posibles"])
    puntos = []
    for tipo, nombres, masas, coordenadas in (
            ("fila", filas_nombres, salida["masa_fila"], salida["coordenadas_fila"]),
            ("columna", columnas_nombres, salida["masa_columna"],
             salida["coordenadas_columna"])):
        for i, nombre in enumerate(nombres):
            # La inercia del punto: su masa por su distancia al centro al
            # cuadrado, sumada sobre todos los ejes.
            propia = suma([masas[i] * coordenadas[j][i] ** 2
                           for j in range(salida["ejes_posibles"])])
            fila = {"tipo": tipo, "punto": nombre, "masa": masas[i],
                    "inercia": propia}
            vistos = 0.0
            for j in range(ejes):
                coordenada = coordenadas[j][i]
                fila[f"eje_{j + 1}"] = coordenada
                aporte = (masas[i] * coordenada * coordenada / salida["inercias"][j]
                          if salida["inercias"][j] > 0 else None)
                fila[f"aporte_{j + 1}"] = aporte
                vistos += masas[i] * coordenada * coordenada
            fila["calidad"] = vistos / propia if propia > 0 else None
            puntos.append(fila)
    return puntos


def avisos_de(salida, filas_nombres, columnas_nombres, parametros, tabla):
    avisos = []
    ejes = min(parametros["ejes"], salida["ejes_posibles"])
    acumulado = suma([salida["inercias"][j] for j in range(ejes)]) / salida["inercia_total"]
    avisos.append({
        "donde": "correspondencias",
        "aviso": f"Los {ejes} ejes que se grafican se llevan el "
                 + f"{100 * acumulado:.1f}".replace(".", ",")
                 + f" % de la inercia. El resto está en las otras "
                 + f"{salida['ejes_posibles'] - ejes} dimensiones, que el mapa no muestra."})

    if salida["p"] >= 0.05:
        avisos.append({
            "donde": "correspondencias",
            "aviso": "La prueba de independencia de la tabla no se rechaza. Con filas y "
                     "columnas independientes no hay nada que mapear: la inercia que el "
                     "análisis reparte entre los ejes es ruido."})
    else:
        # El χ² crece con el total de casos: con una tabla de millones, rechaza
        # siempre. Lo que mide la fuerza de la asociación es la inercia, y la V
        # de Cramér es esa inercia puesta en una escala de cero a uno.
        v = math.sqrt(salida["inercia_total"]
                      / (min(len(filas_nombres), len(columnas_nombres)) - 1))
        if salida["total"] > 100000 and v < 0.2:
            avisos.append({
                "donde": "correspondencias",
                "aviso": f"El χ² da "
                         + f"{salida['chi2']:,.0f}".replace(",", ".")
                         + f" y el p es diminuto, pero eso no dice nada: el χ² crece con "
                           f"el total de casos y acá hay "
                         + f"{salida['total']:,.0f}".replace(",", ".")
                         + ". Lo que mide la fuerza de la asociación es la inercia, que es "
                         + f"{salida['inercia_total']:.4f}".replace(".", ",")
                         + "; puesta en escala de cero a uno —la V de Cramér— da "
                         + f"{v:.3f}".replace(".", ",")
                         + ". La asociación existe y es débil. El mapa muestra su forma, no "
                           "su tamaño."})

    puntos = tabla_de_puntos(salida, filas_nombres, columnas_nombres, parametros)
    flojos = [p for p in puntos if p["calidad"] is not None and p["calidad"] < 0.5]
    if flojos:
        cuales = ", ".join(f"«{p['punto']}»" for p in flojos[:4])
        avisos.append({
            "donde": "correspondencias",
            "aviso": f"Hay {len(flojos)} punto(s) con menos de la mitad de su inercia "
                     f"representada en los ejes que se grafican —{cuales}—. Están en el "
                     f"mapa, se ven igual que los demás, y su posición es una sombra: "
                     f"están lejos en una dirección que no se está mirando."})

    for j in range(ejes):
        del_eje = [p for p in puntos if p.get(f"aporte_{j + 1}") is not None]
        peor = max(del_eje, key=lambda p: p[f"aporte_{j + 1}"])
        if peor[f"aporte_{j + 1}"] > 0.5:
            avisos.append({
                "donde": "correspondencias",
                "aviso": f"El eje {j + 1} lo construye casi solo «{peor['punto']}», que "
                         f"aporta el "
                         + f"{100 * peor[f'aporte_{j + 1}']:.1f}".replace(".", ",")
                         + " % de su inercia. Un eje definido por un punto describe a ese "
                           "punto, no a la tabla."})
    return avisos

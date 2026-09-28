"""Paso 2: conglomerados jerárquicos.

Dos cosas que un dendrograma no dice y este paso sí.

**La primera: el enlace cambia los grupos.** «Agrupamiento jerárquico» no es un
método, son cuatro, y sobre los mismos datos dan particiones distintas. El
simple encadena —arma una serpiente larga y deja afuera a los raros—, el
completo y el de Ward hacen bolas compactas. No hay uno correcto: hay uno
elegido, y hay que decir cuál.

**La segunda, y es la importante: agrupar siempre devuelve grupos.** Pedirle
cuatro conglomerados a una nube sin ninguna estructura devuelve cuatro
conglomerados prolijos, con su dendrograma y todo. Para saber si los grupos
dicen algo hay que compararlos contra el caso en que no dicen nada, y eso es lo
que hace la parte del nulo: se desordena cada columna por separado —con lo cual
cada variable conserva exactamente sus valores y se rompe la relación entre
ellas—, se vuelve a agrupar y se mira la silueta. Si la silueta de los datos de
verdad no le gana a la de los datos desordenados, los grupos son del método y
no de los datos.
"""

import math

from comun import suma

ENLACES = ["simple", "completo", "promedio", "ward"]


def distancias(base):
    """La matriz de distancias euclídeas entre unidades.

    Sobre los datos **tipificados**, siempre. Una distancia euclídea sobre
    columnas en unidades distintas es una suma de cosas que no se suman: la
    variable de números más grandes decide toda la distancia.
    """
    n = len(base)
    p = len(base[0])
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            total = 0.0
            for k in range(p):
                diferencia = base[i][k] - base[j][k]
                total += diferencia * diferencia
            valor = math.sqrt(total)
            d[i][j] = valor
            d[j][i] = valor
    return d


def _lance_williams(enlace, dik, djk, dij, ni, nj, nk):
    """La fórmula que actualiza la distancia al fusionar i con j.

    Los cuatro enlaces son la misma recurrencia con otros coeficientes, y
    escribirlos juntos deja ver que la diferencia entre ellos es de tres
    números y no de método.
    """
    if enlace == "simple":
        return min(dik, djk)
    if enlace == "completo":
        return max(dik, djk)
    if enlace == "promedio":
        return (ni * dik + nj * djk) / (ni + nj)
    # Ward trabaja sobre distancias **al cuadrado**; la altura que se informa
    # después es su raíz. Es lo que hace `hclust(method = "ward.D2")`.
    total = ni + nj + nk
    return ((ni + nk) * dik + (nj + nk) * djk - nk * dij) / total


def agrupar(d, enlace):
    """El árbol completo, de n grupos de a uno hasta uno solo de n.

    En cada paso se fusiona el par más cercano. **Los empates se rompen por
    índice**, del más chico al más grande: sin esa regla, dos motores podrían
    fusionar en distinto orden y devolver árboles distintos con las mismas
    distancias.
    """
    n = len(d)
    # Ward opera sobre cuadrados. El resto, sobre la distancia tal cual.
    trabajo = [[(v * v if enlace == "ward" else v) for v in fila] for fila in d]
    activos = list(range(n))
    miembros = {i: [i] for i in range(n)}
    fusiones = []

    while len(activos) > 1:
        mejor = None
        for a in range(len(activos)):
            for b in range(a + 1, len(activos)):
                i, j = activos[a], activos[b]
                valor = trabajo[i][j]
                if mejor is None or valor < mejor[0]:
                    mejor = (valor, i, j)
        valor, i, j = mejor
        altura = math.sqrt(valor) if enlace == "ward" else valor
        fusiones.append({
            "paso": len(fusiones) + 1,
            "grupo_a": i, "grupo_b": j,
            "altura": altura,
            "tamano": len(miembros[i]) + len(miembros[j]),
        })

        ni, nj = len(miembros[i]), len(miembros[j])
        for k in activos:
            if k in (i, j):
                continue
            trabajo[i][k] = trabajo[k][i] = _lance_williams(
                enlace, trabajo[i][k], trabajo[j][k], trabajo[i][j], ni, nj,
                len(miembros[k]))
        miembros[i] = miembros[i] + miembros[j]
        del miembros[j]
        activos.remove(j)

    return fusiones, miembros


def cortar(fusiones, n, k):
    """La partición en k grupos: se rehacen las fusiones hasta que queden k.

    Las etiquetas salen **por el miembro más chico de cada grupo**, para que el
    grupo 1 sea siempre el mismo grupo y no dependa del orden en que el
    algoritmo los fue armando.

    Con el `agrupar` de acá arriba la regla es redundante —el par se elige
    recorriendo los activos en orden, así que la raíz de un grupo ya es su
    miembro más chico— y está escrita igual: si alguien cambia cómo se elige el
    par, la numeración tiene que seguir siendo la misma.
    """
    miembros = {i: [i] for i in range(n)}
    for f in fusiones[:max(0, n - k)]:
        miembros[f["grupo_a"]] = miembros[f["grupo_a"]] + miembros[f["grupo_b"]]
        del miembros[f["grupo_b"]]
    orden = sorted(miembros, key=lambda i: min(miembros[i]))
    etiquetas = [0] * n
    for numero, raiz in enumerate(orden, start=1):
        for m in miembros[raiz]:
            etiquetas[m] = numero
    return etiquetas


def silueta(d, etiquetas):
    """La silueta de cada unidad y el promedio.

    Para cada unidad: `a` es lo lejos que está de las de su propio grupo, `b` lo
    lejos que está del grupo ajeno más cercano, y la silueta es (b − a) dividido
    por el mayor de los dos. Uno quiere decir «clavada en su grupo», cero «justo
    en el borde» y negativo «está en el grupo equivocado».

    Una unidad sola en su grupo tiene silueta cero por convención: no hay con
    quién compararla adentro.
    """
    n = len(etiquetas)
    grupos = sorted(set(etiquetas))
    por_unidad = []
    for i in range(n):
        propio = [j for j in range(n) if etiquetas[j] == etiquetas[i] and j != i]
        if not propio:
            por_unidad.append(0.0)
            continue
        a = suma([d[i][j] for j in propio]) / len(propio)
        b = None
        for g in grupos:
            if g == etiquetas[i]:
                continue
            ajenos = [j for j in range(n) if etiquetas[j] == g]
            if not ajenos:
                continue
            media = suma([d[i][j] for j in ajenos]) / len(ajenos)
            if b is None or media < b:
                b = media
        if b is None:
            por_unidad.append(0.0)
        else:
            por_unidad.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return por_unidad, suma(por_unidad) / n


def rand_ajustado(a, b):
    """Cuánto se parecen dos particiones, corregido por el azar.

    Vale 1 si son la misma partición y alrededor de 0 si coinciden lo que
    coincidirían dos particiones cualesquiera. Hace falta porque las etiquetas
    de los grupos son arbitrarias: el grupo 1 de un enlace no tiene por qué ser
    el grupo 1 del otro.
    """
    n = len(a)
    ga, gb = sorted(set(a)), sorted(set(b))
    tabla = [[sum(1 for i in range(n) if a[i] == x and b[i] == y) for y in gb]
             for x in ga]

    def combina(x):
        return x * (x - 1) / 2

    juntos = suma([combina(c) for fila in tabla for c in fila])
    filas = suma([combina(sum(fila)) for fila in tabla])
    columnas = suma([combina(sum(tabla[i][j] for i in range(len(ga))))
                     for j in range(len(gb))])
    total = combina(n)
    esperado = filas * columnas / total
    maximo = (filas + columnas) / 2
    if maximo == esperado:
        return 1.0
    return (juntos - esperado) / (maximo - esperado)


def desplazar(base, corrimiento):
    """Cada columna corrida un poco más que la anterior.

    Es la manera de romper la relación entre las variables **sin tocar los
    valores**: cada columna conserva exactamente los suyos, su media y su
    desvío, y lo único que se pierde es con qué fila iba cada uno. No hace
    falta ningún generador de azar, así que los dos idiomas arman exactamente
    los mismos nulos.
    """
    n = len(base)
    p = len(base[0])
    salida = []
    for i in range(n):
        fila = []
        for j in range(p):
            fila.append(base[(i + (j + 1) * corrimiento) % n][j])
        salida.append(fila)
    return salida


def calcular(base, unidades, parametros):
    d = distancias(base)
    n = len(unidades)
    k = parametros["conglomerados"]
    if k > n:
        raise SystemExit(f"Se piden {k} conglomerados y hay {n} unidades.")

    por_enlace = {}
    for enlace in ENLACES:
        fusiones, _ = agrupar(d, enlace)
        etiquetas = cortar(fusiones, n, k)
        propias, media = silueta(d, etiquetas)
        por_enlace[enlace] = {"fusiones": fusiones, "etiquetas": etiquetas,
                              "siluetas": propias, "silueta": media}

    elegido = parametros["enlace"]
    if elegido not in por_enlace:
        raise SystemExit(f"«{elegido}» no es un enlace conocido. Hay: "
                         f"{', '.join(ENLACES)}.")
    return d, por_enlace


def tabla_de_grupos(unidades, por_enlace, parametros):
    elegido = parametros["enlace"]
    filas = []
    for i, nombre in enumerate(unidades):
        fila = {"unidad": nombre}
        for enlace in ENLACES:
            fila[enlace] = por_enlace[enlace]["etiquetas"][i]
        fila["silueta"] = por_enlace[elegido]["siluetas"][i]
        filas.append(fila)
    return filas


def tabla_de_fusiones(por_enlace, unidades):
    filas = []
    for enlace in ENLACES:
        for f in por_enlace[enlace]["fusiones"]:
            filas.append({
                "enlace": enlace, "paso": f["paso"],
                "unidad_a": unidades[f["grupo_a"]],
                "unidad_b": unidades[f["grupo_b"]],
                "altura": f["altura"], "tamano": f["tamano"],
            })
    return filas


def tabla_de_siluetas(por_enlace, parametros):
    elegido = parametros["enlace"]
    referencia = por_enlace[elegido]["etiquetas"]
    filas = []
    for enlace in ENLACES:
        etiquetas = por_enlace[enlace]["etiquetas"]
        tamanos = [etiquetas.count(g) for g in sorted(set(etiquetas))]
        filas.append({
            "enlace": enlace,
            "grupos": len(tamanos),
            "mayor": max(tamanos),
            "menor": min(tamanos),
            "silueta": por_enlace[enlace]["silueta"],
            "negativas": sum(1 for s in por_enlace[enlace]["siluetas"] if s < 0),
            "acuerdo_con_el_elegido": rand_ajustado(etiquetas, referencia),
        })
    return filas


def contra_el_nulo(base, parametros):
    """La misma silueta, sobre datos a los que se les rompió la relación.

    Hay tantos nulos como corrimientos posibles: con n unidades, n − 1. Ninguno
    inventa datos y todos conservan cada columna intacta.
    """
    n = len(base)
    k = parametros["conglomerados"]
    enlace = parametros["enlace"]
    filas = []
    for corrimiento in range(1, n):
        movida = desplazar(base, corrimiento)
        d = distancias(movida)
        fusiones, _ = agrupar(d, enlace)
        etiquetas = cortar(fusiones, n, k)
        _propias, media = silueta(d, etiquetas)
        filas.append({"corrimiento": corrimiento, "silueta": media})
    return filas


def resumen_del_nulo(nulos, real):
    valores = sorted(f["silueta"] for f in nulos)
    n = len(valores)
    mediana = (valores[n // 2] if n % 2 else (valores[n // 2 - 1] + valores[n // 2]) / 2)
    mejores = sum(1 for v in valores if v >= real)
    return {
        "replicas": n,
        "silueta_real": real,
        "menor": valores[0],
        "mediana": mediana,
        "mayor": valores[-1],
        "nulos_que_igualan_o_superan": mejores,
        # La proporción de nulos que llegan a la silueta real. No es un valor p
        # —los nulos no son independientes entre sí— pero se lee parecido.
        "proporcion": mejores / n,
    }


def avisos_de(por_enlace, nulo, parametros, unidades):
    salida = []
    elegido = parametros["enlace"]

    if nulo["mayor"] >= nulo["silueta_real"]:
        salida.append({
            "donde": "conglomerados",
            "aviso": f"La silueta de los datos de verdad es "
                     + f"{nulo['silueta_real']:.3f}".replace(".", ",")
                     + f" y la de los datos desordenados llega hasta "
                     + f"{nulo['mayor']:.3f}".replace(".", ",")
                     + ". Los grupos que salen no son mejores que los que salen de una "
                       "tabla a la que se le rompió la relación entre variables: son del "
                       "método, no de los datos."})
    else:
        salida.append({
            "donde": "conglomerados",
            "aviso": f"La silueta de los datos de verdad es "
                     + f"{nulo['silueta_real']:.3f}".replace(".", ",")
                     + f" y ninguno de los {nulo['replicas']} desordenados la alcanza: el "
                     + f"mejor llega a "
                     + f"{nulo['mayor']:.3f}".replace(".", ",")
                     + ". Hay estructura. Eso no dice que los grupos sean los correctos ni "
                       "que sean cuatro: dice que no son un invento del método."})

    acuerdos = tabla_de_siluetas(por_enlace, parametros)
    peor = min((f for f in acuerdos if f["enlace"] != elegido),
               key=lambda f: f["acuerdo_con_el_elegido"])
    salida.append({
        "donde": "conglomerados",
        "aviso": f"Cambiar de enlace cambia los grupos. Entre «{elegido}» y "
                 f"«{peor['enlace']}» el índice de Rand ajustado es "
                 + f"{peor['acuerdo_con_el_elegido']:.3f}".replace(".", ",")
                 + ". Los cuatro árboles salen de la misma matriz de distancias: lo único "
                   "que cambia es cómo se mide la distancia entre dos grupos ya armados."})

    for enlace in ("simple",):
        etiquetas = por_enlace[enlace]["etiquetas"]
        tamanos = [etiquetas.count(g) for g in sorted(set(etiquetas))]
        if max(tamanos) >= len(unidades) - len(tamanos):
            salida.append({
                "donde": "conglomerados",
                "aviso": f"El enlace {enlace} deja {max(tamanos)} de las "
                         f"{len(unidades)} unidades en un solo grupo y el resto casi "
                         f"sueltas. Es lo que hace: encadena. No está roto, está haciendo "
                         f"lo que la fórmula dice, y por eso casi nunca se usa para armar "
                         f"tipologías."})

    negativas = sum(1 for s in por_enlace[elegido]["siluetas"] if s < 0)
    if negativas:
        salida.append({
            "donde": "conglomerados",
            "aviso": f"Hay {negativas} unidad(es) con silueta negativa: están más cerca "
                     f"del grupo de al lado que del propio. Un dendrograma no las muestra, "
                     f"y en un mapa de los dos primeros componentes tampoco se ven."})
    return salida

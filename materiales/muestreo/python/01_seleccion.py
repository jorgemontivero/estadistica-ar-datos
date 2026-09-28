"""Paso 1: sacar la muestra, de cuatro maneras.

Los cuatro diseños salen del **mismo marco y con la misma semilla**, y cada
uno deja escrito cuál es la probabilidad de inclusión de cada unidad. Esa
probabilidad es todo lo que el paso siguiente necesita: el ponderador es su
inversa, y de ahí sale cualquier estimación.

    aleatorio simple   n de N, todos con la misma probabilidad.
    sistemático        un arranque al azar y después cada k. Es el más fácil
                       de ejecutar en campo y el único de los cuatro que **no
                       tiene un estimador insesgado de la varianza**.
    estratificado      se reparte la muestra entre los estratos y dentro de
                       cada uno se hace un aleatorio simple. Con afijación
                       proporcional o de Neyman.
    bietápico          primero se sortean conglomerados dentro de cada
                       estrato, y después hogares dentro de cada conglomerado
                       elegido. Es el diseño de cualquier encuesta de hogares
                       que salga a la calle.

Los cuatro devuelven lo mismo —las posiciones elegidas y su probabilidad—, así
que el resto del proyecto no necesita saber cuál se usó.
"""

import math

from azar import GeneradorR, sample_int
from comun import indices_por, ordenar


def aleatorio_simple(datos, n, semilla):
    """`set.seed(semilla); sample.int(N, n)`, ni más ni menos."""
    total = len(datos)
    elegidos = sample_int(GeneradorR(semilla), total, n)
    probabilidad = n / total
    return [{"fila": i - 1, "probabilidad": probabilidad, "conglomerado": None}
            for i in sorted(elegidos)]


def sistematico(datos, n, semilla):
    """Arranque al azar en (0, k] y después cada k, con k = N/n.

    El intervalo se deja decimal a propósito. Redondearlo es lo que hace que
    una muestra sistemática termine con un caso de más o de menos, y con el
    último tramo del marco sin representar.

    **Ojo con el orden del marco.** Un sistemático sobre un marco ordenado por
    una variable relacionada con lo que se mide es, en los hechos, un
    estratificado —y sale mejor que un aleatorio simple—. Sobre un marco con
    una periodicidad que coincida con k, sale mucho peor. El diseño no está en
    el algoritmo: está en cómo viene ordenado el archivo.
    """
    total = len(datos)
    k = total / n
    arranque = GeneradorR(semilla).unif() * k
    posiciones = []
    for i in range(n):
        # El techo de arranque + i·k, acotado al último caso.
        pos = min(total, int(math.ceil(arranque + i * k)))
        posiciones.append(max(1, pos))
    probabilidad = n / total
    return ([{"fila": p - 1, "probabilidad": probabilidad, "conglomerado": None}
             for p in sorted(set(posiciones))], k, arranque)


def afijar(tamanos, desvios, n, metodo):
    """Cuántos casos le tocan a cada estrato.

    proporcional   en proporción a su tamaño. Es la que casi siempre se usa y
                   la que hace que todos los pesos salgan iguales.
    neyman         en proporción a N_h·S_h: más muestra donde hay más
                   dispersión. Minimiza la varianza para un n dado, y a cambio
                   deja pesos desiguales.

    El reparto se hace por restos mayores y no redondeando cada cuota, para
    que la suma dé exactamente n. Redondear una por una es lo que hace que una
    muestra de 320 termine teniendo 318 o 323.
    """
    if metodo == "neyman":
        pesos = [tamanos[i] * desvios[i] for i in range(len(tamanos))]
    else:
        pesos = list(tamanos)
    suma = math.fsum(pesos)
    if suma <= 0:
        pesos = [1.0] * len(tamanos)
        suma = float(len(tamanos))

    exactos = [n * p / suma for p in pesos]
    enteros = [int(x) for x in exactos]
    # Los que sobran van a los estratos con el resto más grande; entre restos
    # iguales manda el orden del estrato, para que no dependa del azar.
    faltan = n - sum(enteros)
    orden = sorted(range(len(pesos)), key=lambda i: (-(exactos[i] - enteros[i]), i))
    for i in range(faltan):
        enteros[orden[i % len(orden)]] += 1
    # Nadie puede quedar con menos de dos casos ni con más de los que tiene.
    return [min(tamanos[i], max(2, enteros[i])) for i in range(len(enteros))]


def estratificado(datos, n, semilla, estrato, metodo, valores):
    """Un aleatorio simple dentro de cada estrato, con las cuotas ya repartidas.

    La semilla se usa una sola vez y el generador se pasa de estrato en
    estrato, igual que haría un `for` en R con un único `set.seed` al
    principio. Sembrar de nuevo en cada estrato daría muestras correlacionadas
    entre estratos, que es un error silencioso y bastante común.
    """
    grupos = indices_por(datos, estrato)
    nombres = list(grupos)
    tamanos = [len(grupos[h]) for h in nombres]
    desvios = []
    for h in nombres:
        v = [valores[i] for i in grupos[h]]
        m = math.fsum(v) / len(v)
        desvios.append(math.sqrt(math.fsum((x - m) ** 2 for x in v) / (len(v) - 1))
                       if len(v) > 1 else 0.0)

    cuotas = afijar(tamanos, desvios, n, metodo)
    generador = GeneradorR(semilla)
    salida = []
    for j, h in enumerate(nombres):
        posiciones = grupos[h]
        elegidos = sample_int(generador, len(posiciones), cuotas[j])
        probabilidad = cuotas[j] / len(posiciones)
        for e in sorted(elegidos):
            salida.append({"fila": posiciones[e - 1], "probabilidad": probabilidad,
                           "conglomerado": None})
    salida.sort(key=lambda f: f["fila"])
    return salida, dict(zip(nombres, cuotas))


def bietapico(datos, semilla, estrato, conglomerado, por_estrato, por_conglomerado):
    """Conglomerados dentro de cada estrato, y hogares dentro de cada uno.

    La probabilidad de inclusión de un hogar es el producto de las dos etapas:

        π = (a_h / A_h) · (m / M_i)

    donde a_h de los A_h conglomerados del estrato salieron sorteados, y m de
    los M_i hogares del conglomerado i. Si todos los conglomerados tuvieran el
    mismo tamaño, esa probabilidad sería igual para todos y los pesos saldrían
    parejos; como no lo son, no salen parejos, y ahí empieza a importar el
    ponderador.
    """
    por_estr = indices_por(datos, estrato)
    generador = GeneradorR(semilla)
    salida = []
    detalle = []
    for h in por_estr:
        # Los conglomerados del estrato, en orden fijo.
        nombres = ordenar([datos[i][conglomerado] for i in por_estr[h]])
        cuantos = min(por_estrato, len(nombres))
        elegidos = sample_int(generador, len(nombres), cuantos)
        detalle.append({"estrato": h, "conglomerados_en_el_marco": len(nombres),
                        "conglomerados_elegidos": cuantos})
        for e in sorted(elegidos):
            nombre = nombres[e - 1]
            dentro = [i for i in por_estr[h] if datos[i][conglomerado] == nombre]
            m = min(por_conglomerado, len(dentro))
            hogares = sample_int(generador, len(dentro), m)
            probabilidad = (cuantos / len(nombres)) * (m / len(dentro))
            for g in sorted(hogares):
                salida.append({"fila": dentro[g - 1], "probabilidad": probabilidad,
                               "conglomerado": nombre})
    salida.sort(key=lambda f: f["fila"])
    return salida, detalle


def calcular(datos, parametros, valores):
    """Los cuatro diseños, con el mismo tamaño de muestra.

    El tamaño lo fija el bietápico —conglomerados por estrato × hogares por
    conglomerado × estratos— y los otros tres lo copian, porque comparar
    diseños de distinto n no diría nada sobre el diseño.
    """
    semilla = parametros["semilla"]
    estrato = parametros["estrato"]
    conglomerado = parametros["conglomerado"]

    dos_etapas, detalle = bietapico(datos, semilla, estrato, conglomerado,
                                    parametros["conglomerados_por_estrato"],
                                    parametros["hogares_por_conglomerado"])
    n = len(dos_etapas)

    sis, intervalo, arranque = sistematico(datos, n, semilla)
    proporcional, cuotas_p = estratificado(datos, n, semilla, estrato,
                                           "proporcional", valores)
    neyman, cuotas_n = estratificado(datos, n, semilla, estrato, "neyman", valores)

    return {
        "n": n,
        "disenos": {
            "aleatorio simple": aleatorio_simple(datos, n, semilla),
            "sistemático": sis,
            "estratificado proporcional": proporcional,
            "estratificado de Neyman": neyman,
            "bietápico": dos_etapas,
        },
        "intervalo": intervalo, "arranque": arranque,
        "cuotas_proporcional": cuotas_p, "cuotas_neyman": cuotas_n,
        "detalle_bietapico": detalle,
    }

"""Autovalores y autovectores de una matriz simétrica, a mano y sin dependencias.

Es la pieza de la que cuelga todo el proyecto: componentes principales,
correspondencias y hasta las distancias salen de descomponer una matriz
simétrica. Está escrita a mano por dos razones.

**La primera es que tiene que dar lo mismo en los dos idiomas.** `eigen` de R y
`numpy.linalg.eigh` usan LAPACK, y aun así no devuelven los mismos bits: eligen
distinto el orden de los autovalores empatados, y sobre todo eligen distinto el
**signo** de cada autovector. Un componente principal con el signo cambiado es
el mismo componente —la varianza explicada no cambia, las cargas cambian todas
de signo a la vez— pero es la causa número uno de que dos personas digan que
«el PCA les dio distinto». Acá el signo lo fija una regla escrita más abajo.

**La segunda es que el método de Jacobi se puede leer.** Son cuarenta líneas de
rotaciones de dos por dos que van poniendo ceros fuera de la diagonal, y cada
una se entiende sola. Para matrices chicas —las de este proyecto tienen ocho y
cinco filas— es tan preciso como cualquier otro método y bastante más
transparente.

**No hay ninguna suma compensada acá adentro.** En el resto del proyecto las
sumas largas van con `math.fsum`, que en R no existe; acá todo se acumula con
sumas comunes en un orden fijo, así que las dos versiones hacen exactamente las
mismas operaciones de punto flotante y devuelven exactamente los mismos bits.
"""

import math

# Cuándo se considera que ya no queda nada fuera de la diagonal. Es una suma de
# cuadrados, así que la tolerancia se compara contra su raíz.
TOLERANCIA = 1e-14
BARRIDOS = 100


def identidad(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def simetrica(a) -> bool:
    n = len(a)
    return all(a[i][j] == a[j][i] for i in range(n) for j in range(i + 1, n))


def fuera_de_la_diagonal(a) -> float:
    """La suma de los cuadrados de lo que hay fuera de la diagonal.

    Es lo que el método va llevando a cero: cuando esto es cero, la matriz es
    diagonal y en la diagonal están los autovalores.
    """
    n = len(a)
    total = 0.0
    for p in range(n - 1):
        for q in range(p + 1, n):
            total += a[p][q] * a[p][q]
    return total


def rotar(a, v, p: int, q: int) -> None:
    """Una rotación de Jacobi: la que pone en cero el elemento (p, q).

    El ángulo sale de resolver una cuadrática. La forma en que se calcula `t`
    —con el signo adelante y la raíz en el denominador— no es capricho: es la
    que evita restar dos números parecidos, que es donde una implementación
    ingenua pierde precisión.
    """
    n = len(a)
    theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
    if theta >= 0.0:
        t = 1.0 / (theta + math.sqrt(theta * theta + 1.0))
    else:
        t = -1.0 / (-theta + math.sqrt(theta * theta + 1.0))
    c = 1.0 / math.sqrt(t * t + 1.0)
    s = t * c

    for k in range(n):
        akp = a[k][p]
        akq = a[k][q]
        a[k][p] = c * akp - s * akq
        a[k][q] = s * akp + c * akq
    for k in range(n):
        apk = a[p][k]
        aqk = a[q][k]
        a[p][k] = c * apk - s * aqk
        a[q][k] = s * apk + c * aqk
    # Los dos que la rotación acaba de anular se ponen en cero exacto: el valor
    # que queda es del orden del error de redondeo y dejarlo hace que el
    # criterio de corte tarde de más.
    a[p][q] = 0.0
    a[q][p] = 0.0

    for k in range(n):
        vkp = v[k][p]
        vkq = v[k][q]
        v[k][p] = c * vkp - s * vkq
        v[k][q] = s * vkp + c * vkq


def ordenar_y_fijar_signo(valores, vectores):
    """Los autovalores de mayor a menor, y el signo de cada vector decidido.

    **El signo de un autovector es arbitrario**: si v es autovector, −v también,
    con el mismo autovalor. Ningún método lo determina, así que cada biblioteca
    devuelve el que le sale, y de ahí vienen los «me dio al revés que a vos».

    La regla de acá: el elemento de mayor valor absoluto de cada vector queda
    **positivo**, y si hay empate manda el de índice más chico. Es arbitraria
    igual que cualquier otra, pero está escrita, así que el resultado se puede
    reproducir. Es la misma convención que usan varios paquetes de PCA.
    """
    n = len(valores)
    orden = sorted(range(n), key=lambda i: (-valores[i], i))
    nuevos = [valores[i] for i in orden]
    columnas = []
    for i in orden:
        columna = [vectores[k][i] for k in range(n)]
        mayor = 0
        for k in range(1, n):
            if abs(columna[k]) > abs(columna[mayor]):
                mayor = k
        if columna[mayor] < 0.0:
            columna = [-x for x in columna]
        columnas.append(columna)
    return nuevos, columnas


def descomponer(a, tolerancia: float = TOLERANCIA, barridos: int = BARRIDOS):
    """Los autovalores y autovectores de una matriz simétrica.

    Devuelve los autovalores de mayor a menor y los autovectores como una lista
    de columnas: `vectores[j][i]` es la coordenada i del autovector j.
    """
    n = len(a)
    if n == 0:
        return [], [], 0
    if not simetrica(a):
        raise SystemExit("La matriz que se quiere descomponer no es simétrica. "
                         "Jacobi solo sirve para simétricas.")

    trabajo = [fila[:] for fila in a]
    v = identidad(n)
    usados = 0
    for _ in range(barridos):
        if math.sqrt(fuera_de_la_diagonal(trabajo)) <= tolerancia:
            break
        usados += 1
        for p in range(n - 1):
            for q in range(p + 1, n):
                if trabajo[p][q] != 0.0:
                    rotar(trabajo, v, p, q)
    else:
        raise SystemExit(f"Jacobi no convergió en {barridos} barridos. La matriz "
                         f"debe tener algo raro: revisá que no haya infinitos.")

    valores = [trabajo[i][i] for i in range(n)]
    valores, vectores = ordenar_y_fijar_signo(valores, v)
    return valores, vectores, usados


def por_vector(a, v):
    """El producto de una matriz por un vector, en orden fijo."""
    salida = []
    for fila in a:
        total = 0.0
        for j in range(len(v)):
            total += fila[j] * v[j]
        salida.append(total)
    return salida

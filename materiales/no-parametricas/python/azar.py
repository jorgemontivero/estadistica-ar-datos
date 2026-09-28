"""El generador de números al azar, escrito a mano.

**Por qué no se usa `sample()` de R ni `random` de Python.** Los dos usan
Mersenne Twister, así que suena a que con la misma semilla darían lo mismo. No
lo dan: difieren en cómo siembran el estado y en cómo convierten el número de
32 bits en un índice entre 1 y n. Con la misma semilla y el mismo n, la
primera fila remuestreada ya sale distinta.

Y eso, en un bootstrap, no es un detalle de formato. Todo el resultado —cada
límite de cada intervalo, cada valor p de permutación— sale de qué filas
tocaron. Si los dos idiomas remuestrean distinto, los archivos dejan de ser
comparables, y la promesa de este proyecto es que salen idénticos byte a byte.

Lo que hay acá es un **generador congruencial multiplicativo** de Lehmer, el
clásico de Park y Miller:

    x ← 48271 · x  (mod 2³¹ − 1)

Se eligió ese par de constantes por una razón práctica: el producto más grande
posible, 48271 × 2147483646, vale alrededor de 1,04·10¹⁴, y eso entra exacto
en un número de doble precisión —que aguanta enteros hasta 9·10¹⁵—. O sea que
R, que no tiene enteros de 64 bits, calcula exactamente lo mismo que Python
sin ningún truco.

**Sus límites, declarados.** El período es 2³¹ − 2, unos 2.100 millones de
números. Un bootstrap de 2.000 réplicas sobre 150 casos consume 300.000, o sea
la siete milésima parte: no hay riesgo de dar la vuelta. Pero no es un
generador para criptografía ni para simulaciones que pidan millones de
millones de números, y los pares consecutivos caen sobre un retículo, que es
la debilidad conocida de todos los congruenciales. Para remuestrear una tabla
está de sobra; para otra cosa, conviene mirarlo dos veces.
"""

MODULO = 2147483647       # 2³¹ − 1, que es primo
MULTIPLICADOR = 48271     # raíz primitiva de ese primo


class Azar:
    """Un flujo de números al azar reproducible.

    Se pasa como objeto y no como estado global a propósito: así cada paso del
    proyecto puede arrancar de su propia semilla y no depende de en qué orden
    corrieron los otros.
    """

    def __init__(self, semilla):
        self.estado = int(semilla) % MODULO
        # El cero es un punto fijo de la multiplicación: si el estado cae ahí,
        # el generador devuelve ceros para siempre.
        if self.estado <= 0:
            self.estado += MODULO - 1

    def siguiente(self) -> int:
        self.estado = (MULTIPLICADOR * self.estado) % MODULO
        return self.estado

    def uniforme(self) -> float:
        """Un número en [0, 1)."""
        return (self.siguiente() - 1) / (MODULO - 1)

    def indice(self, n: int) -> int:
        """Un índice entre 0 y n − 1, con la misma probabilidad cada uno.

        El `min` cubre el caso de borde en que `uniforme()` devuelve algo que
        al multiplicar por n redondea justo a n.
        """
        return min(n - 1, int(self.uniforme() * n))

    def remuestrear(self, n: int) -> list[int]:
        """n índices con reposición: una réplica de bootstrap."""
        return [self.indice(n) for _ in range(n)]

    def permutar(self, n: int) -> list[int]:
        """Una permutación de 0 a n − 1, por Fisher-Yates hacia atrás.

        Es el algoritmo que hay que escribir a mano de los dos lados por lo
        mismo que el generador: `sample()` de R y `random.shuffle` de Python
        recorren el arreglo en órdenes distintos y consumen una cantidad
        distinta de números.
        """
        orden = list(range(n))
        for i in range(n - 1, 0, -1):
            j = self.indice(i + 1)
            orden[i], orden[j] = orden[j], orden[i]
        return orden

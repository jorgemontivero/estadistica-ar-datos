"""El generador de R, reimplementado en Python.

Este archivo **no tiene equivalente en R**, y esa asimetría es el punto.

Una muestra hay que poder volver a sacarla. No es una preferencia de estilo:
es lo que separa una selección auditable de una que hay que creer. Si alguien
pregunta cómo se eligieron esos 320 hogares, la respuesta tiene que ser un
par de líneas que cualquiera pueda correr y obtener exactamente los mismos
320.

El estándar de hecho para eso, en estadística oficial y en investigación, es
R:

    set.seed(2026)
    sample.int(80, 8)

Por eso la versión en R de este proyecto **usa `set.seed` y `sample.int` tal
cual**, sin ninguna capa intermedia, y la de Python reproduce ese generador
bit por bit. Al revés no serviría: nadie audita una selección corriendo el
`random` de Python.

Lo que hay que copiar, y que no es obvio:

    1. `set.seed(s)` no carga la semilla directo en el estado. Primero la pasa
       cincuenta veces por la congruencial s ← 69069·s + 1 —el «initial
       scrambling»— y después llena las 625 posiciones del vector siguiendo
       con la misma congruencial.
    2. La primera de esas 625 posiciones es el índice del generador, no parte
       del estado, y R la pisa con 624 apenas arranca: eso fuerza a que la
       primera llamada regenere el bloque entero.
    3. El real que sale pasa por `fixup`, que corre un 0 o un 1 exactos al
       interior del intervalo.
    4. Desde la versión 3.6, R sortea enteros **por rechazo** y no con
       floor(n·u). El método viejo tenía un sesgo medible con poblaciones
       grandes. Y el armado de bits tiene un bucle que va de 0 a `bits`
       INCLUSIVE: con 16 bits justos hace dos tandas y no una. Parece un
       descuido y es lo que R hace; copiarlo «corregido» daría otra muestra.

La calculadora `calc-muestreo` del sitio hace exactamente lo mismo en
TypeScript, así que la página, este proyecto y R coinciden en la muestra.
"""

import math

N = 624
M = 397
MATRIZ_A = 0x9908B0DF
MASCARA_ALTA = 0x80000000
MASCARA_BAJA = 0x7FFFFFFF

# 1/(2³² − 1), el borde que usa `fixup` para no devolver nunca 0 ni 1.
I2_32M1 = 2.328306437080797e-10
# 2⁻³², la escala con que MT_genrand pasa de entero a real.
DOS_A_LA_MENOS_32 = 2.3283064365386963e-10


def fixup(x: float) -> float:
    """El `fixup` de R: corre un 0 o un 1 exactos al interior de (0, 1).

    Actúa cuando el Mersenne-Twister devuelve un cero exacto, que pasa una vez
    cada 2³² números. Está separada para poder probarla directamente: ninguna
    comparación contra un chorro aleatorio la ejercita.
    """
    if x <= 0:
        return 0.5 * I2_32M1
    if 1 - x <= 0:
        return 1 - 0.5 * I2_32M1
    return x


class GeneradorR:
    """El Mersenne-Twister de R, con su estado y su sembrado."""

    def __init__(self, semilla: int):
        s = int(semilla) & 0xFFFFFFFF
        for _ in range(50):
            s = (69069 * s + 1) & 0xFFFFFFFF
        # La primera posición del vector de semilla es el índice: se genera y
        # se descarta, porque R la reemplaza por 624.
        s = (69069 * s + 1) & 0xFFFFFFFF
        self.mt = [0] * N
        for j in range(N):
            s = (69069 * s + 1) & 0xFFFFFFFF
            self.mt[j] = s
        self.mti = N

    def _genrand(self) -> float:
        """MT_genrand de R: un real en [0, 1) con 32 bits de resolución."""
        mt = self.mt
        if self.mti >= N:
            for kk in range(N - M):
                y = (mt[kk] & MASCARA_ALTA) | (mt[kk + 1] & MASCARA_BAJA)
                mt[kk] = mt[kk + M] ^ (y >> 1) ^ (MATRIZ_A if y & 1 else 0)
            for kk in range(N - M, N - 1):
                y = (mt[kk] & MASCARA_ALTA) | (mt[kk + 1] & MASCARA_BAJA)
                mt[kk] = mt[kk + (M - N)] ^ (y >> 1) ^ (MATRIZ_A if y & 1 else 0)
            y = (mt[N - 1] & MASCARA_ALTA) | (mt[0] & MASCARA_BAJA)
            mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ (MATRIZ_A if y & 1 else 0)
            self.mti = 0

        y = mt[self.mti]
        self.mti += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y &= 0xFFFFFFFF
        y ^= y >> 18
        return y * DOS_A_LA_MENOS_32

    def unif(self) -> float:
        """unif_rand() de R: un real en (0, 1), nunca los extremos."""
        return fixup(self._genrand())

    def _rbits(self, bits: int) -> int:
        """rbits de R: un entero de `bits` bits armado con tandas de 16.

        El bucle va de 0 a `bits` INCLUSIVE en pasos de 16, así que con 16 bits
        justos hace dos tandas y no una. Es lo que R hace.
        """
        v = 0
        n = 0
        while n <= bits:
            v1 = int(self.unif() * 65536)
            v = 65536 * v + v1
            n += 16
        return v % (2 ** bits)

    def indice(self, dn: int) -> int:
        """R_unif_index: un entero uniforme en [0, dn), por rechazo."""
        if dn <= 0:
            return 0
        bits = math.ceil(math.log2(dn))
        while True:
            dv = self._rbits(bits)
            if dn > dv:
                return dv


def sample_int(generador: GeneradorR, n: int, tamano: int) -> list[int]:
    """`sample.int(n, tamano)` sin reposición, con el mismo resultado que R.

    Devuelve las posiciones en el ORDEN EN QUE SALEN, empezando en 1, que es
    lo que devuelve R. Ordenarlas es cosa de quien llama.

    Es el camino de `do_sample`: un Fisher-Yates parcial que trae el último
    elemento al hueco del elegido. R tiene un segundo camino para poblaciones
    de más de diez millones, que este proyecto no necesita y no trae.
    """
    if not (n >= 0) or not (tamano >= 0) or tamano > n:
        raise SystemExit("no se puede sacar una muestra más grande que la población")
    if tamano == 0:
        return []
    if n > 10_000_000:
        raise SystemExit("con más de diez millones R cambia de algoritmo; "
                         "este proyecto no lo implementa")

    x = list(range(n))
    resto = n
    salida = []
    for _ in range(tamano):
        j = generador.indice(resto)
        salida.append(x[j] + 1)
        resto -= 1
        x[j] = x[resto]
    return salida

#!/usr/bin/env python
"""
Figuras de las entradas de gráficos del módulo de estadística descriptiva.

Las entradas que explican un tipo de gráfico tienen que mostrar ese gráfico.
Este script produce las cuatro que faltaban, a partir de las tablas que ya
calculó `preparar-tablas-m02.py` sobre el microdato de la EPH:

    src/figuras/nivel-educativo-barras.svg     barras horizontales ordinales
    src/figuras/nivel-educativo-sectores.svg   torta de tres porciones
    src/figuras/edades-poligono.svg            histograma con el polígono
    src/figuras/edades-ojiva.svg               acumulada y lectura de la mediana

No lee el microdato: toma `datos/eph/tablas-m02.json`, así que se vuelve a
correr sin el ZIP del INDEC a mano.

    python datos/eph/generar-figuras-m02.py

Los SVG no llevan colores propios: usan las clases de `.grafico` del sitio
—barra, curva, guia, eje, media, rotulo—, que se resuelven con las variables
CSS y por eso funcionan igual en tema claro y oscuro.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TABLAS = Path(__file__).resolve().parent / "tablas-m02.json"
SALIDA = RAIZ / "src" / "figuras"

AN = 720  # ancho del lienzo, igual que el resto de las figuras del sitio


def encabezado(alto: int, etiqueta: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {alto}" '
        f'class="grafico" role="img" aria-label="{etiqueta}">'
    ]


def guardar(nombre: str, partes: list[str]) -> None:
    partes.append("</svg>")
    destino = SALIDA / f"{nombre}.svg"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"  {destino.relative_to(RAIZ)}")


def n(x: float) -> str:
    """Coordenada SVG: punto decimal, que es la sintaxis del formato."""
    return f"{x:.1f}".rstrip("0").rstrip(".")


def cifra(x: float, decimales: int = 1) -> str:
    """Número visible: coma decimal, que es la convención en castellano."""
    return f"{x:.{decimales}f}".replace(".", ",")


def miles(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# --- 1 · Barras horizontales -------------------------------------------------


def barras(tabla: dict) -> None:
    filas = tabla["filas"]
    alto = 40 + len(filas) * 34 + 46
    izq, der = 178, 660          # el eje arranca después de las etiquetas
    maximo = max(f["pi"] for f in filas)
    escala = (der - izq) / (maximo * 1.12)

    p = encabezado(alto, "Gráfico de barras del nivel educativo de las personas ocupadas")

    # guías verticales cada 10 %
    marca = 0
    while marca <= maximo * 1.1:
        x = izq + marca * escala
        p.append(f'<line class="guia" x1="{n(x)}" y1="30" x2="{n(x)}" y2="{alto - 44}"/>')
        p.append(f'<text class="rotulo-chico" x="{n(x)}" y="{alto - 28}" '
                 f'text-anchor="middle">{marca} %</text>')
        marca += 10

    for i, f in enumerate(filas):
        y = 40 + i * 34
        largo = f["pi"] * escala
        p.append(f'<rect class="barra" x="{izq}" y="{y}" '
                 f'width="{n(largo)}" height="22"/>')
        p.append(f'<text class="rotulo-chico" x="{izq - 10}" y="{y + 16}" '
                 f'text-anchor="end">{f["etiqueta"]}</text>')
        p.append(f'<text class="rotulo-chico" x="{n(izq + largo + 8)}" y="{y + 16}">'
                 f'{cifra(f["pi"])} %</text>')

    p.append(f'<line class="eje" x1="{izq}" y1="{alto - 44}" x2="{der}" y2="{alto - 44}"/>')
    p.append(f'<text class="rotulo" x="{(izq + der) / 2:.0f}" y="{alto - 8}" '
             f'text-anchor="middle">Porcentaje de personas ocupadas</text>')
    guardar("nivel-educativo-barras", p)


# --- 2 · Sectores ------------------------------------------------------------


def sectores(tabla: dict) -> None:
    """Las siete categorías agrupadas en tres, que es cuando la torta funciona."""
    filas = tabla["filas"]
    grupos = [
        ("Hasta primario completo", sum(f["pi"] for f in filas[:3]), 1.0),
        ("Secundario", sum(f["pi"] for f in filas[3:5]), 0.62),
        ("Superior", sum(f["pi"] for f in filas[5:]), 0.3),
    ]
    alto = 340
    cx, cy, r = 250, 170, 118

    p = encabezado(alto, "Gráfico de sectores del nivel educativo agrupado en tres categorías")

    angulo = -90.0  # arranca a las 12 en punto
    for etiqueta, pct, opacidad in grupos:
        barrido = pct / 100 * 360
        fin = angulo + barrido
        x1 = cx + r * math.cos(math.radians(angulo))
        y1 = cy + r * math.sin(math.radians(angulo))
        x2 = cx + r * math.cos(math.radians(fin))
        y2 = cy + r * math.sin(math.radians(fin))
        grande = 1 if barrido > 180 else 0
        p.append(
            f'<path class="barra" fill-opacity="{opacidad}" '
            f'd="M {cx} {cy} L {n(x1)} {n(y1)} '
            f'A {r} {r} 0 {grande} 1 {n(x2)} {n(y2)} Z"/>'
        )
        # porcentaje sobre la porción
        medio = math.radians(angulo + barrido / 2)
        p.append(f'<text class="rotulo" x="{n(cx + 0.62 * r * math.cos(medio))}" '
                 f'y="{n(cy + 0.62 * r * math.sin(medio) + 5)}" '
                 f'text-anchor="middle">{cifra(pct)} %</text>')
        angulo = fin

    # referencias al costado, en vez de leyenda suelta
    y = 118
    for etiqueta, pct, opacidad in grupos:
        p.append(f'<rect class="barra" fill-opacity="{opacidad}" x="416" y="{y - 12}" '
                 f'width="16" height="16"/>')
        p.append(f'<text class="rotulo" x="442" y="{y}">{etiqueta}</text>')
        y += 34

    p.append('<text class="rotulo-chico" x="416" y="238">Personas ocupadas, 1T 2026</text>')
    guardar("nivel-educativo-sectores", p)


# --- 3 · Polígono de frecuencias --------------------------------------------


def poligono(tabla: dict) -> None:
    filas = tabla["filas"]
    ancho_clase = 10
    alto, izq, der, base, techo = 340, 56, 698, 288, 30
    marcas = [f["marca"] for f in filas]
    # se agregan las dos clases de frecuencia cero que cierran la figura
    puntos = ([(marcas[0] - ancho_clase, 0.0)]
              + [(f["marca"], f["pi"]) for f in filas]
              + [(marcas[-1] + ancho_clase, 0.0)])
    xmin, xmax = puntos[0][0], puntos[-1][0]
    ymax = max(pi for _, pi in puntos) * 1.15

    def px(v: float) -> float:
        return izq + (v - xmin) / (xmax - xmin) * (der - izq)

    def py(v: float) -> float:
        return base - v / ymax * (base - techo)

    p = encabezado(alto, "Polígono de frecuencias de la edad de las personas ocupadas")

    for marca in range(0, 26, 5):
        y = py(marca)
        p.append(f'<line class="guia" x1="{izq}" y1="{n(y)}" x2="{der}" y2="{n(y)}"/>')
        p.append(f'<text class="rotulo-chico" x="{izq - 8}" y="{n(y + 4)}" '
                 f'text-anchor="end">{marca} %</text>')

    # el histograma de fondo, para que se vea que el polígono lo reemplaza
    for f in filas:
        x = px(f["marca"] - ancho_clase / 2)
        w = px(f["marca"] + ancho_clase / 2) - x
        y = py(f["pi"])
        p.append(f'<rect class="barra" fill-opacity="0.28" x="{n(x)}" y="{n(y)}" '
                 f'width="{n(w)}" height="{n(base - y)}"/>')

    linea = " ".join(f"{n(px(x))},{n(py(y))}" for x, y in puntos)
    p.append(f'<polyline class="curva" points="{linea}"/>')
    for x, y in puntos:
        p.append(f'<circle class="barra" cx="{n(px(x))}" cy="{n(py(y))}" r="4"/>')

    p.append(f'<line class="eje" x1="{izq}" y1="{base}" x2="{der}" y2="{base}"/>')
    for x, _ in puntos:
        p.append(f'<text class="rotulo-chico" x="{n(px(x))}" y="{base + 20}" '
                 f'text-anchor="middle">{x:.0f}</text>')
    p.append(f'<text class="rotulo" x="{(izq + der) // 2}" y="{base + 44}" '
             f'text-anchor="middle">Edad (marca de clase de cada intervalo)</text>')
    guardar("edades-poligono", p)


# --- 4 · Ojiva ---------------------------------------------------------------


def ojiva(tabla: dict) -> None:
    filas = tabla["filas"]
    alto, izq, der, base, techo = 340, 56, 698, 282, 34
    limites = [tabla["minimo"]] + [f["marca"] + 5 for f in filas]
    acumuladas = [0.0] + [f["Pi"] for f in filas]
    xmin, xmax = limites[0], limites[-1]

    def px(v: float) -> float:
        return izq + (v - xmin) / (xmax - xmin) * (der - izq)

    def py(v: float) -> float:
        return base - v / 100 * (base - techo)

    p = encabezado(alto, "Ojiva de la edad de las personas ocupadas")

    for marca in range(0, 101, 25):
        y = py(marca)
        p.append(f'<line class="guia" x1="{izq}" y1="{n(y)}" x2="{der}" y2="{n(y)}"/>')
        p.append(f'<text class="rotulo-chico" x="{izq - 8}" y="{n(y + 4)}" '
                 f'text-anchor="end">{marca} %</text>')

    linea = " ".join(f"{n(px(x))},{n(py(y))}" for x, y in zip(limites, acumuladas))
    p.append(f'<polyline class="curva" points="{linea}"/>')
    for x, y in zip(limites, acumuladas):
        p.append(f'<circle class="barra" cx="{n(px(x))}" cy="{n(py(y))}" r="4"/>')

    # la lectura de la mediana: se entra por el 50 % y se baja
    mediana = None
    for (x0, y0), (x1, y1) in zip(list(zip(limites, acumuladas)),
                                  list(zip(limites, acumuladas))[1:]):
        if y0 < 50 <= y1:
            mediana = x0 + (50 - y0) / (y1 - y0) * (x1 - x0)
            break
    if mediana is not None:
        p.append(f'<line class="media" x1="{izq}" y1="{n(py(50))}" '
                 f'x2="{n(px(mediana))}" y2="{n(py(50))}"/>')
        p.append(f'<line class="media" x1="{n(px(mediana))}" y1="{n(py(50))}" '
                 f'x2="{n(px(mediana))}" y2="{base}"/>')
        p.append(f'<text class="rotulo-media" x="{n(px(mediana) + 8)}" '
                 f'y="{n(py(50) - 8)}">Mediana ≈ {cifra(mediana)} años</text>')

    p.append(f'<line class="eje" x1="{izq}" y1="{base}" x2="{der}" y2="{base}"/>')
    for x in limites:
        p.append(f'<text class="rotulo-chico" x="{n(px(x))}" y="{base + 20}" '
                 f'text-anchor="middle">{x:.0f}</text>')
    p.append(f'<text class="rotulo" x="{(izq + der) // 2}" y="{base + 44}" '
             f'text-anchor="middle">Edad (límite superior de cada intervalo)</text>')
    guardar("edades-ojiva", p)


def main() -> None:
    tablas = json.loads(TABLAS.read_text(encoding="utf-8"))
    print("figuras de los gráficos del módulo descriptiva:")
    barras(tablas["nivel_educativo"])
    sectores(tablas["nivel_educativo"])
    poligono(tablas["edades_agrupadas"])
    ojiva(tablas["edades_agrupadas"])


if __name__ == "__main__":
    main()

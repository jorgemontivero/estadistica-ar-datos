#!/usr/bin/env python
"""
Mapas de coropletas para la entrada del módulo de estadística descriptiva.

Dibuja la tasa de mortalidad infantil por provincia sobre la geometría del
IGN, y produce dos figuras:

    src/figuras/mapa-tmi-provincias.svg   el mapa, con cortes redondos
    src/figuras/mapa-tmi-cortes.svg       el mismo dato con dos criterios
                                          de corte distintos, lado a lado

La segunda es el argumento central de la entrada: con los mismos números y
dos reglas de clasificación igual de defendibles, el mapa cambia de cara.

    python datos/demografia/generar-mapas-m02.py

La geometría se simplifica acá mismo con Douglas-Peucker para que el SVG pese
unas decenas de kilobytes en vez de un megabyte; no hay dependencias fuera de
la biblioteca estándar. Los colores salen de las clases `.grafico` del sitio.
"""

from __future__ import annotations

import os

import json
import math
import unicodedata
from pathlib import Path


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "src" / "figuras"
TASAS = Path(__file__).resolve().parent / "tasas-m05.json"

GEOMETRIA = Path(
    DATOS + r"\Infraestructura_territorio"
    r"\servicio-de-normalizacion-de-direcciones-y-unidades-territoriales-de-argentina"
    r"\Provincias_GeoJSON.geojson"
)

# El sector antártico y las islas del Atlántico Sur entran en la geometría de
# Tierra del Fuego y estirarían el mapa hasta hacerlo ilegible. Se recorta al
# continente y se declara en el pie de la figura.
LIMITE_SUR = -56.0
LIMITE_OESTE = -74.0
LIMITE_ESTE = -53.0

TOLERANCIA = 0.02  # grados; simplificación de los contornos

EQUIVALENCIAS = {
    "ciudadautonomadebuenosaires": "caba",
    "tierradelfuegoantartidaeislasdelatlanticosur": "tierradelfuego",
}


def clave(nombre: str) -> str:
    s = unicodedata.normalize("NFKD", nombre.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c for c in s if c.isalnum())
    return EQUIVALENCIAS.get(s, s)


# --- geometría ---------------------------------------------------------------


def simplificar(puntos: list, tol: float) -> list:
    """Douglas-Peucker: conserva la forma y tira los vértices que no aportan."""
    if len(puntos) < 3:
        return puntos
    (x1, y1), (x2, y2) = puntos[0], puntos[-1]
    dx, dy = x2 - x1, y2 - y1
    norma = math.hypot(dx, dy)
    peor, indice = 0.0, 0
    for i, (x, y) in enumerate(puntos[1:-1], 1):
        if norma == 0:
            d = math.hypot(x - x1, y - y1)
        else:
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norma
        if d > peor:
            peor, indice = d, i
    if peor <= tol:
        return [puntos[0], puntos[-1]]
    return simplificar(puntos[: indice + 1], tol)[:-1] + simplificar(puntos[indice:], tol)


def anillos(geom: dict) -> list:
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [anillo for poly in geom["coordinates"] for anillo in poly]


def preparar(features: list) -> dict:
    """Simplifica, recorta al continente y devuelve los anillos por provincia."""
    salida = {}
    for f in features:
        piezas = []
        for anillo in anillos(f["geometry"]):
            puntos = [(lon, lat) for lon, lat in anillo
                      if LIMITE_OESTE <= lon <= LIMITE_ESTE and lat >= LIMITE_SUR]
            if len(puntos) < 4:
                continue
            simple = simplificar(puntos, TOLERANCIA)
            if len(simple) >= 4:
                piezas.append(simple)
        if piezas:
            salida[clave(f["properties"]["nombre"])] = {
                "nombre": f["properties"]["nombre"],
                "piezas": piezas,
            }
    return salida


def proyector(provincias: dict, ancho: float, alto: float, x0: float, y0: float):
    """Equirrectangular con corrección por la latitud media: alcanza y no miente."""
    todos = [p for prov in provincias.values() for pieza in prov["piezas"] for p in pieza]
    lons = [lon for lon, _ in todos]
    lats = [lat for _, lat in todos]
    lat_media = (min(lats) + max(lats)) / 2
    k = math.cos(math.radians(lat_media))
    ancho_geo = (max(lons) - min(lons)) * k
    alto_geo = max(lats) - min(lats)
    escala = min(ancho / ancho_geo, alto / alto_geo)

    def proyectar(lon: float, lat: float) -> tuple[float, float]:
        x = x0 + (lon - min(lons)) * k * escala + (ancho - ancho_geo * escala) / 2
        y = y0 + (max(lats) - lat) * escala + (alto - alto_geo * escala) / 2
        return x, y

    return proyectar


def camino(prov: dict, proyectar) -> str:
    partes = []
    for pieza in prov["piezas"]:
        d = " ".join(
            f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}"
            for i, (x, y) in enumerate(proyectar(lon, lat) for lon, lat in pieza)
        )
        partes.append(d + " Z")
    return " ".join(partes)


# --- clasificación -----------------------------------------------------------

OPACIDADES = [0.16, 0.34, 0.54, 0.74, 0.95]


def clase(valor: float, cortes: list[float]) -> int:
    for i, c in enumerate(cortes):
        if valor < c:
            return i
    return len(cortes)


def cuantiles(valores: list[float], k: int) -> list[float]:
    orden = sorted(valores)
    return [orden[round(i * len(orden) / k)] for i in range(1, k)]


def cifra(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


# --- figuras -----------------------------------------------------------------


def leyenda(p: list, x: float, y: float, cortes: list[float], titulo: str) -> None:
    p.append(f'<text class="rotulo" x="{x}" y="{y - 14}">{titulo}</text>')
    etiquetas = ([f"menos de {cifra(cortes[0])}"]
                 + [f"{cifra(cortes[i])} a {cifra(cortes[i + 1])}" for i in range(len(cortes) - 1)]
                 + [f"{cifra(cortes[-1])} o más"])
    for i, etiqueta in enumerate(etiquetas):
        yy = y + i * 22
        p.append(f'<rect class="barra" fill-opacity="{OPACIDADES[i]}" '
                 f'x="{x}" y="{yy}" width="18" height="14"/>')
        p.append(f'<text class="rotulo-chico" x="{x + 26}" y="{yy + 12}">{etiqueta}</text>')


def mapa_principal(provincias: dict, tmi: dict) -> None:
    AN, AL = 720, 560
    cortes = [6.0, 8.0, 10.0, 12.0]
    proyectar = proyector(provincias, 300, 520, 20, 20)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="Mapa de la tasa de mortalidad '
         f'infantil por provincia, Argentina 2024">']

    for k, prov in sorted(provincias.items()):
        valor = tmi.get(k)
        if valor is None:
            continue
        op = OPACIDADES[clase(valor, cortes)]
        p.append(f'<path class="barra" fill-opacity="{op}" stroke="var(--papel)" '
                 f'stroke-width="0.6" d="{camino(prov, proyectar)}">'
                 f'<title>{prov["nombre"]} · {cifra(valor)}</title></path>')

    leyenda(p, 380, 150, cortes,
            "Muertes de menores de 1 año por cada 1.000 nacidos vivos")

    extremos = sorted(((v, k) for k, v in tmi.items()
                       if k in provincias), reverse=True)[:3]
    p.append('<text class="rotulo" x="380" y="300">Las tres tasas más altas</text>')
    for i, (v, k) in enumerate(extremos):
        p.append(f'<text class="rotulo-chico" x="380" y="{324 + i * 20}">'
                 f'{provincias[k]["nombre"]} · {cifra(v)}</text>')
    if "argentina" in tmi:
        p.append(f'<text class="rotulo-chico" x="380" y="{404}">'
                 f'Total del país · {cifra(tmi["argentina"])}</text>')

    p.append("</svg>")
    (SALIDA / "mapa-tmi-provincias.svg").write_text("\n".join(p) + "\n", encoding="utf-8")
    print("  src/figuras/mapa-tmi-provincias.svg")


def mapa_cortes(provincias: dict, tmi: dict) -> None:
    """El mismo dato, dos criterios de corte: la comparación que importa."""
    AN, AL = 720, 470
    valores = [v for k, v in tmi.items() if k in provincias]
    lo, hi = min(valores), max(valores)
    iguales = [lo + (hi - lo) * i / 5 for i in range(1, 5)]
    quintiles = cuantiles(valores, 5)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {AN} {AL}" '
         f'class="grafico" role="img" aria-label="El mismo mapa con dos criterios '
         f'de corte: intervalos iguales y quintiles">']

    for panel, (titulo, cortes, x0) in enumerate([
        ("Intervalos de igual amplitud", iguales, 10),
        ("Quintiles: mismo número de provincias", quintiles, 370),
    ]):
        proyectar = proyector(provincias, 200, 330, x0 + 60, 40)
        p.append(f'<text class="rotulo" x="{x0 + 160}" y="26" '
                 f'text-anchor="middle">{titulo}</text>')
        for k, prov in sorted(provincias.items()):
            valor = tmi.get(k)
            if valor is None:
                continue
            op = OPACIDADES[clase(valor, cortes)]
            p.append(f'<path class="barra" fill-opacity="{op}" stroke="var(--papel)" '
                     f'stroke-width="0.6" d="{camino(prov, proyectar)}">'
                     f'<title>{prov["nombre"]} · {cifra(valor)}</title></path>')
        etiqueta = " · ".join(cifra(c) for c in cortes)
        p.append(f'<text class="rotulo-chico" x="{x0 + 160}" y="406" '
                 f'text-anchor="middle">Cortes: {etiqueta}</text>')

    p.append('<text class="rotulo-chico" x="360" y="446" text-anchor="middle">'
             'Los mismos 24 valores, dos reglas de clasificación.</text>')
    p.append("</svg>")
    (SALIDA / "mapa-tmi-cortes.svg").write_text("\n".join(p) + "\n", encoding="utf-8")
    print("  src/figuras/mapa-tmi-cortes.svg")


def main() -> None:
    geo = json.loads(GEOMETRIA.read_text(encoding="utf-8"))
    provincias = preparar(geo["features"])
    tasas = json.loads(TASAS.read_text(encoding="utf-8"))
    tmi = tasas["deis"]["tmi_por_provincia"]

    faltan = [k for k in provincias if k not in tmi]
    if faltan:
        raise SystemExit(f"sin dato de TMI: {faltan}")

    print(f"mapas: {len(provincias)} provincias, "
          f"{sum(len(pz) for p in provincias.values() for pz in p['piezas'])} puntos")
    mapa_principal(provincias, tmi)
    mapa_cortes(provincias, tmi)


if __name__ == "__main__":
    main()

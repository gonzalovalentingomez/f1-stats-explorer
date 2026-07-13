"""Módulo propio para consumir la API pública Jolpica-F1.

Este módulo se encarga exclusivamente de obtener datos crudos de resultados
de carreras de Fórmula 1 (temporada completa), ya sea desde la API o desde
una caché local en disco. No realiza ningún cálculo estadístico: esa
responsabilidad es del módulo `analisis.py` (separación de responsabilidades).

Fuente de datos: Jolpica-F1 (https://github.com/jolpica/jolpica-f1),
sucesora comunitaria de la API Ergast.
"""

import json
from pathlib import Path

import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(__file__).parent / "data_cache"
TIMEOUT_SEGUNDOS = 15
MAXIMO_PAGINAS = 20  # tope de seguridad para evitar bucles infinitos


class TemporadaInvalidaError(Exception):
    """Se lanza cuando la temporada solicitada no tiene datos disponibles."""


class ErrorDeConexionError(Exception):
    """Se lanza cuando no se puede contactar a la API y tampoco hay caché."""


def _ruta_cache(clave: str) -> Path:
    """Devuelve la ruta del archivo de caché para una clave dada."""
    return CACHE_DIR / f"{clave}.json"


def _guardar_en_cache(clave: str, carreras: list) -> None:
    """Guarda una lista de carreras en un archivo JSON local.

    Args:
        clave: Identificador del contenido cacheado (ej: "2021" o
            "2021_sprint").
        carreras: Lista de carreras a guardar.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    with open(_ruta_cache(clave), "w", encoding="utf-8") as archivo:
        json.dump(carreras, archivo, ensure_ascii=False, indent=2)


def _leer_de_cache(clave: str) -> list | None:
    """Lee una lista de carreras desde caché, si existe.

    Returns:
        La lista de carreras si hay caché válida, o None si no existe.
    """
    ruta = _ruta_cache(clave)
    if not ruta.exists():
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (json.JSONDecodeError, OSError):
        # Caché corrupta: se ignora y se vuelve a pedir a la API.
        return None


def _pedir_pagina(url: str) -> dict:
    """Hace un único pedido HTTP a la API y devuelve el JSON parseado.

    Función separada para poder reusarla en el bucle de paginación sin
    repetir el manejo de errores.

    Raises:
        ErrorDeConexionError: ante timeout, error de conexión o HTTP.
    """
    try:
        respuesta = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
    except requests.exceptions.Timeout as error:
        raise ErrorDeConexionError(
            "La API tardó demasiado en responder. Probá de nuevo en un momento."
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise ErrorDeConexionError(
            "No se pudo conectar a la API. Verificá tu conexión a internet."
        ) from error
    except requests.exceptions.HTTPError as error:
        raise ErrorDeConexionError(
            f"La API respondió con un error: {error}"
        ) from error

    return respuesta.json()


def _fusionar_carreras(
    carreras_acumuladas: dict, carreras_nuevas: list, clave_resultados: str
) -> None:
    """Agrega carreras nuevas al diccionario acumulado, fusionando por ronda.

    La API pagina por cantidad de RESULTADOS, no de carreras, así que una
    misma carrera puede llegar partida en dos páginas distintas. Por eso
    se acumula en un diccionario indexado por número de ronda y se
    concatenan los resultados en vez de sobreescribirlos.

    Args:
        carreras_acumuladas: Diccionario {ronda: carrera} que se modifica
            in-place.
        carreras_nuevas: Lista de carreras devuelta por una página de la API.
        clave_resultados: Nombre de la lista de resultados dentro de cada
            carrera ("Results" para carreras normales, "SprintResults"
            para sprints).
    """
    for carrera in carreras_nuevas:
        ronda = carrera["round"]
        if ronda in carreras_acumuladas:
            carreras_acumuladas[ronda][clave_resultados].extend(
                carrera[clave_resultados]
            )
        else:
            carreras_acumuladas[ronda] = carrera


def _obtener_recurso_paginado(temporada: int, endpoint: str, clave_resultados: str) -> list:
    """Descarga y pagina un recurso de la API Jolpica-F1 para una temporada.

    La API Jolpica-F1 limita cada respuesta a un máximo real de resultados
    por pedido (documentado hasta 1000, pero en la práctica el servidor
    puede devolver menos, por ejemplo 100) sin importar el `limit` que se
    pida. Por eso esta función pagina automáticamente usando el campo
    `offset` hasta juntar el total indicado por la propia API
    (`MRData.total`).

    Args:
        temporada: Año de la temporada a consultar (ej: 2021).
        endpoint: Recurso de la API ("results" o "sprint").
        clave_resultados: Nombre de la lista de resultados dentro de cada
            carrera ("Results" o "SprintResults").

    Returns:
        Lista de carreras (con sus resultados ya completos), ordenada por
        número de ronda. Lista vacía si la temporada no tiene datos para
        ese recurso (por ejemplo, una temporada sin carreras sprint).

    Raises:
        ErrorDeConexionError: si falla la conexión.
    """
    carreras_acumuladas: dict = {}
    offset = 0
    total = 0

    for _ in range(MAXIMO_PAGINAS):
        url = f"{BASE_URL}/{temporada}/{endpoint}/?limit=100&offset={offset}"
        datos = _pedir_pagina(url)

        try:
            carreras_pagina = datos["MRData"]["RaceTable"]["Races"]
            total = int(datos["MRData"]["total"])
            limite_usado = int(datos["MRData"]["limit"])
        except (KeyError, ValueError) as error:
            raise TemporadaInvalidaError(
                f"La respuesta de la API no tiene el formato esperado: {error}"
            ) from error

        _fusionar_carreras(carreras_acumuladas, carreras_pagina, clave_resultados)

        offset += limite_usado
        if offset >= total or limite_usado == 0:
            break

    return [carreras_acumuladas[r] for r in sorted(carreras_acumuladas, key=int)]


def obtener_resultados_temporada(temporada: int, usar_cache: bool = True) -> list:
    """Obtiene los resultados de todas las carreras de una temporada de F1.

    Primero intenta leer de la caché local (si `usar_cache` es True y existe).
    Si no hay caché, consulta la API Jolpica-F1 (paginando automáticamente)
    y guarda el resultado para la próxima vez.

    Args:
        temporada: Año de la temporada a consultar (ej: 2021).
        usar_cache: Si es False, fuerza a pedir los datos siempre a la API.

    Returns:
        Lista de diccionarios, cada uno representando una carrera con sus
        resultados, ordenada por número de ronda.

    Raises:
        TemporadaInvalidaError: si la temporada no existe o no tiene carreras.
        ErrorDeConexionError: si falla la conexión y no hay caché disponible.
    """
    clave = str(temporada)
    if usar_cache:
        datos_cacheados = _leer_de_cache(clave)
        if datos_cacheados is not None:
            return datos_cacheados

    carreras = _obtener_recurso_paginado(temporada, "results", "Results")

    if not carreras:
        raise TemporadaInvalidaError(
            f"No se encontraron carreras para la temporada {temporada}. "
            "Verificá que el año sea correcto (F1 corre desde 1950)."
        )

    _guardar_en_cache(clave, carreras)
    return carreras


def obtener_resultados_sprint_temporada(temporada: int, usar_cache: bool = True) -> list:
    """Obtiene los resultados de las carreras sprint de una temporada (si las tuvo).

    El formato sprint se introdujo recién en 2021, así que la mayoría de las
    temporadas no tienen ninguna: en ese caso esta función devuelve una
    lista vacía en vez de lanzar una excepción, porque no tener sprints es
    un estado normal, no un error.

    Args:
        temporada: Año de la temporada a consultar (ej: 2021).
        usar_cache: Si es False, fuerza a pedir los datos siempre a la API.

    Returns:
        Lista de carreras sprint con sus resultados (puede estar vacía).

    Raises:
        ErrorDeConexionError: si falla la conexión y no hay caché disponible.
    """
    clave = f"{temporada}_sprint"
    if usar_cache:
        datos_cacheados = _leer_de_cache(clave)
        if datos_cacheados is not None:
            return datos_cacheados

    carreras_sprint = _obtener_recurso_paginado(temporada, "sprint", "SprintResults")
    _guardar_en_cache(clave, carreras_sprint)
    return carreras_sprint

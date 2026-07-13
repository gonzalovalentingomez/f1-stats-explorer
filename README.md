# 🏎️ F1 Stats Explorer

Aplicación web para explorar estadísticas de temporadas históricas de Fórmula 1: puntos, victorias, podios, posición promedio y porcentaje de carreras terminadas por piloto. Los datos son reales y se obtienen en el momento desde la API pública [Jolpica-F1](https://github.com/jolpica/jolpica-f1).

Proyecto final de la materia **Programación 1** — Tecnicatura en Ciencia de Datos e Integración con IA (ISTEA).

## ¿Qué hace?

1. El usuario elige una temporada (por ejemplo, 2021).
2. El programa consulta la API y trae los resultados de todas las carreras de esa temporada.
3. Calcula estadísticas por piloto: puntos totales, victorias, podios, posición promedio y % de carreras terminadas.
4. Muestra todo en tablas y gráficos interactivos, con la posibilidad de comparar varios pilotos entre sí y descargar los resultados en CSV.

## Cómo ejecutarlo

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd f1_stats_explorer

# 2. Crear y activar un entorno virtual
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
streamlit run app.py
```

Esto abre la aplicación en el navegador, normalmente en `http://localhost:8501`.

## Estructura del proyecto

```
f1_stats_explorer/
├── app.py              # Interfaz de usuario (Streamlit)
├── api_f1.py            # Módulo propio: conexión a la API Jolpica-F1 + caché local
├── analisis.py           # Módulo propio: procesamiento de datos con pandas
├── tests/
│   └── test_analisis.py  # Pruebas del módulo de análisis
├── requirements.txt
├── .gitignore
└── README.md
```

## Librerías externas utilizadas

| Librería | Para qué se usa |
|---|---|
| `requests` | Consumir la API Jolpica-F1 (peticiones HTTP) |
| `pandas` | Transformar el JSON anidado en tablas y calcular estadísticas |
| `streamlit` | Construir la interfaz web sin escribir HTML/CSS |

## Módulos propios

- **`api_f1.py`**: obtiene los resultados crudos de una temporada. Si ya se consultó esa temporada antes, los lee de una caché local en `data_cache/` en vez de volver a pedirlos a la API (más rápido y funciona aunque falle la conexión momentáneamente). Maneja errores de conexión, timeouts y temporadas inválidas con excepciones propias (`ErrorDeConexionError`, `TemporadaInvalidaError`).
- **`analisis.py`**: convierte los datos crudos en un DataFrame de pandas y calcula las estadísticas por piloto. No sabe nada de la API ni de la interfaz — solo recibe datos y devuelve datos, lo que lo hace fácil de probar por separado (ver `tests/test_analisis.py`).

## Decisiones de diseño

- **Separación en 3 módulos** (conexión / análisis / interfaz): cada uno tiene una única responsabilidad, lo que permite probar `analisis.py` sin necesidad de conexión a internet, y cambiar la interfaz en el futuro sin tocar la lógica de datos.
- **Caché en archivo local**: evita golpear la API innecesariamente y hace la app más robusta ante caídas de conexión temporales.
- **Excepciones propias** (`TemporadaInvalidaError`, `ErrorDeConexionError`) en vez de dejar pasar las excepciones genéricas de `requests`, para que el resto del código (y la interfaz) pueda reaccionar de forma clara y mostrar mensajes de error entendibles para el usuario.
- **Paginación manual**: la API Jolpica-F1 limita cada respuesta a un máximo real de resultados (aunque se pida un `limit` más alto), así que una temporada completa (~440 resultados) no entra en un solo pedido. `api_f1.py` pagina automáticamente con `offset` hasta juntar el total que indica la propia API.
- **Puntos de sprint**: desde 2021 algunas temporadas tienen carreras sprint, que otorgan puntos extra por fuera de los resultados de carrera. Se consultan por separado (`obtener_resultados_sprint_temporada`) y se suman solo al total de puntos — victorias, podios y % de carreras terminadas siguen contando únicamente Grandes Premios, tal como lo hace la clasificación oficial.

## Fuente de datos

[Jolpica-F1](https://github.com/jolpica/jolpica-f1) — API pública y gratuita, sucesora comunitaria de la clásica API Ergast. No requiere registro ni API key.

## Autor

Gonzalo — Tecnicatura en Ciencia de Datos e Integración con IA, ISTEA (2026).

"""F1 Stats Explorer - Interfaz Streamlit.

Punto de entrada de la aplicación. Se encarga únicamente de la interfaz
(mostrar controles, tablas y gráficos); toda la lógica de conexión a la
API vive en `api_f1.py` y todo el cálculo de estadísticas vive en
`analisis.py`. Esta separación es la aplicación práctica de la
modularización pedida en la consigna.

Para ejecutar: streamlit run app.py
"""

import streamlit as st

import analisis
from api_f1 import (
    ErrorDeConexionError,
    TemporadaInvalidaError,
    obtener_resultados_sprint_temporada,
    obtener_resultados_temporada,
)

st.set_page_config(page_title="F1 Stats Explorer", page_icon="🏎️", layout="wide")

st.title("🏎️ F1 Stats Explorer")
st.caption(
    "Estadísticas de temporadas de Fórmula 1, usando datos reales de la API Jolpica-F1."
)

with st.sidebar:
    st.header("Configuración")
    temporada = st.number_input(
        "Temporada",
        min_value=1950,
        max_value=2026,
        value=2021,
        step=1,
    )
    buscar = st.button("Buscar temporada", type="primary")

if "tabla" not in st.session_state:
    st.session_state["tabla"] = None
    st.session_state["carreras"] = None
    st.session_state["carreras_sprint"] = None
    st.session_state["temporada_cargada"] = None

if buscar:
    with st.spinner(f"Consultando datos de la temporada {temporada}..."):
        try:
            carreras = obtener_resultados_temporada(int(temporada))
            st.session_state["carreras"] = carreras
            st.session_state["tabla"] = analisis.construir_tabla_resultados(carreras)
            st.session_state["carreras_sprint"] = obtener_resultados_sprint_temporada(
                int(temporada)
            )
            st.session_state["temporada_cargada"] = int(temporada)
        except TemporadaInvalidaError as error:
            st.error(f"⚠️ {error}")
        except ErrorDeConexionError as error:
            st.error(f"🔌 {error}")

tabla = st.session_state["tabla"]
carreras = st.session_state["carreras"]
carreras_sprint = st.session_state["carreras_sprint"]

if tabla is None:
    st.info(
        "👈 Elegí una temporada en el panel izquierdo y presioná "
        "**Buscar temporada** para arrancar."
    )
else:
    temporada_cargada = st.session_state["temporada_cargada"]
    st.success(f"Mostrando datos de la temporada {temporada_cargada}")
    if carreras_sprint:
        st.caption(
            f"ℹ️ Esta temporada tuvo {len(carreras_sprint)} carrera(s) sprint — "
            "sus puntos ya están sumados al total de cada piloto."
        )

    podio = analisis.podio_temporada(tabla, carreras_sprint)
    medallas = ["🥇", "🥈", "🥉"]

    st.subheader("🏆 Podio del campeonato")
    columnas_podio = st.columns(3)
    for columna, lugar, medalla in zip(columnas_podio, podio, medallas):
        with columna:
            st.metric(
                label=f"{medalla} {lugar['nombre']}",
                value=f"{lugar['puntos_totales']:.0f} pts",
                delta=f"{lugar['victorias']} victorias · {lugar['podios']} podios",
                delta_color="off",
            )

    st.divider()

    pilotos = analisis.listar_pilotos(tabla, carreras_sprint)

    st.subheader("Campeonato de pilotos (por puntos)")
    col_tabla, col_grafico = st.columns([1, 1])
    with col_tabla:
        st.dataframe(pilotos, use_container_width=True, hide_index=True)
    with col_grafico:
        st.bar_chart(pilotos.set_index("piloto")["puntos_totales"])

    st.divider()

    st.subheader("Comparar pilotos")
    opciones = dict(zip(pilotos["piloto"], pilotos["piloto_id"]))
    seleccionados = st.multiselect(
        "Elegí uno o más pilotos para comparar",
        options=list(opciones.keys()),
        default=list(opciones.keys())[: min(3, len(opciones))],
    )

    if seleccionados:
        ids_seleccionados = [opciones[nombre] for nombre in seleccionados]
        comparacion = analisis.comparar_pilotos(tabla, ids_seleccionados, carreras_sprint)
        st.dataframe(
            comparacion.rename(columns={
                "nombre": "Piloto",
                "puntos_totales": "Puntos",
                "victorias": "Victorias",
                "podios": "Podios",
                "posicion_promedio": "Posición prom.",
                "carreras_disputadas": "Carreras",
                "porcentaje_terminadas": "% Terminadas",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Seleccioná al menos un piloto para ver la comparación.")

    st.divider()

    col_calendario, col_cambios = st.columns(2)

    with col_calendario:
        st.subheader("📅 Calendario de la temporada")
        calendario = analisis.calendario_temporada(carreras)
        st.dataframe(
            calendario.rename(columns={
                "ronda": "Ronda",
                "gran_premio": "Gran Premio",
                "fecha": "Fecha",
                "circuito": "Circuito",
                "pais": "País",
            }),
            use_container_width=True,
            hide_index=True,
            height=300,
        )

    with col_cambios:
        st.subheader("🔄 Cambios de equipo")
        cambios = analisis.cambios_de_equipo(tabla)
        if cambios.empty:
            st.info("Ningún piloto cambió de equipo durante esta temporada.")
        else:
            st.dataframe(
                cambios.rename(columns={
                    "piloto": "Piloto",
                    "ronda": "Desde ronda",
                    "equipo_anterior": "Equipo anterior",
                    "equipo_nuevo": "Equipo nuevo",
                }),
                use_container_width=True,
                hide_index=True,
                height=300,
            )

    with st.expander("Ver tabla completa de resultados (todas las carreras)"):
        st.dataframe(tabla, use_container_width=True, hide_index=True)

    csv = tabla.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar resultados en CSV",
        data=csv,
        file_name=f"f1_resultados_{temporada_cargada}.csv",
        mime="text/csv",
    )

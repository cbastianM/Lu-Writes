import streamlit as st
import os, sys

st.set_page_config(page_title="Configuracion — Lu Writes", layout="wide")

MODELS = [
    "google/gemma-4-26b-a4b-it"
]
STYLE_DIR = os.path.join(os.path.dirname(__file__), "..", "estilos")
os.makedirs(STYLE_DIR, exist_ok=True)

st.title("Configuracion")
st.markdown("*Parametros globales de la sesion. Se aplican en Redaccion y Bibliografia.*")
st.divider()

st.subheader("API Key de OpenRouter")
openrouter_api_key = st.text_input(
    "Ingresa tu API Key de OpenRouter",
    value=st.session_state.get("openrouter_api_key", ""),
    type="password",
    placeholder="sk-or-v1-...",
    help="Cada usuario debe usar su propia API Key. No se comparte ni se almacena en el servidor.",
)

api_key_ok = bool(openrouter_api_key.strip())

if not api_key_ok:
    st.warning("Ingresa tu API Key de OpenRouter para poder redactar.")
else:
    st.success("API Key ingresada correctamente.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Modelo y precision")

    modelo = st.selectbox(
        "Modelo de lenguaje",
        MODELS,
        index=MODELS.index(st.session_state.get("modelo", MODELS[0]))
              if st.session_state.get("modelo") in MODELS else 0,
    )

    TEMP_OPTS = {
        "Preciso y conservador — 0.3": 0.3,
        "Equilibrado — 0.6": 0.6,
        "Fluido y natural — 0.8  (recomendado)": 0.8,
        "Muy creativo — 1.0": 1.0,
    }
    temp_label = st.selectbox(
        "Nivel de creatividad",
        list(TEMP_OPTS.keys()),
        index=list(TEMP_OPTS.keys()).index(st.session_state.get("temp_label", "Fluido y natural — 0.8  (recomendado)"))
              if st.session_state.get("temp_label") in TEMP_OPTS else 2,
    )
    temperatura = TEMP_OPTS[temp_label]

with col2:
    st.subheader("Escritura")

    LONG_OPTS = [
        "Corto  —  250 palabras",
        "Mediano  —  600 palabras",
        "Largo  —  1100 palabras",
    ]
    longitud = st.radio(
        "Longitud del texto generado",
        LONG_OPTS,
        index=LONG_OPTS.index(st.session_state.get("longitud", LONG_OPTS[1]))
              if st.session_state.get("longitud") in LONG_OPTS else 1,
    )

    archivos_md = [f for f in os.listdir(STYLE_DIR) if f.endswith(".md")]
    opciones = ["Ninguno"] + archivos_md
    actual = st.session_state.get("estilo_elegido", "Ninguno")
    estilo_elegido = st.selectbox(
        "Archivo de estilo de escritura (.md)",
        opciones,
        index=opciones.index(actual) if actual in opciones else 0,
    )
    if not archivos_md:
        st.caption("Agrega archivos .md en la carpeta estilos/ para personalizar el tono de redaccion.")

st.divider()

if st.button("Guardar configuracion", type="primary"):
    st.session_state.modelo        = modelo
    st.session_state.temperatura   = temperatura
    st.session_state.temp_label    = temp_label
    st.session_state.estilo_elegido = estilo_elegido
    st.session_state.longitud      = longitud
    st.session_state.openrouter_api_key = openrouter_api_key.strip()
    st.success("Configuracion guardada. Navega a Redaccion o Bibliografia.")

# Resumen activo
if st.session_state.get("modelo"):
    st.info(
        f"Modelo: {st.session_state.get('modelo','—')}  |  "
        f"Temperatura: {st.session_state.get('temperatura','—')}  |  "
        f"Longitud: {st.session_state.get('longitud','—')}  |  "
        f"Estilo: {st.session_state.get('estilo_elegido','Ninguno')}"
    )

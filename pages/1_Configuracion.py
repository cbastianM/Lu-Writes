import streamlit as st
import os, sys

st.set_page_config(page_title="Configuracion — Lu Writes", layout="wide")

MODELS = [
    "openrouter/free",
]

STYLE_DIR = os.path.join(os.path.dirname(__file__), "..", "estilos")
os.makedirs(STYLE_DIR, exist_ok=True)

# ── valores por defecto ──────────────────────────────────────────────────────
if "modelo" not in st.session_state:
    st.session_state.modelo = "openrouter/free"
if "temperatura" not in st.session_state:
    st.session_state.temperatura = 1.0
if "temp_label" not in st.session_state:
    st.session_state.temp_label = "Muy creativo — 1.0 (recomendado)"
if "doble_pasada" not in st.session_state:
    st.session_state.doble_pasada = True
if "longitud" not in st.session_state:
    st.session_state.longitud = "Mediano  —  300 palabras"
if "estilo_elegido" not in st.session_state:
    st.session_state.estilo_elegido = "academico_tecnico.md"

st.title("Configuracion")
st.markdown("*Parametros globales de la sesion. Se aplican en Redaccion y Bibliografia.*")
st.divider()

st.subheader("API Key de OpenRouter")
openrouter_api_key = st.text_input(
    "Ingresa tu API Key de OpenRouter",
    value=st.session_state.get("openrouter_api_key", ""),
    type="password",
    placeholder="sk-or-v1-...",
    help="Obten tu API Key gratuita en https://openrouter.ai/keys",
)

api_key_ok = bool(openrouter_api_key.strip())

if not api_key_ok:
    st.warning("Ingresa tu API Key de OpenRouter para poder redactar.")
else:
    st.success("API Key ingresada correctamente.")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Modelo y precision")

    modelo_actual = st.session_state.get("modelo", MODELS[0])
    idx_modelo = MODELS.index(modelo_actual) if modelo_actual in MODELS else 0
    modelo = st.selectbox("Modelo de lenguaje", MODELS, index=idx_modelo)

    TEMP_OPTS = {
        "Preciso y conservador — 0.3": 0.3,
        "Equilibrado — 0.6": 0.6,
        "Fluido y natural — 0.8": 0.8,
        "Muy creativo — 1.0 (recomendado)": 1.0,
    }
    temp_actual = st.session_state.get("temp_label", "Muy creativo — 1.0 (recomendado)")
    idx_temp = list(TEMP_OPTS.keys()).index(temp_actual) if temp_actual in TEMP_OPTS else 3
    temp_label = st.selectbox("Nivel de creatividad", list(TEMP_OPTS.keys()), index=idx_temp)
    temperatura = TEMP_OPTS[temp_label]

with col2:
    st.subheader("Escritura")

    LONG_OPTS = [
        "Corto  —  100 palabras",
        "Mediano  —  300 palabras",
        "Largo  —  500 palabras",
    ]
    long_actual = st.session_state.get("longitud", LONG_OPTS[1])
    idx_long = LONG_OPTS.index(long_actual) if long_actual in LONG_OPTS else 1
    longitud = st.radio("Longitud del texto generado", LONG_OPTS, index=idx_long)

    archivos_md = [f for f in os.listdir(STYLE_DIR) if f.endswith(".md")]
    opciones = archivos_md if archivos_md else ["academico_tecnico.md"]
    actual = st.session_state.get("estilo_elegido", "academico_tecnico.md")
    idx_estilo = opciones.index(actual) if actual in opciones else 0
    estilo_elegido = st.selectbox("Archivo de estilo de escritura (.md)", opciones, index=idx_estilo)
    st.caption("Estilo académico-técnico seleccionado por defecto.")

st.divider()

if st.button("Guardar configuracion", type="primary"):
    st.session_state.modelo = modelo
    st.session_state.temperatura = temperatura
    st.session_state.temp_label = temp_label
    st.session_state.estilo_elegido = estilo_elegido
    st.session_state.longitud = longitud
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

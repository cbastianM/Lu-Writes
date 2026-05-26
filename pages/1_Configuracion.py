import streamlit as st
from pathlib import Path

# ====================== CONFIG ======================

st.set_page_config(page_title="Configuracion — Lu Writes", layout="wide")

ROOT = Path(__file__).resolve().parent.parent
STYLE_DIR = ROOT / "estilos"
STYLE_DIR.mkdir(exist_ok=True)

MODELS = [
    "openrouter/free",
]

TEMP_OPTS = {
    "Preciso y conservador — 0.3": 0.3,
    "Equilibrado — 0.6": 0.6,
    "Fluido y natural — 0.8": 0.8,
    "Muy creativo — 1.0 (recomendado)": 1.0,
}

LONG_OPTS = [
    "Corto  —  100 palabras",
    "Mediano  —  300 palabras",
    "Largo  —  500 palabras",
]

DEFAULTS = {
    "modelo": MODELS[0],
    "temperatura": 1.0,
    "temp_label": "Muy creativo — 1.0 (recomendado)",
    "doble_pasada": True,
    "longitud": "Mediano  —  300 palabras",
    "estilo_elegido": "academico_tecnico.md",
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


# ====================== HELPERS ======================

def listar_estilos() -> list:
    archivos = sorted(f.name for f in STYLE_DIR.glob("*.md"))
    return archivos or ["academico_tecnico.md"]


# ====================== UI ======================

st.title("Configuracion")
st.markdown("*Parametros globales de la sesion. Se aplican en Redaccion y Bibliografia.*")
st.divider()

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Modelo y precision")

    modelo_actual = st.session_state.get("modelo", MODELS[0])
    idx_modelo = MODELS.index(modelo_actual) if modelo_actual in MODELS else 0
    modelo = st.selectbox("Modelo de lenguaje", MODELS, index=idx_modelo)

    temp_actual = st.session_state.get("temp_label", list(TEMP_OPTS)[-1])
    idx_temp = list(TEMP_OPTS).index(temp_actual) if temp_actual in TEMP_OPTS else len(TEMP_OPTS) - 1
    temp_label = st.selectbox("Nivel de creatividad", list(TEMP_OPTS), index=idx_temp)
    temperatura = TEMP_OPTS[temp_label]

with col2:
    st.subheader("Escritura")

    long_actual = st.session_state.get("longitud", LONG_OPTS[1])
    idx_long = LONG_OPTS.index(long_actual) if long_actual in LONG_OPTS else 1
    longitud = st.radio("Longitud del texto generado", LONG_OPTS, index=idx_long)

    opciones_estilo = listar_estilos()
    actual = st.session_state.get("estilo_elegido", "academico_tecnico.md")
    idx_estilo = opciones_estilo.index(actual) if actual in opciones_estilo else 0
    estilo_elegido = st.selectbox(
        "Archivo de estilo de escritura (.md)",
        opciones_estilo,
        index=idx_estilo,
    )
    st.caption("Estilo academico-tecnico seleccionado por defecto.")


st.divider()

if st.button("Guardar configuracion", type="primary"):
    st.session_state["modelo"] = modelo
    st.session_state["temperatura"] = temperatura
    st.session_state["temp_label"] = temp_label
    st.session_state["estilo_elegido"] = estilo_elegido
    st.session_state["longitud"] = longitud
    st.toast("Configuracion guardada.", icon="✅")
    st.success("Configuracion guardada. Navega a Redaccion o Bibliografia.")


# --- Resumen activo ---
st.info(
    f"**Modelo:** {st.session_state.get('modelo', '—')}  |  "
    f"**Temperatura:** {st.session_state.get('temperatura', '—')}  |  "
    f"**Longitud:** {st.session_state.get('longitud', '—')}  |  "
    f"**Estilo:** {st.session_state.get('estilo_elegido', 'Ninguno')}"
)

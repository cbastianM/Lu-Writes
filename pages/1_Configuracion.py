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

def api_key_en_secrets() -> bool:
    """True si OPENROUTER_API_KEY esta definida en .streamlit/secrets.toml."""
    try:
        return "OPENROUTER_API_KEY" in st.secrets and bool(st.secrets["OPENROUTER_API_KEY"])
    except Exception:
        return False


def listar_estilos() -> list:
    archivos = sorted(f.name for f in STYLE_DIR.glob("*.md"))
    return archivos or ["academico_tecnico.md"]


# ====================== UI ======================

st.title("Configuracion")
st.markdown("*Parametros globales de la sesion. Se aplican en Redaccion y Bibliografia.*")
st.divider()


# --- API KEY ---
st.subheader("API Key de OpenRouter")

api_key_desde_secrets = api_key_en_secrets()
openrouter_api_key = ""  # placeholder por si no se muestra el input

if api_key_desde_secrets:
    st.success("API Key cargada desde `.streamlit/secrets.toml` — no necesitas hacer nada mas.")
    with st.expander("Por que ya no aparece el campo?"):
        st.markdown(
            "La key se lee directamente desde `secrets.toml` (o desde "
            "*Settings → Secrets* en Streamlit Community Cloud).\n\n"
            "Para cambiarla, edita ese archivo. "
            "Esto evita exponerla en la UI y, si tienes "
            "`.streamlit/secrets.toml` en tu `.gitignore`, tampoco se sube al repo."
        )
else:
    st.caption(
        "No se encontro la key en `secrets.toml`. Puedes ingresarla aqui "
        "(se guarda solo en la sesion, no en disco)."
    )
    openrouter_api_key = st.text_input(
        "Ingresa tu API Key de OpenRouter",
        value=st.session_state.get("openrouter_api_key", ""),
        type="password",
        placeholder="sk-or-v1-...",
        help="Obten tu API Key gratuita en https://openrouter.ai/keys",
    )
    if openrouter_api_key.strip():
        st.success("API Key ingresada correctamente.")
    else:
        st.warning("Ingresa tu API Key de OpenRouter para poder redactar.")


# --- Parametros del modelo y de escritura ---
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
    if not api_key_desde_secrets:
        st.session_state["openrouter_api_key"] = openrouter_api_key.strip()
    st.toast("Configuracion guardada.", icon="✅")
    st.success("Configuracion guardada. Navega a Redaccion o Bibliografia.")


# --- Resumen activo ---
fuente_api = (
    "secrets.toml" if api_key_desde_secrets
    else ("sesion" if st.session_state.get("openrouter_api_key") else "no configurada")
)

st.info(
    f"**Modelo:** {st.session_state.get('modelo', '—')}  |  "
    f"**Temperatura:** {st.session_state.get('temperatura', '—')}  |  "
    f"**Longitud:** {st.session_state.get('longitud', '—')}  |  "
    f"**Estilo:** {st.session_state.get('estilo_elegido', 'Ninguno')}  |  "
    f"**API Key:** {fuente_api}"
)

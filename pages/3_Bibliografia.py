import streamlit as st
from openai import OpenAI
import re, os, sys

st.set_page_config(page_title="Bibliografia — Lu Writes", layout="wide")

def limpiar(texto: str) -> str:
    texto = re.sub(r'^```.*?\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'```\s*$', '', texto, flags=re.MULTILINE)
    texto = ''.join(c for c in texto if c.isprintable() or c in '\n\r\t')
    return re.sub(r'[\u200B-\u200D\uFEFF]', '', texto).strip()

# ── valores por defecto ──────────────────────────────────────────────────────
if "modelo" not in st.session_state:
    st.session_state.modelo = "google/gemma-4-26b-a4b-it"
if "temperatura" not in st.session_state:
    st.session_state.temperatura = 0.8
if "temp_label" not in st.session_state:
    st.session_state.temp_label = "Fluido y natural — 0.8  (recomendado)"
if "longitud" not in st.session_state:
    st.session_state.longitud = "Mediano  —  300 palabras"
if "estilo_elegido" not in st.session_state:
    st.session_state.estilo_elegido = "Ninguno"

API_KEY = st.session_state.get("openrouter_api_key", "")
if not API_KEY:
    st.error("No se encontro API Key. Ve a Configuracion e ingresa tu OPENROUTER_API_KEY.")
    st.stop()

st.title("Generador de Bibliografia")
st.markdown("*Produce unicamente listas de referencias formateadas. Sin texto, sin mezclas.*")
st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Fuente BibTeX")

    bibtex_content = st.session_state.get("bibtex_cargado", "")

    if bibtex_content:
        nombre = st.session_state.get("bibtex_nombre", "archivo.txt")
        n = sum(bibtex_content.count(f"@{t}") for t in
                ["article","book","inproceedings","misc","techreport","phdthesis","mastersthesis"])
        st.success(f"BibTeX en memoria — {nombre}  ({n} referencia(s))")
        if st.checkbox("Ver / editar BibTeX cargado"):
            bibtex_content = st.text_area("Contenido BibTeX", value=bibtex_content, height=200)
    else:
        st.info("No hay BibTeX en memoria. Subelo aqui directamente.")

    bib_file = st.file_uploader(
        "Subir o reemplazar archivo BibTeX (.txt)",
        type=["txt"],
        key="bib_biblio_page",
    )
    if bib_file:
        bibtex_content = bib_file.read().decode("utf-8")
        st.session_state["bibtex_cargado"] = bibtex_content
        st.session_state["bibtex_nombre"]  = bib_file.name
        st.success(f"Cargado: {bib_file.name}")

with col2:
    st.subheader("Opciones de salida")

    formatos = st.multiselect(
        "Formatos a generar",
        ["IEEE", "APA 7ma edicion", "Vancouver", "Chicago"],
        default=["IEEE", "APA 7ma edicion"],
    )

    orden = st.radio(
        "Orden de las referencias",
        ["Orden de aparicion  (IEEE estandar)", "Orden alfabetico por apellido"],
        index=0,
    )

    st.caption("Las referencias se generan exclusivamente desde el BibTeX subido. La IA no inventa ni alucina autores ni datos.")

st.divider()

if st.button("Generar Referencias Bibliograficas", type="primary", use_container_width=True):
    if not bibtex_content.strip():
        st.error("Sube un archivo BibTeX (.txt) para continuar.")
        st.stop()
    if not formatos:
        st.error("Selecciona al menos un formato.")
        st.stop()

    orden_str   = "en orden de aparicion (numerico)" if "aparicion" in orden else "en orden alfabetico por apellido del primer autor"
    formatos_str = " y ".join(formatos)

    system_prompt = f"""Eres un gestor bibliografico de precision absoluta.

FUNCION UNICA: convertir referencias BibTeX a los formatos solicitados.

REGLAS ABSOLUTAS:
- Genera SOLAMENTE las listas de referencias. Cero texto narrativo, cero explicaciones.
- No introduzcas ni cierres con comentarios.
- Usa UNICAMENTE los datos presentes en el BibTeX. Si un campo falta, omitelo.
- Cero alucinaciones: no inventes datos bibliograficos.
- Ordena {orden_str}.
- Sé fiel al estandar de cada formato: puntuacion, orden de campos, cursivas (en texto plano usa *titulo*).

FORMATO DE SALIDA:
Por cada formato solicitado escribe exactamente:
--- [NOMBRE DEL FORMATO] ---
[lista numerada]

Separa cada bloque con una linea vacia. Nada mas."""

    user_prompt = f"Genera las referencias en los siguientes formatos: {formatos_str}.\n\nBibTeX:\n{bibtex_content}"

    with st.spinner("Generando listas bibliograficas..."):
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)
            resp = client.chat.completions.create(
                model=st.session_state["modelo"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
            )
            resultado = limpiar(resp.choices[0].message.content)
            st.session_state["referencias_generadas"] = resultado
        except Exception as e:
            st.error(f"Error OpenRouter: {e}")

# ── resultado ─────────────────────────────────────────────────────────────────
if st.session_state.get("referencias_generadas"):
    resultado = st.session_state["referencias_generadas"]
    st.divider()
    st.subheader("Referencias Generadas")

    bloques = [b.strip() for b in re.split(r'(?=--- .+ ---)', resultado) if b.strip()]

    if len(bloques) > 1:
        for bloque in bloques:
            lineas  = bloque.split('\n')
            titulo  = lineas[0].replace('---', '').strip()
            cuerpo  = '\n'.join(lineas[1:]).strip()
            st.markdown(f"**{titulo}**")
            st.caption("Copia con el boton en la esquina superior derecha.")
            st.code(cuerpo, language="text")
    else:
        st.caption("Copia con el boton en la esquina superior derecha.")
        with st.container(border=True):
            st.code(resultado, language="text")

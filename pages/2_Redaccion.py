import streamlit as st
from openai import OpenAI
import re, os, sys

st.set_page_config(page_title="Redaccion — Lu Writes", layout="wide")

# ── helpers ──────────────────────────────────────────────────────────────────
def limpiar(texto: str) -> str:
    texto = re.sub(r'^```.*?\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'```\s*$', '', texto, flags=re.MULTILINE)
    texto = ''.join(c for c in texto if c.isprintable() or c in '\n\r\t')
    return re.sub(r'[\u200B-\u200D\uFEFF]', '', texto).strip()

def leer_estilo(nombre: str) -> str:
    ruta = os.path.join(os.path.dirname(__file__), "..", "estilos", nombre)
    return open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else ""

LONG_MAP = {
    "Corto  —  100 palabras":   "CORTA, aproximadamente 100 palabras.",
    "Mediano  —  300 palabras": "MEDIANA, aproximadamente 300 palabras.",
    "Largo  —  500 palabras":   "LARGA, aproximadamente 500 palabras.",
}

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

# ── verificar API key ─────────────────────────────────────────────────────────
API_KEY = st.session_state.get("openrouter_api_key", "")
if not API_KEY:
    st.error("No se encontro API Key. Ve a Configuracion e ingresa tu OPENROUTER_API_KEY.")
    st.stop()

# ── layout ────────────────────────────────────────────────────────────────────
st.title("Redaccion Academica")
st.markdown("*Genera texto academico original a partir de tus propias notas e hipotesis.*")
st.divider()

col_izq, col_der = st.columns([1.15, 0.85], gap="large")

with col_izq:
    st.subheader("Seccion y contenido")

    SECCIONES = ["Introduccion", "Marco Teorico", "Revision de Literatura",
                 "Metodologia", "Resultados", "Discusion", "Conclusion", "Abstract"]
    seccion = st.selectbox("Seccion a redactar", SECCIONES)

    tema = st.text_input("Tema principal", placeholder="ej. Analisis de fallas en estructuras de hormigon armado")

    contexto = st.text_area(
        "Notas, datos e hipotesis del investigador",
        height=230,
        placeholder=(
            "Escribe aqui tus propias ideas, datos preliminares, hipotesis y argumentos.\n"
            "Lu construira el texto a partir de esto — no inventara hechos ajenos."
        ),
    )

    cita_fmt = st.radio(
        "Formato de citas dentro del texto",
        ["IEEE  —  [1], [2]", "APA  —  Apellido, Año"],
        horizontal=True,
    )

with col_der:
    st.subheader("Literatura cientifica  (opcional)")

    st.info("Sube tu archivo .txt con referencias BibTeX. Si no tienes, Lu redactara igualmente sin citas.")

    bibtex_file = st.file_uploader("Archivo BibTeX (.txt)", type=["txt"], key="bib_red")

    bibtex_content = ""
    if bibtex_file:
        bibtex_content = bibtex_file.read().decode("utf-8")
        n = sum(bibtex_content.count(f"@{t}") for t in
                ["article","book","inproceedings","misc","techreport","phdthesis","mastersthesis"])
        st.success(f"BibTeX cargado — {n} referencia(s) detectada(s): {bibtex_file.name}")
        st.session_state["bibtex_cargado"] = bibtex_content
        st.session_state["bibtex_nombre"]  = bibtex_file.name
    elif st.session_state.get("bibtex_cargado"):
        bibtex_content = st.session_state["bibtex_cargado"]
        st.caption(f"BibTeX en memoria: {st.session_state.get('bibtex_nombre','archivo.txt')}")

    resumen_bib = ""
    if bibtex_content:
        resumen_bib = st.text_area(
            "Notas sobre como usar cada referencia  (opcional)",
            height=150,
            placeholder="Smith (2023) demuestra que X afecta Y bajo condiciones Z...",
        )

st.divider()

if st.button("Redactar con Lu Writes", type="primary", use_container_width=True):
    if not tema.strip() or not contexto.strip():
        st.error("El tema y el contexto son obligatorios.")
        st.stop()

    long_defecto = "Mediano  —  300 palabras"
    longitud_str = LONG_MAP.get(st.session_state.get("longitud", long_defecto),
                                "MEDIANA, aproximadamente 300 palabras.")
    estilo_txt = ""
    eg = st.session_state.get("estilo_elegido", "Ninguno")
    if eg != "Ninguno":
        estilo_txt = leer_estilo(eg)

    inst_bib = ""
    datos_bib = ""
    if bibtex_content.strip():
        fmt = "IEEE — [1], [2]" if "IEEE" in cita_fmt else "APA 7ma edicion"
        inst_bib = (
            "\nINTEGRACION DE LITERATURA:\n"
            "- Usa las referencias BibTeX proporcionadas para enriquecer el argumento.\n"
            f"- Inserta citas in-text en formato {fmt} de forma organica, solo donde el argumento las necesite.\n"
            "- Cero alucinaciones: no inventes autores, titulos ni datos que no esten en el BibTeX.\n"
            "- Las listas bibliograficas NO van en este texto; se generan en la pagina de Bibliografia.\n"
        )
        datos_bib = f"\n\n--- REFERENCIAS BIBTEX ---\n{bibtex_content}"
        if resumen_bib.strip():
            datos_bib += f"\n\n--- INSTRUCCIONES DE USO ---\n{resumen_bib}"

    estilo_extra = f"\nDIRECTRICES DE ESTILO:\n{estilo_txt}" if estilo_txt else ""

    system_prompt = (
        'Eres "Lu", un redactor academico experto con decadas de experiencia en investigacion.\n\n'
        "IDENTIDAD:\n"
        "- Piensas antes de escribir. Tu prosa es densa, tecnica y elegante.\n"
        "- Alternas con maestria oraciones cortas de impacto (8-12 palabras) con oraciones largas\n"
        "  y subordinadas (25-40 palabras) que desarrollan ideas complejas.\n"
        "- Nunca dos parrafos consecutivos empiezan con la misma estructura.\n\n"
        "ORIGINALIDAD E INTEGRIDAD ACADEMICA (CRITICO):\n"
        "- El texto DEBE ser 100% original en su construccion. Prohibido reproducir frases\n"
        "  textuales de otras fuentes aunque esten en el BibTeX.\n"
        "- Sintetiza ideas, no copies. Parafraseae con precision academica, no literalmente.\n"
        "- Cada argumento debe emerger de los datos del investigador, no de generalizaciones vagas.\n"
        "- Cero alucinaciones: si un dato no esta en las notas ni en el BibTeX, no lo incluyas.\n"
        "- Construye el texto como lo haria un autor humano experto: con voz propia, no como un resumen automatico.\n\n"
        "REGLAS DE ESTILO ANTI-DETECCION:\n"
        '- PROHIBIDO: "En resumen", "Es importante", "Es crucial", "Cabe destacar", "En conclusion",\n'
        '  "Sin embargo" al inicio de parrafo, "Por otro lado", "En este sentido", "Es evidente que",\n'
        '  "A lo largo de", "En el contexto de", "Resulta fundamental".\n'
        "- PROHIBIDO: listas con viñetas o numeradas en el cuerpo del texto.\n"
        "- PROHIBIDO: negritas o cursivas de Markdown en el cuerpo.\n"
        "- PROHIBIDO: escribir el titulo de la seccion al principio.\n"
        "- USA: conectores academicos variados y sofisticados. Transiciones implicitas.\n"
        "  Voz activa y pasiva mezcladas. Clausulas absolutas. Incisos explicativos.\n\n"
        "FORMATO DE SALIDA:\n"
        "- Texto plano continuo. Solo parrafos separados por linea en blanco.\n"
        f"- Longitud: {longitud_str}\n"
        "- NO incluyas referencias bibliograficas al final.\n"
        f"{inst_bib}\n"
        f"{estilo_extra}"
    )

    user_prompt = (
        f"Seccion: {seccion}\n"
        f"Tema: {tema}\n\n"
        f"Notas e hipotesis del investigador:\n{contexto}"
        f"{datos_bib}"
    )

    st.divider()
    st.subheader(seccion)

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

        stream = client.chat.completions.create(
            model=st.session_state["modelo"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=st.session_state.get("temperatura", 0.8),
            stream=True,
        )

        def token_generator():
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        texto_completo = st.write_stream(token_generator())
        texto_limpio   = limpiar(texto_completo)

        st.session_state["texto_redaccion"]  = texto_limpio
        st.session_state["seccion_generada"] = seccion

        palabras = len(texto_limpio.split())
        st.caption(f"Aproximadamente {palabras} palabras.")

        st.divider()
        st.caption("Copia el texto en texto plano desde el bloque de abajo:")
        with st.container(border=True):
            st.code(texto_limpio, language="text")

    except Exception as e:
        st.error(f"Error OpenRouter: {e}")

# ── resultado guardado (si se navega de vuelta) ────────────────────────────────
elif st.session_state.get("texto_redaccion"):
    st.divider()
    st.subheader(st.session_state.get("seccion_generada", "Texto generado"))
    st.write(st.session_state["texto_redaccion"])
    palabras = len(st.session_state["texto_redaccion"].split())
    st.caption(f"Aproximadamente {palabras} palabras.")
    st.divider()
    st.caption("Copia el texto en texto plano desde el bloque de abajo:")
    with st.container(border=True):
        st.code(st.session_state["texto_redaccion"], language="text")

import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
import re
import time
import json
from pathlib import Path

# ====================== CONFIG ======================

st.set_page_config(page_title="Redaccion — Lu Writes", layout="wide")

ROOT = Path(__file__).resolve().parent.parent
ESTILOS_DIR = ROOT / "estilos"
ESTILO_DEFAULT = "academico_tecnico.md"

MAX_REFERENCIAS = 3
LONGITUD_RESUMEN = 200
UMBRAL_RESUMEN_BIB = 80
UMBRAL_RESUMEN_PREVIEW = 50

CARACTERES_PERMITIDOS = set(
    'abcdefghijklmnopqrstuvwxyz'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'ñÑáéíóúÁÉÍÓÚüÜ'
    '0123456789'
    ' '
    '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    'ºª@#~€¬'
)

SECCIONES = [
    "Introduccion", "Marco Teorico", "Revision de Literatura",
    "Metodologia", "Resultados", "Discusion", "Conclusion", "Abstract",
]

LONG_MAP = {
    "Corto  —  100 palabras":   "CORTA, aproximadamente 100 palabras.",
    "Mediano  —  300 palabras": "MEDIANA, aproximadamente 300 palabras.",
    "Largo  —  500 palabras":   "LARGA, aproximadamente 500 palabras.",
}

TIPOS_BIBTEX = [
    "article", "book", "inproceedings", "misc",
    "techreport", "phdthesis", "mastersthesis",
]

MODELS = [
    "openrouter/free",
]

TEMP_OPTS = {
    "Preciso y conservador — 0.3": 0.3,
    "Equilibrado — 0.6": 0.6,
    "Fluido y natural — 0.8": 0.8,
    "Muy creativo — 1.0 (recomendado)": 1.0,
}





# ====================== HELPERS ======================

def limpiar(texto: str) -> str:
    """Limpia razonamiento, watermarks, markdown y caracteres no permitidos."""
    # Bloques de razonamiento
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL | re.IGNORECASE)
    # Bloques markdown
    texto = re.sub(r'^```.*?\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'```\s*$', '', texto, flags=re.MULTILINE)
    # Watermarks U+XXXX y variantes
    texto = re.sub(r'U\s*\+\s*[0-9A-Fa-f]{2,8}', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\\u\s*[0-9A-Fa-f]{4}', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'U000A', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'&#10;', ' ', texto)
    # Saltos a espacios (parrafo unico)
    texto = texto.replace('\n', ' ').replace('\r', ' ')
    # Filtrar caracteres
    texto = ''.join(c for c in texto if c in CARACTERES_PERMITIDOS)
    # Normalizar espacios
    return re.sub(r' +', ' ', texto).strip()


def leer_estilo(nombre: str) -> str:
    ruta = ESTILOS_DIR / nombre
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def listar_estilos() -> list:
    """Lista archivos .md en la carpeta de estilos. Garantiza el default si esta vacia."""
    ESTILOS_DIR.mkdir(exist_ok=True)
    archivos = sorted(f.name for f in ESTILOS_DIR.glob("*.md"))
    return archivos or [ESTILO_DEFAULT]


def contar_referencias(bibtex: str) -> int:
    return sum(bibtex.count(f"@{t}") for t in TIPOS_BIBTEX)


def parsear_referencias(bibtex: str, max_refs: int = MAX_REFERENCIAS) -> list:
    """Extrae las primeras N referencias y las simplifica a una linea cada una."""
    entradas = re.split(r'\n(?=@)', bibtex)
    refs = []
    for entrada in entradas:
        if len(refs) >= max_refs:
            break
        if not entrada.strip().startswith('@'):
            continue

        autor = re.search(r'author\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
        year = re.search(r'year\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
        titulo = re.search(r'title\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
        if not (autor and year):
            continue

        # Buscar resumen: linea larga sin formato BibTeX
        resumen = ""
        for linea in entrada.split('\n'):
            l = linea.strip()
            if len(l) > UMBRAL_RESUMEN_BIB and not l.startswith('@') and '=' not in l[:30]:
                resumen = l[:LONGITUD_RESUMEN]
                break

        titulo_txt = titulo.group(1) if titulo else 'Sin titulo'
        ref = f"[{len(refs)+1}] {autor.group(1)} ({year.group(1)}): {titulo_txt}"
        if resumen:
            ref += f" - Idea clave: {resumen}"
        refs.append(ref)
    return refs


@st.cache_resource(show_spinner=False)
def crear_cliente(api_key: str) -> OpenAI:
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def llamar_api(client: OpenAI, modelo: str, messages: list,
               temperatura: float, max_intentos: int = 5):
    """Llama a la API con backoff exponencial ante rate limit."""
    for intento in range(1, max_intentos + 1):
        try:
            return client.chat.completions.create(
                model=modelo,
                messages=messages,
                temperature=temperatura,
                stream=False,
            )
        except Exception as e:
            err = str(e).lower()
            es_rate_limit = any(s in err for s in ("429", "rate", "limit"))
            if es_rate_limit and intento < max_intentos:
                time.sleep(2 ** intento)
                continue
            if es_rate_limit:
                st.error("Limite de solicitudes agotado. Espera unos segundos y reintenta.")
            else:
                st.error(f"Error OpenRouter: {e}")
            return None


def animacion_typing(texto: str, height: int = 400) -> None:
    """Renderiza el texto con animacion de tipeo."""
    texto_json = json.dumps(texto, ensure_ascii=False)
    html = f"""
    <div id="lu-typing" style="
        font-family: 'Source Sans Pro', 'Segoe UI', sans-serif;
        font-size: 1.05rem;
        line-height: 1.75;
        color: #f0f2f6;
        white-space: pre-wrap;
        word-break: break-word;
        padding: 1rem 0;
    "></div>
    <script>
    (function() {{
        const text = {texto_json};
        const el = document.getElementById('lu-typing');
        const speed = 18;
        let i = 0;
        function type() {{
            if (i < text.length) {{
                const chunk = text.substring(i, Math.min(i + 3, text.length));
                el.textContent += chunk;
                i += chunk.length;
                requestAnimationFrame(() => setTimeout(type, speed));
            }}
        }}
        type();
    }})();
    </script>
    """
    components.html(html, height=height, scrolling=True)


def descargar_texto(texto: str, key: str) -> None:
    """Boton nativo de Streamlit para descarga."""
    st.download_button(
        label="Descargar texto",
        data=texto.encode("utf-8"),
        file_name="texto_redaccion.txt",
        mime="text/plain",
        type="primary",
        use_container_width=True,
        key=key,
    )


# ====================== PROMPT ANTI-IA ======================

INST_BIBTEX_TEMPLATE = """
INTEGRACION DE LITERATURA (REGLAS ESTRICTAS):
REGLA CRITICA: NO escribas como un resumen de papers. Escribe TU argumento original.

- Formato de citas: {fmt}
- MAXIMO 1 cita en TODO el texto (opcional). Preferiblemente NINGUNA.
- NO cites en cada oracion o parrafo.
- Si citas, hazlo al final de una oracion, nunca al principio.
- Reformula TODO en TUS propias palabras. NO uses frases de los papers.
- Tu voz debe ser 98% del texto, las citas solo 2%.
- Prohibido nombres de autores en el texto.
"""

SYSTEM_PROMPT_TEMPLATE = """Actua como un investigador senior con 20 anos de trayectoria. Eres un academico con opiniones firmes, dudas genuinas y un estilo de escritura imperfecto y humano. Tu trabajo es redactar un texto que NADIE pueda distinguir del de una persona real.

FORMATO:
- Un solo parrafo continuo, sin saltos de linea. No escribas titulos.
- Usa TILDES CORRECTAS (a e i o u, n). Si no las usas, te detectaran como IA.
- Cero markdown, cero comandos especiales, cero caracteres raros.
- REDACCION ACADEMICA EN TERCERA PERSONA.

ESTILO HUMANO (reglas no negociables):

A. BURSTINESS EXTREMA (variacion de longitud):
   - Alterna caoticamente: 5 palabras. Luego una oracion de 35 palabras con subordinadas, matices y giros. Luego 9 palabras. Luego 28. Rompe la simetria.
   - Prohibido el ritmo uniforme. No hagas corto-largo-corto-largo de forma predecible.

B. PERPLEJIDAD ALTA (palabras inesperadas):
   - Elige siempre el sinonimo MENOS obvio. No uses la palabra que "espera" la IA.
   - Prohibido: "importante, robusto, eficiente, efectivo, significativo, claro, evidente".
   - Prohibido: "enfoque innovador, representa un, aborda tanto, desafios, limitaciones".
   - Prohibido: "no solo... sino que tambien, por su parte, en este sentido".
   - Usa en su lugar: "relevante, solido, consistente, que marca diferencia, que pesa".

C. TONO ACADEMICO (pero humano):
   - USA TERCERA PERSONA: "Se considera", "Se observa", "Los autores sostienen", "Resulta evidente que".
   - Rompe reglas gramaticales cuando suene natural: empieza con "Y", "Pero", "Aunque".
   - Incluye UNA expresion coloquial academica: "a fin de cuentas", "en el fondo", "vamos al grano".
   - Usa modismos naturales: "no es para tanto", "hay que verlo en perspectiva".
   - Haz PREGUNTAS retoricas: "Que significa esto realmente?", "Hasta que punto es valido?".

D. SIMPLICIDAD (anti-jerga):
   - Prefiere lenguaje directo. Si una palabra tiene equivalente simple, usa el simple.
   - Evita jerga innecesaria que suene a "relleno academico".
   - Cada palabra debe tener un significado preciso, no decorativo.
   - Si puedes decir algo en 5 palabras en vez de 12, hazlo.

E. IMPERFECCIONES HUMANAS:
   - Incluye redundancias ocasionales o giros que no son gramaticalmente perfectos.
   - Interrumpe el flujo con parentesis: "esto ocurre (y aqui viene lo interesante) porque...".
   - Repite una palabra intencionalmente para enfatizar. Los humanos lo hacen.
   - No seas simetrico. No uses estructuras paralelas perfectas.

F. VOZ Y OPINION:
   - Ten postura. No seas neutral. Defiende el punto aunque sea controversial.
   - Critica: "Lo que falla aqui es...", "No resulta convincente que...".
   - Haz hedging: "parece que", "podria ser", "quizas", "no esta del todo claro".
   - NUNCA afirmes algo con certeza del 100%. Todo debe estar matizado.

G. ESTRUCTURA CAOTICA:
   - No sigas el patron: idea 1, idea 2, idea 3. Mezcla las ideas de forma no lineal.
   - Si la primera mitad usa vocabulario tecnico, la segunda mitad usa otro registro.
   - Cambia el ritmo intencionalmente a mitad del texto.

H. TRANSICIONES NATURALES (no robotizadas):
   - PROHIBIDO usar: "Ademas", "En conclusion", "Por otro lado", "Es importante destacar", "Cabe mencionar", "En resumen", "Es crucial", "Sin embargo" al inicio, "En este sentido", "A lo largo de", "Es fundamental", "Como se puede observar", "En la actualidad", "Dado que", "Por consiguiente", "En efecto".
   - Permitido (con variedad): "Esto sugiere...", "Visto asi...", "Lo que sigue es...", "Un dato que sorprende...", "Contrariamente a lo esperado...", "Cabe preguntarse...".
   - Simplemente NO uses conectores a veces. Los humanos saltan de idea sin avisar.

I. CITAS (si las hay):
   - Maximo 1 cita en todo el texto, preferible cero. No nombres autores en el texto.
   - Reformula completamente las ideas. No copies frases de los papers.
   - Si citas, solo [1] al final de una oracion, como apoyo, no como contenido principal.

EJEMPLO DE TEXTO IA (PROHIBIDO):
"El diseno de herramientas computacionales representa un enfoque innovador que aborda tanto desafios pedagogicos como limitaciones tecnicas. La implementacion de soluciones personalizadas permite adaptar recursos a las necesidades curriculares."

EJEMPLO DE TEXTO HUMANO (OBLIGATORIO) - EN TERCERA PERSONA:
"Se duda que las herramientas comerciales sean la respuesta definitiva. Si bien funcionan para la industria --eso hay que reconocerlo--, en el aula resultan excesivas y, lo que es peor, costosas. A ver, no es que se este en contra de todo. Simplemente se considera que desarrollar software a medida, aunque requiera esfuerzo inicial, ofrece ventajas que van mas alla del ahorro economico. Esto permite ajustar cada funcion a como realmente se ensena. Claro, esto plantea un problema: no todos los departamentos tienen capacidad para mantener estas herramientas. Quizas la solucion pasa por buscar un termino medio."

LONGITUD: {longitud_str}
{inst_bib}
{estilo_extra}"""


# ====================== ESTADO INICIAL ======================

DEFAULTS = {
    "modelo": "openrouter/free",
    "temperatura": 1.0,
    "temp_label": "Muy creativo — 1.0 (recomendado)",
    "longitud": "Mediano  —  300 palabras",
    "estilo_elegido": ESTILO_DEFAULT,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# Limpiar bibliografia residual de sesiones anteriores
for k in ("bibtex_cargado", "bibtex_nombre"):
    st.session_state.pop(k, None)


# ====================== API KEY ======================

try:
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    API_KEY = ""

if not API_KEY:
    st.error(
        "Falta `OPENROUTER_API_KEY` en `.streamlit/secrets.toml`. "
        "Agregala con: `OPENROUTER_API_KEY = \"sk-or-v1-...\"` y reinicia la app."
    )
    st.stop()


# ====================== SIDEBAR ======================

with st.sidebar:
    st.header("Ajustes")
    st.caption("Parametros del modelo y la salida.")

    st.selectbox("Modelo de lenguaje", MODELS, key="modelo")

    st.selectbox("Nivel de creatividad", list(TEMP_OPTS), key="temp_label")
    st.session_state["temperatura"] = TEMP_OPTS[st.session_state["temp_label"]]

    st.radio("Longitud del texto", list(LONG_MAP), key="longitud")

    # Validar que el estilo guardado siga existiendo en disco
    estilos_disponibles = listar_estilos()
    if st.session_state["estilo_elegido"] not in estilos_disponibles:
        st.session_state["estilo_elegido"] = estilos_disponibles[0]
    st.selectbox("Estilo de escritura", estilos_disponibles, key="estilo_elegido")

    st.divider()
    st.caption(f"Temperatura activa: **{st.session_state['temperatura']}**")


# ====================== UI ======================

st.title("Redaccion Academica")
st.markdown("*Genera texto plano limpio para secciones academicas desde tus notas.*")
st.divider()

col_izq, col_der = st.columns([1.15, 0.85], gap="large")

with col_izq:
    st.subheader("Seccion y contenido")
    seccion = st.selectbox("Seccion a redactar", SECCIONES)
    tema = st.text_input(
        "Tema principal",
        placeholder="ej. Analisis de fallas en estructuras de hormigon armado",
    )
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
    st.info(
        "Sube tu archivo .txt con referencias BibTeX y resumenes/abstracts.\n\n"
        "El archivo puede contener:\n"
        "- Entradas BibTeX (@article, @book, etc.)\n"
        "- Resumenes o abstracts de los articulos\n"
        "- Notas sobre como usar cada referencia\n\n"
        f"NOTA: Se usaran maximo {MAX_REFERENCIAS} referencias simplificadas. "
        "El objetivo es que TU voz sea 95% del texto, no un resumen de papers."
    )

    bibtex_file = st.file_uploader("Archivo de referencias (.txt)", type=["txt"], key="bib_red")
    bibtex_content = ""
    if bibtex_file:
        bibtex_content = bibtex_file.read().decode("utf-8")
        n_refs = contar_referencias(bibtex_content)
        lineas_resumen = [
            l for l in bibtex_content.split('\n')
            if len(l) > UMBRAL_RESUMEN_PREVIEW
            and not l.strip().startswith(('@', '{'))
        ]
        mensaje = f"Archivo cargado — {n_refs} referencia(s) BibTeX"
        if lineas_resumen:
            mensaje += f" + {len(lineas_resumen)} bloques de resumen"
        st.success(f"{mensaje}: {bibtex_file.name}")
        with st.expander("Ver contenido cargado"):
            preview = bibtex_content[:2000] + ("..." if len(bibtex_content) > 2000 else "")
            st.text_area("Preview", preview, height=200, disabled=True)

st.divider()


# ====================== GENERACION ======================

if st.button("Redactar con Lu Writes", type="primary", use_container_width=True):
    if not tema.strip() or not contexto.strip():
        st.error("El tema y el contexto son obligatorios.")
        st.stop()

    # Resolver longitud y estilo
    longitud_str = LONG_MAP.get(
        st.session_state.get("longitud", "Mediano  —  300 palabras"),
        "MEDIANA, aproximadamente 300 palabras.",
    )
    estilo_archivo = st.session_state.get("estilo_elegido", ESTILO_DEFAULT)
    estilo_txt = leer_estilo(estilo_archivo) or leer_estilo(ESTILO_DEFAULT)
    estilo_extra = f"\nDIRECTRICES DE ESTILO:\n{estilo_txt}" if estilo_txt else ""

    # Procesar bibliografia
    inst_bib = ""
    datos_bib = ""
    if bibtex_content.strip():
        fmt = "IEEE — [1], [2]" if "IEEE" in cita_fmt else "APA 7ma edicion"
        refs = parsear_referencias(bibtex_content)
        if refs:
            st.info(f"Integrando {len(refs)} referencias de forma natural.")
            inst_bib = INST_BIBTEX_TEMPLATE.format(fmt=fmt)
            datos_bib = (
                "\n\n--- REFERENCIAS SIMPLIFICADAS (reformula en tus palabras) ---\n"
                + "\n".join(refs)
            )

    # Construir prompts
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        longitud_str=longitud_str,
        inst_bib=inst_bib,
        estilo_extra=estilo_extra,
    )
    user_prompt = f"Seccion: {seccion}\nTema: {tema}\n\n{contexto}{datos_bib}"

    # Llamar al modelo
    st.divider()
    st.subheader(seccion)

    client = crear_cliente(API_KEY)
    modelo = st.session_state["modelo"]
    # La app fuerza temperatura alta para evitar texto plano (minimo 1.0)
    temperatura = max(float(st.session_state.get("temperatura", 1.0)), 1.0)

    with st.spinner("Generando texto..."):
        resp = llamar_api(
            client=client,
            modelo=modelo,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperatura=temperatura,
        )

    if resp is None:
        st.stop()

    texto_limpio = limpiar(resp.choices[0].message.content or "")

    if texto_limpio:
        animacion_typing(texto_limpio, height=400)
        palabras = len(texto_limpio.split())
        st.success(f"Texto generado. Aproximadamente {palabras} palabras.")
        st.session_state["texto_redaccion"] = texto_limpio
        st.session_state["seccion_generada"] = seccion
        descargar_texto(texto_limpio, key="dl_nuevo")
    else:
        st.warning("(Sin texto generado)")


# ====================== TEXTO PERSISTENTE ======================

elif st.session_state.get("texto_redaccion"):
    st.divider()
    st.subheader(st.session_state.get("seccion_generada", "Texto generado"))
    palabras = len(st.session_state["texto_redaccion"].split())
    st.caption(f"Aproximadamente {palabras} palabras.")
    descargar_texto(st.session_state["texto_redaccion"], key="dl_persistente")

import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components
import re, os, time, base64, json

st.set_page_config(page_title="Redaccion — Lu Writes", layout="wide")

# Limpiar referencias de sesiones anteriores para evitar mezclar temas
if "bibtex_cargado" in st.session_state:
    del st.session_state["bibtex_cargado"]
if "bibtex_nombre" in st.session_state:
    del st.session_state["bibtex_nombre"]

CARACTERES_PERMITIDOS = set(
    'abcdefghijklmnopqrstuvwxyz'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'ñÑ'
    'áéíóú'
    'ÁÉÍÓÚ'
    'üÜ'
    '0123456789'
    ' '  # espacio
    '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    'ºª@#~€¬'
)

def limpiar(texto: str) -> str:
    # Eliminar bloques de razonamiento <think>...</think>
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL | re.IGNORECASE)
    
    # Eliminar bloques markdown
    texto = re.sub(r'^```.*?\s*', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'```\s*$', '', texto, flags=re.MULTILINE)
    
    # Eliminar watermarks U+XXXX de forma agresiva
    texto = re.sub(r'U\s*\+\s*[0-9A-Fa-f]{2,8}', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\\u\s*[0-9A-Fa-f]{4}', ' ', texto, flags=re.IGNORECASE)
    
    # Especificamente U+000A (newline) y variantes
    texto = re.sub(r'U\s*\+\s*000A', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'U000A', ' ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'&#10;', ' ', texto)
    
    # Eliminar saltos de linea y convertir en espacios (TODO en un solo parrafo)
    texto = texto.replace('\n', ' ')
    texto = texto.replace('\r', ' ')
    
    # Eliminar otros caracteres no permitidos
    texto = ''.join(c for c in texto if c in CARACTERES_PERMITIDOS)
    
    # Normalizar espacios multiples
    texto = re.sub(r' +', ' ', texto)
    
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    
    return texto

def leer_estilo(nombre: str) -> str:
    ruta = os.path.join(os.path.dirname(__file__), "..", "estilos", nombre)
    return open(ruta, encoding="utf-8").read() if os.path.exists(ruta) else ""

LONG_MAP = {
    "Corto  —  100 palabras":   "CORTA, aproximadamente 100 palabras.",
    "Mediano  —  300 palabras": "MEDIANA, aproximadamente 300 palabras.",
    "Largo  —  500 palabras":   "LARGA, aproximadamente 500 palabras.",
}

if "modelo" not in st.session_state:
    st.session_state.modelo = "openrouter/free"
if "temperatura" not in st.session_state:
    st.session_state.temperatura = 1.0
if "temp_label" not in st.session_state:
    st.session_state.temp_label = "Muy creativo — 1.0 (recomendado)"
if "longitud" not in st.session_state:
    st.session_state.longitud = "Mediano  —  300 palabras"
if "estilo_elegido" not in st.session_state:
    st.session_state.estilo_elegido = "academico_tecnico.md"

API_KEY = st.session_state.get("openrouter_api_key", "")
if not API_KEY:
    st.error("No se encontro API Key. Ve a Configuracion e ingresa tu API Key de OpenRouter.")
    st.stop()

st.title("Redaccion Academica")
st.markdown("*Genera texto plano limpio para secciones academicas desde tus notas.*")
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

    st.info("""Sube tu archivo .txt con referencias BibTeX y resumenes/abstracts. 
    
    El archivo puede contener:
    - Entradas BibTeX (@article, @book, etc.)
    - Resumenes o abstracts de los articulos
    - Notas sobre como usar cada referencia
    
    NOTA: Se usaran maximo 3 referencias simplificadas. 
    El objetivo es que TU voz sea 95% del texto, no un resumen de papers.""")

    bibtex_file = st.file_uploader("Archivo de referencias (.txt)", type=["txt"], key="bib_red")

    bibtex_content = ""
    if bibtex_file:
        bibtex_content = bibtex_file.read().decode("utf-8")
        n = sum(bibtex_content.count(f"@{t}") for t in
                ["article","book","inproceedings","misc","techreport","phdthesis","mastersthesis"])
        
        # Contar lineas que parecen resumenes (lineas largas sin @)
        lineas_resumen = [l for l in bibtex_content.split('\n') if len(l) > 50 and not l.strip().startswith('@') and not l.strip().startswith('{')]
        
        mensaje = f"Archivo cargado — {n} referencia(s) BibTeX"
        if lineas_resumen:
            mensaje += f" + {len(lineas_resumen)} bloques de resumen"
        st.success(f"{mensaje}: {bibtex_file.name}")
        
        # NO guardar en session_state para evitar persistencia entre temas
        # st.session_state["bibtex_cargado"] = bibtex_content
        # st.session_state["bibtex_nombre"]  = bibtex_file.name
        
        # Mostrar preview del contenido
        with st.expander("Ver contenido cargado"):
            st.text_area("Preview", bibtex_content[:2000] + ("..." if len(bibtex_content) > 2000 else ""), height=200, disabled=True)

st.divider()

if st.button("Redactar con Lu Writes", type="primary", use_container_width=True):
    if not tema.strip() or not contexto.strip():
        st.error("El tema y el contexto son obligatorios.")
        st.stop()

    long_defecto = "Mediano  —  300 palabras"
    longitud_str = LONG_MAP.get(st.session_state.get("longitud", long_defecto),
                                "MEDIANA, aproximadamente 300 palabras.")
    estilo_txt = ""
    eg = st.session_state.get("estilo_elegido", "academico_tecnico.md")
    if eg and os.path.exists(os.path.join(os.path.dirname(__file__), "..", "estilos", eg)):
        estilo_txt = leer_estilo(eg)
    else:
        ruta_default = os.path.join(os.path.dirname(__file__), "..", "estilos", "academico_tecnico.md")
        if os.path.exists(ruta_default):
            estilo_txt = open(ruta_default, encoding="utf-8").read()

    inst_bib = ""
    datos_bib = ""
    referencias_procesadas = ""
    if bibtex_content.strip():
        fmt = "IEEE — [1], [2]" if "IEEE" in cita_fmt else "APA 7ma edicion"
        
        # Extraer solo la informacion esencial de cada referencia
        import re
        entradas = re.split(r'\n(?=@)', bibtex_content)
        referencias_simplificadas = []
        
        for i, entrada in enumerate(entradas[:3]):  # Maximo 3 referencias
            if not entrada.strip().startswith('@'):
                continue
                
            # Extraer autor, año y titulo
            autor_match = re.search(r'author\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
            year_match = re.search(r'year\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
            title_match = re.search(r'title\s*=\s*\{([^}]+)\}', entrada, re.IGNORECASE)
            
            # Buscar resumen (lineas largas sin formato BibTeX)
            lineas = entrada.split('\n')
            resumen = ""
            for linea in lineas:
                linea_limpia = linea.strip()
                if len(linea_limpia) > 80 and not linea_limpia.startswith('@') and not '=' in linea_limpia[:30]:
                    resumen = linea_limpia[:200]  # Maximo 200 caracteres
                    break
            
            if autor_match and year_match:
                ref_simple = f"[{i+1}] {autor_match.group(1)} ({year_match.group(1)}): {title_match.group(1) if title_match else 'Sin titulo'}"
                if resumen:
                    ref_simple += f" - Idea clave: {resumen}"
                referencias_simplificadas.append(ref_simple)
        
        if referencias_simplificadas:
            referencias_procesadas = "\n".join(referencias_simplificadas)
            st.info(f"Integrando {len(referencias_simplificadas)} referencias de forma natural.")
        
        inst_bib = (
            "\nINTEGRACION DE LITERATURA (REGLAS ESTRICTAS):\n"
            "REGLA CRITICA: NO escribas como un resumen de papers. Escribe TU argumento original.\n\n"
            f"- Formato de citas: {fmt}\n"
            "- MAXIMO 1 cita en TODO el texto (opcional). Preferiblemente NINGUNA.\n"
            "- NO cites en cada oracion o parrafo.\n"
            "- Si citas, hazlo al final de una oracion, nunca al principio.\n"
            "- Reformula TODO en TUS propias palabras. NO uses frases de los papers.\n"
            "- Tu voz debe ser 98% del texto, las citas solo 2%.\n"
            "- Prohibido nombres de autores en el texto.\n"
        )
        datos_bib = f"\n\n--- REFERENCIAS SIMPLIFICADAS (reformula en tus palabras) ---\n{referencias_procesadas}"

    estilo_extra = f"\nDIRECTRICES DE ESTILO:\n{estilo_txt}" if estilo_txt else ""

    # Prompt maestro anti-IA: combina perplejidad, burstiness, tono academico y simplicidad
    system_prompt = (
        'Actua como un investigador senior con 20 anos de trayectoria. Eres un academico con opiniones '
        'firmes, dudas genuinas y un estilo de escritura imperfecto y humano. Tu trabajo es redactar '
        'un texto que NA DIE pueda distinguir del de una persona real.\n\n'
        'FORMATO:\n'
        '- Un solo parrafo continuo, sin saltos de linea. No escribas titulos.\n'
        '- Usa TILDES CORRECTAS (a e i o u, n). Si no las usas, te detectaran como IA.\n'
        '- Cero markdown, cero comandos especiales, cero caracteres raros.\n'
        '- REDACCION ACADEMICA EN TERCERA PERSONA.\n\n'
        'ESTILO HUMANO (reglas no negociables):\n\n'
        'A. BURSTINESS EXTREMA (variacion de longitud):\n'
        '   - Alterna caoticamente: 5 palabras. Luego una oracion de 35 palabras con subordinadas, '
        'matices y giros. Luego 9 palabras. Luego 28. Rompe la simetria.\n'
        '   - Prohibido el ritmo uniforme. No hagas corto-largo-corto-largo de forma predecible.\n\n'
        'B. PERPLEJIDAD ALTA (palabras inesperadas):\n'
        '   - Elige siempre el sinonimo MENOS obvio. No uses la palabra que "espera" la IA.\n'
        '   - Prohibido: "importante, robusto, eficiente, efectivo, significativo, claro, evidente".\n'
        '   - Prohibido: "enfoque innovador, representa un, aborda tanto, desafios, limitaciones".\n'
        '   - Prohibido: "no solo... sino que tambien, por su parte, en este sentido".\n'
        '   - Usa en su lugar: "relevante, solido, consistente, que marca diferencia, que pesa".\n\n'
        'C. TONO ACADEMICO (pero humano):\n'
        '   - USA TERCERA PERSONA: "Se considera", "Se observa", "Los autores sostienen", "Resulta evidente que".\n'
        '   - Rompe reglas gramaticales cuando suene natural: empieza con "Y", "Pero", "Aunque".\n'
        '   - Incluye UNA expresion coloquial academica: "a fin de cuentas", "en el fondo", "vamos al grano".\n'
        '   - Usa modismos naturales: "no es para tanto", "hay que verlo en perspectiva".\n'
        '   - Haz PREGUNTAS retoricas: "Que significa esto realmente?", "Hasta que punto es valido?".\n\n'
        'D. SIMPLICIDAD (anti-jerga):\n'
        '   - Prefiere lenguaje directo. Si una palabra tiene equivalente simple, usa el simple.\n'
        '   - Evita jerga innecesaria que suene a "relleno academico".\n'
        '   - Cada palabra debe tener un significado preciso, no decorativo.\n'
        '   - Si puedes decir algo en 5 palabras en vez de 12, hazlo.\n\n'
        'E. IMPERFECCIONES HUMANAS:\n'
        '   - Incluye redundancias ocasionales o giros que no son gramaticalmente perfectos.\n'
        '   - Interrumpe el flujo con parentesis: "esto ocurre (y aqui viene lo interesante) porque...".\n'
        '   - Repite una palabra intencionalmente para enfatizar. Los humanos lo hacen.\n'
        '   - No seas simetrico. No uses estructuras paralelas perfectas.\n\n'
        'F. VOZ Y OPINION:\n'
        '   - Ten postura. No seas neutral. Defiende el punto aunque sea controversial.\n'
        '   - Critica: "Lo que falla aqui es...", "No resulta convincente que...".\n'
        '   - Haz hedging: "parece que", "podria ser", "quizas", "no esta del todo claro".\n'
        '   - NUNCA afirmes algo con certeza del 100%. Todo debe estar matizado.\n\n'
        'G. ESTRUCTURA CAOTICA:\n'
        '   - No sigas el patron: idea 1, idea 2, idea 3. Mezcla las ideas de forma no lineal.\n'
        '   - Si la primera mitad usa vocabulario tecnico, la segunda mitad usa otro registro.\n'
        '   - Cambia el ritmo intencionalmente a mitad del texto.\n\n'
        'H. TRANSICIONES NATURALES (no robotizadas):\n'
        '   - PROHIBIDO usar: "Ademas", "En conclusion", "Por otro lado", "Es importante destacar", '
        '"Cabe mencionar", "En resumen", "Es crucial", "Sin embargo" al inicio, "En este sentido", '
        '"A lo largo de", "Es fundamental", "Como se puede observar", "En la actualidad", "Dado que", '
        '"Por consiguiente", "En efecto".\n'
        '   - Permitido (con variedad): "Esto sugiere...", "Visto asi...", "Lo que sigue es...", '
        '"Un dato que sorprende...", "Contrariamente a lo esperado...", "Cabe preguntarse...".\n'
        '   - Simplemente NO uses conectores a veces. Los humanos saltan de idea sin avisar.\n\n'
        'I. CITAS (si las hay):\n'
        '   - Maximo 1 cita en todo el texto, preferible cero. No nombres autores en el texto.\n'
        '   - Reformula completamente las ideas. No copies frases de los papers.\n'
        '   - Si citas, solo [1] al final de una oracion, como apoyo, no como contenido principal.\n\n'
        'EJEMPLO DE TEXTO IA (PROHIBIDO):\n'
        '"El diseno de herramientas computacionales representa un enfoque innovador que aborda '
        'tanto desafios pedagogicos como limitaciones tecnicas. La implementacion de soluciones '
        'personalizadas permite adaptar recursos a las necesidades curriculares."\n\n'
        'EJEMPLO DE TEXTO HUMANO (OBLIGATORIO) - EN TERCERA PERSONA:\n'
        '"Se duda que las herramientas comerciales sean la respuesta definitiva. Si bien funcionan '
        'para la industria --eso hay que reconocerlo--, en el aula resultan excesivas y, '
        'lo que es peor, costosas. A ver, no es que se este en contra de todo. Simplemente se considera que '
        'desarrollar software a medida, aunque requiera esfuerzo inicial, ofrece ventajas que van '
        'mas alla del ahorro economico. Esto permite ajustar cada funcion a como realmente se ensena. '
        'Claro, esto plantea un problema: no todos los departamentos tienen capacidad para mantener estas '
        'herramientas. Quizas la solucion pasa por buscar un termino medio."\n\n'
        f'LONGITUD: {longitud_str}\n'
        f'{inst_bib}\n'
        f'{estilo_extra}'
    )

    user_prompt = (
        f"Seccion: {seccion}\n"
        f"Tema: {tema}\n\n"
        f"{contexto}"
        f"{datos_bib}"
    )

    st.divider()
    st.subheader(seccion)

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)
    temp = max(st.session_state.get("temperatura", 0.8), 1.0)
    modelo = st.session_state["modelo"]

    def llamar_api(messages, temperatura):
        max_intentos = 5
        for intento in range(1, max_intentos + 1):
            try:
                return client.chat.completions.create(
                    model=modelo,
                    messages=messages,
                    temperature=max(temperatura, 0.9),
                    stream=False,
                )
            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower() or "limit" in err.lower():
                    if intento < max_intentos:
                        time.sleep(2 ** intento)
                    else:
                        st.error("Limite de solicitudes agotado. Espera unos segundos y vuelve a intentarlo.")
                        st.stop()
                else:
                    st.error(f"Error OpenRouter: {e}")
                    st.stop()
        return None

    # Generar sin stream (mas confiable con modelos gratuitos)
    with st.spinner("Generando texto..."):
        resp = llamar_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperatura=temp,
        )

    if resp is None:
        st.stop()

    texto_limpio = limpiar(resp.choices[0].message.content or "")

    if texto_limpio:
        texto_json = json.dumps(texto_limpio, ensure_ascii=False)
        typing_html = f"""
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
        components.html(typing_html, height=350, scrolling=True)
    else:
        st.write("(Sin texto generado)")

    st.session_state["texto_redaccion"] = texto_limpio
    st.session_state["seccion_generada"] = seccion

    palabras = len(texto_limpio.split())
    st.success(f"Texto generado. Aproximadamente {palabras} palabras.")

    # Copiar al portapapeles usando pyperclip (metodo confiable)
    import base64
    
    # Generar un enlace de descarga como alternativa
    b64 = base64.b64encode(texto_limpio.encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="texto.txt" style="text-decoration:none;"><button style="background:#FF4B4B;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;">Descargar texto</button></a>'
    st.markdown(href, unsafe_allow_html=True)
    st.caption("Abre el archivo descargado y copia el contenido con Ctrl+A y Ctrl+C.")

elif st.session_state.get("texto_redaccion"):
    st.divider()
    st.subheader(st.session_state.get("seccion_generada", "Texto generado"))
    palabras = len(st.session_state["texto_redaccion"].split())
    st.caption(f"Aproximadamente {palabras} palabras.")

    import base64
    b64 = base64.b64encode(st.session_state["texto_redaccion"].encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="texto.txt" style="text-decoration:none;"><button style="background:#FF4B4B;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;">Descargar texto</button></a>'
    st.markdown(href, unsafe_allow_html=True)
    st.caption("Abre el archivo descargado y copia el contenido con Ctrl+A y Ctrl+C.")

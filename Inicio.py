import streamlit as st

st.set_page_config(page_title="Lu Writes", layout="wide", initial_sidebar_state="expanded")

st.title("Lu Writes")
st.markdown("*Redaccion academica asistida por inteligencia artificial.*")
st.divider()

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    st.subheader("Pagina 01 — Configuracion")
    st.write("Define el modelo, la temperatura y los parametros globales. Se configura una vez por sesion.")
with c2:
    st.subheader("Pagina 02 — Redaccion")
    st.write("Genera secciones academicas desde tus notas. Sube un BibTeX y Lu integrara la literatura con citas correctas.")
with c3:
    st.subheader("Pagina 03 — Bibliografia")
    st.write("Genera exclusivamente listas de referencias en IEEE, APA 7 u otros formatos. Texto y bibliografia siempre separados.")

st.divider()
st.info("Usa el menu lateral para navegar. Empieza por Configuracion.")

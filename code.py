import io
import streamlit as st
from gtts import gTTS

# idioma -> (código, sotaque/tld)
IDIOMAS = {
    "English (US)": ("en", "com"),
    "English (UK)": ("en", "co.uk"),
    "Português (PT)": ("pt", "pt"),
    "Português (BR)": ("pt", "com.br"),
    "Français": ("fr", "fr"),
}

st.set_page_config(page_title="Leitor multilíngue", page_icon="🔊")
st.title("🔊 Leitor multilíngue")

idioma = st.selectbox("Idioma", list(IDIOMAS.keys()))
texto = st.text_area("Texto para ler", height=200)
lento = st.checkbox("Leitura lenta (bom para treino)")


@st.cache_data(show_spinner=False)
def gerar_audio(texto, lang, tld, lento):
    buf = io.BytesIO()
    gTTS(texto, lang=lang, tld=tld, slow=lento).write_to_fp(buf)
    return buf.getvalue()


if st.button("Ler em voz alta"):
    if not texto.strip():
        st.warning("Escreva ou cole um texto primeiro.")
    else:
        lang, tld = IDIOMAS[idioma]
        try:
            st.audio(gerar_audio(texto, lang, tld, lento), format="audio/mp3")
        except Exception as e:
            st.error(f"Não foi possível gerar o áudio: {e}")
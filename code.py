import io
import time

import streamlit as st
from gtts import gTTS

try:
    from google import genai
except ImportError:
    genai = None

# ----------------------------- Configuração -----------------------------
MODELO = "gemini-2.5-flash-lite"  # leve = mais quota no plano gratuito

IDIOMAS = {
    "English (US)": ("en", "com", "English"),
    "English (UK)": ("en", "co.uk", "English"),
    "Português (PT)": ("pt", "pt", "Português de Portugal"),
    "Português (BR)": ("pt", "com.br", "Português do Brasil"),
    "Français": ("fr", "fr", "Français"),
    "中文 (Mandarim)": ("zh-CN", "com", "Mandarim (chinês simplificado)"),
    "한국어 (Coreano)": ("ko", "com", "Coreano"),
    "Afrikaans": ("af", "com", "Afrikaans"),
    "Kiswahili (Swahili)": ("sw", "com", "Swahili"),
    "Türkçe (Turco)": ("tr", "com", "Turco"),
}

DESTINOS = [
    "English",
    "Português",
    "Français",
    "Mandarim (chinês simplificado)",
    "Coreano",
    "Afrikaans",
    "Swahili",
    "Turco",
]

st.set_page_config(page_title="Leitor multilíngue", page_icon="🔊")
st.title("🔊 Leitor multilíngue")
st.caption(
    "Leitura em voz alta e assistente de IA em inglês, português, francês, "
    "mandarim, coreano, afrikaans, swahili e turco"
)


# ------------------------------- Funções --------------------------------
@st.cache_data(show_spinner=False)
def gerar_audio(texto, lang, tld, lento):
    buf = io.BytesIO()
    gTTS(texto, lang=lang, tld=tld, slow=lento).write_to_fp(buf)
    return buf.getvalue()


def obter_cliente():
    if genai is None:
        return None
    try:
        chave = st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None
    return genai.Client(api_key=chave)


@st.cache_data(show_spinner=False, ttl=3600)
def perguntar_ia(prompt):
    """Chama o Gemini com retry (backoff) e cache para poupar quota."""
    cliente = obter_cliente()
    if cliente is None:
        return "⚠️ Chave GEMINI_API_KEY não configurada nos Secrets."

    espera = 2
    for tentativa in range(3):
        try:
            resp = cliente.models.generate_content(model=MODELO, contents=prompt)
            return resp.text or "Sem resposta."
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower():
                if tentativa < 2:
                    time.sleep(espera)
                    espera *= 2
                    continue
                return (
                    "⚠️ Limite de uso da API atingido. "
                    "Tente novamente daqui a alguns minutos."
                )
            return f"⚠️ Erro da API: {msg[:200]}"
    return "⚠️ Não foi possível obter resposta."


# ------------------------------ Interface -------------------------------
idioma = st.selectbox("Idioma do texto", list(IDIOMAS.keys()))
lang, tld, nome_idioma = IDIOMAS[idioma]

texto = st.text_area("Texto", height=200, placeholder="Escreva ou cole o texto aqui...")
lento = st.checkbox("Leitura lenta (bom para treino)")

aba_ler, aba_ia = st.tabs(["🔊 Ler em voz alta", "🤖 Assistente IA"])

with aba_ler:
    if st.button("Ler em voz alta", type="primary"):
        if not texto.strip():
            st.warning("Escreva ou cole um texto primeiro.")
        else:
            try:
                audio = gerar_audio(texto.strip(), lang, tld, lento)
                st.audio(audio, format="audio/mp3")
                st.download_button(
                    "⬇️ Baixar áudio", audio, file_name="leitura.mp3", mime="audio/mpeg"
                )
            except Exception as e:
                st.error(f"Não foi possível gerar o áudio: {e}")

with aba_ia:
    acao = st.radio(
        "O que deseja?",
        ["Explicar o texto", "Traduzir", "Corrigir erros", "Fazer uma pergunta"],
        horizontal=True,
    )

    destino = None
    pergunta = ""
    if acao == "Traduzir":
        destino = st.selectbox("Traduzir para", DESTINOS)
    if acao == "Fazer uma pergunta":
        pergunta = st.text_input("A sua pergunta sobre o texto")

    if st.button("Executar"):
        if not texto.strip():
            st.warning("Escreva ou cole um texto primeiro.")
        elif acao == "Fazer uma pergunta" and not pergunta.strip():
            st.warning("Escreva a sua pergunta.")
        else:
            if acao == "Explicar o texto":
                prompt = (
                    f"Explica de forma simples o seguinte texto em {nome_idioma}. "
                    f"Responde em {nome_idioma}.\n\nTexto:\n{texto}"
                )
            elif acao == "Traduzir":
                prompt = (
                    f"Traduz o seguinte texto para {destino}. "
                    f"Devolve apenas a tradução.\n\nTexto:\n{texto}"
                )
            elif acao == "Corrigir erros":
                prompt = (
                    f"Corrige a gramática e a ortografia do texto em {nome_idioma}. "
                    "Mostra o texto corrigido e, depois, explica brevemente as "
                    f"correções.\n\nTexto:\n{texto}"
                )
            else:
                prompt = (
                    f"Com base no texto abaixo, responde à pergunta em {nome_idioma}."
                    f"\n\nTexto:\n{texto}\n\nPergunta: {pergunta}"
                )

            with st.spinner("A pensar..."):
                resposta = perguntar_ia(prompt)
            st.markdown(resposta)

            if not resposta.startswith("⚠️"):
                try:
                    st.caption("🔊 Ouvir a resposta")
                    st.audio(
                        gerar_audio(resposta[:3000], lang, tld, lento),
                        format="audio/mp3",
                    )
                except Exception as e:
                    st.error(f"Erro no áudio: {e}")
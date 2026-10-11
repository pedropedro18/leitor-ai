import hmac
import io
import time
from urllib.parse import quote

import streamlit as st
from gtts import gTTS

try:
    from google import genai
except ImportError:
    genai = None

# ----------------------------- Configuração -----------------------------
# Modelo principal: pode ser mudado nos Secrets com a linha  MODELO = "nome"
# Se falhar (404), o app tenta automaticamente os modelos de reserva.
MODELO_PADRAO = "gemini-3.5-flash-lite"
MODELOS_RESERVA = ["gemini-3.5-flash", "gemini-2.0-flash"]

NUMERO_WHATSAPP = "923030010"  # número para enviar o comprovativo
NUMERO_EXPRESS = "923030010"  # número para o pagamento Express
PRECO = "3.000 Kz"
INDICATIVO = "244"  # Angola

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

if "acesso" not in st.session_state:
    st.session_state.acesso = False
if "pedir_pagamento" not in st.session_state:
    st.session_state.pedir_pagamento = False


# ------------------------------- Acesso ---------------------------------
def codigos_validos():
    try:
        return [str(c).strip().upper() for c in st.secrets["CODIGOS_ACESSO"]]
    except Exception:
        return []


def codigo_correto(digitado):
    digitado = digitado.strip().upper()
    return any(hmac.compare_digest(digitado, c) for c in codigos_validos())


def painel_pagamento():
    """Mostra as instruções de pagamento e o campo do código."""
    st.warning("🔒 Para usar o leitor precisa de um código de acesso.")
    st.markdown(
        f"""
*Como obter o código:*
1. Faça o pagamento de *{PRECO}* por *Express* para *{NUMERO_EXPRESS}*.
2. Envie o *comprovativo* pelo WhatsApp.
3. Receberá o seu *código de acesso*. Cole-o abaixo.
"""
    )
    msg = quote(
        f"Olá! Fiz o pagamento de {PRECO} por Express para o Leitor multilíngue. "
        "Segue o comprovativo. Podem enviar-me o código de acesso?"
    )
    st.link_button(
        "📲 Enviar comprovativo no WhatsApp",
        f"https://wa.me/{INDICATIVO}{NUMERO_WHATSAPP}?text={msg}",
    )

    codigo = st.text_input("Código de acesso", type="password", key="campo_codigo")
    if st.button("Validar código"):
        if codigo_correto(codigo):
            st.session_state.acesso = True
            st.session_state.pedir_pagamento = False
            st.rerun()
        else:
            st.error("Código inválido. Confira e tente novamente.")


def exigir_acesso():
    """True se o utilizador já tem acesso; senão mostra o painel de pagamento."""
    if st.session_state.acesso:
        return True
    st.session_state.pedir_pagamento = True
    return False


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


def lista_de_modelos():
    try:
        principal = str(st.secrets["MODELO"]).strip()
    except Exception:
        principal = MODELO_PADRAO
    modelos = [principal] + [m for m in MODELOS_RESERVA if m != principal]
    return modelos


@st.cache_data(show_spinner=False, ttl=3600)
def perguntar_ia(prompt):
    """Chama o Gemini com cache, retry (429) e modelos de reserva (404)."""
    cliente = obter_cliente()
    if cliente is None:
        return "⚠️ Chave GEMINI_API_KEY não configurada nos Secrets."

    ultimo_erro = ""
    for modelo in lista_de_modelos():
        espera = 2
        for tentativa in range(3):
            try:
                resp = cliente.models.generate_content(model=modelo, contents=prompt)
                return resp.text or "Sem resposta."
            except Exception as e:
                msg = str(e)
                ultimo_erro = msg
                if "429" in msg or "quota" in msg.lower():
                    if tentativa < 2:
                        time.sleep(espera)
                        espera *= 2
                        continue
                    return (
                        "⚠️ Limite de uso da API atingido. "
                        "Tente novamente daqui a alguns minutos."
                    )
                if "404" in msg or "NOT_FOUND" in msg:
                    break  # tenta o modelo seguinte
                return f"⚠️ Erro da API: {msg[:200]}"
    return f"⚠️ Nenhum modelo disponível. Último erro: {ultimo_erro[:200]}"


# ------------------------------ Interface -------------------------------
idioma = st.selectbox("Idioma do texto", list(IDIOMAS.keys()))
lang, tld, nome_idioma = IDIOMAS[idioma]

texto = st.text_area("Texto", height=200, placeholder="Escreva ou cole o texto aqui...")
lento = st.checkbox("Leitura lenta (bom para treino)")

aba_ler, aba_ia, aba_priv = st.tabs(
    ["🔊 Ler em voz alta", "🤖 Assistente IA", "🔐 Privacidade"]
)

with aba_ler:
    if st.button("Ler em voz alta", type="primary"):
        if not texto.strip():
            st.warning("Escreva ou cole um texto primeiro.")
        elif exigir_acesso():
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
        elif exigir_acesso():
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

with aba_priv:
    st.subheader("Política de privacidade")
    st.markdown(
        """
*Que dados usamos*
- O texto que escreve ou cola, apenas para gerar o áudio ou a resposta da IA.
- O código de acesso, apenas para validar a sua entrada.

*O que fazemos com eles*
- *Não guardamos* os seus textos em nenhuma base de dados nem os usamos para outros fins.
- *Não vendemos, não partilhamos e não cedemos* os seus dados a terceiros para publicidade ou qualquer outro fim.
- O comprovativo de pagamento enviado pelo WhatsApp serve só para confirmar o pagamento e enviar o código.

*Serviços técnicos necessários*
Para funcionar, o texto é enviado de forma temporária aos serviços da Google que
geram a voz (síntese de voz) e as respostas de IA (Gemini). Esses serviços
processam o texto apenas para devolver o resultado, e têm as suas próprias
políticas de privacidade.

*Os seus direitos*
Pode pedir esclarecimentos ou a eliminação do comprovativo enviado, contactando-nos pelo WhatsApp.
"""
    )

# O painel de pagamento aparece quando o utilizador tenta usar sem código
if st.session_state.pedir_pagamento and not st.session_state.acesso:
    st.divider()
    painel_pagamento()
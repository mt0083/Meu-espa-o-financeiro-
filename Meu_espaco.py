import streamlit as st
import hashlib
import sqlite3
import uuid
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
import re

# ==============================================
# ⚙️ CONFIGURAÇÃO — 🏡 MEU ESPAÇO FINANCEIRO
# ==============================================
st.set_page_config(
    page_title="Meu Espaço Financeiro",
    page_icon="🏡",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "🏡 Meu Espaço Financeiro — Simples, tranquilo e seu espaço.",
        'Get Help': None,
        'Report a bug': None
    }
)

# ==============================================
# 🎨 ESTILO CALMO — CORES SUAVES
# ==============================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #f0f4f8 0%, #e2e8f0 100%);
    color: #1e293b;
}
h1, h2, h3 {color: #2c5282; font-weight: 500;}
.caixa {
    background: white;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    max-width: 420px;
    margin: 1rem auto;
}
.stButton > button {
    width: 100%;
    border-radius: 12px;
    height: 3rem;
    font-size: 1.05rem;
    font-weight: 500;
    background: #3b82f6;
    color: white;
    border: none;
}
.stButton > button:hover {background: #2563eb;}
.stTextInput > div > div > input,
.stTextArea > div > textarea {
    border-radius: 8px;
    border: 1px solid #cbd5e1;
    padding: 0.75rem;
    font-size: 1rem;
    background: white;
    color: #1e293b;
}
.rodape {
    text-align: center;
    margin-top: 3rem;
    color: #64748b;
    font-size: 0.9rem;
}
#MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================================
# 📧 CONFIGURAÇÃO DE E-MAIL
# ==============================================
CONFIG_EMAIL = {
    "remetente": "seu-email@gmail.com",
    "senha_app": "sua-senha-de-app-aqui",
    "smtp_servidor": "smtp.gmail.com",
    "smtp_porta": 587,
    "url_app": "http://localhost:8501"
}

# ==============================================
# 🗄️ BANCO DE DADOS
# ==============================================
DB_PATH = "meu_espaco_financeiro.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            data_cadastro TEXT NOT NULL,
            ultimo_acesso TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS preferencias (
            usuario_id TEXT PRIMARY KEY,
            ativos_favoritos TEXT,
            capital_total REAL DEFAULT 10000,
            risco_por_operacao REAL DEFAULT 2.0,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS recuperacao_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            criado_em TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            usado INTEGER DEFAULT 0,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==============================================
# 🔒 FUNÇÕES DE SEGURANÇA
# ==============================================
def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def validar_email(email: str) -> bool:
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def gerar_id_usuario() -> str:
    return str(uuid.uuid4())

def gerar_token_seguro() -> str:
    return secrets.token_hex(16)

# ==============================================
# 📧 ENVIAR E-MAIL
# ==============================================
def enviar_email(destinatario: str, assunto: str, mensagem: str) -> tuple[bool, str]:
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG_EMAIL['remetente']
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'html'))
        servidor = smtplib.SMTP(CONFIG_EMAIL['smtp_servidor'], CONFIG_EMAIL['smtp_porta'])
        servidor.starttls()
        servidor.login(CONFIG_EMAIL['remetente'], CONFIG_EMAIL['senha_app'])
        servidor.sendmail(CONFIG_EMAIL['remetente'], destinatario, msg.as_string())
        servidor.quit()
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, "Não foi possível enviar o e-mail. Tente novamente mais tarde."

# ==============================================
# 🔑 RECUPERAÇÃO DE SENHA
# ==============================================
def solicitar_recuperacao(email: str) -> tuple[bool, str]:
    email = email.lower().strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nome FROM usuarios WHERE email = ?", (email,))
    usuario = c.fetchone()
    if not usuario:
        conn.close()
        return True, "Se esse e-mail estiver cadastrado, você receberá um link para redefinir sua senha em alguns instantes 💛"
    usuario_id, nome = usuario
    token = gerar_token_seguro()
    agora = datetime.now().isoformat()
    expira = (datetime.now() + timedelta(minutes=15)).isoformat()
    c.execute("UPDATE recuperacao_senha SET usado = -1 WHERE usuario_id = ? AND usado = 0", (usuario_id,))
    c.execute('''
        INSERT INTO recuperacao_senha (usuario_id, token, criado_em, expira_em)
        VALUES (?, ?, ?, ?)
    ''', (usuario_id, token, agora, expira))
    conn.commit()
    conn.close()
    link = f"{CONFIG_EMAIL['url_app']}?token={token}&email={email}"
    html = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 500px; padding: 20px;">
        <div style="background: #f8fafc; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0;">
            <h2 style="color: #3b82f6; text-align: center;">🔑 Esqueceu sua senha?</h2>
            <p>Olá, <strong>{nome}</strong>!</p>
            <p>Recebemos um pedido para criar uma nova senha para sua conta.</p>
            <p style="text-align: center; margin: 25px 0;">
                <a href="{link}" style="background: #3b82f6; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 16px; display: inline-block;">
                    Criar nova senha
                </a>
            </p>
            <p style="color: #64748b; font-size: 14px;">
                ⏰ Esse link vale por <strong>15 minutos</strong>.<br>
                Se não foi você que pediu, pode ignorar esse e-mail — sua senha continua a mesma!
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 13px; color: #94a3b8;">Atenciosamente,<br>Equipe do Meu Espaço Financeiro 🏡</p>
        </div>
    </body></html>
    """
    enviar_email(email, "🔑 Redefinir sua senha", html)
    return True, "Pronto! Verifique seu e-mail — inclusive a caixa de Spam, tá? 💛"

def validar_token(token: str, email: str) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    agora = datetime.now().isoformat()
    c.execute('''
        SELECT rs.usuario_id, rs.expira_em, rs.usado
        FROM recuperacao_senha rs
        JOIN usuarios u ON rs.usuario_id = u.id
        WHERE rs.token = ? AND u.email = ?
        ORDER BY rs.criado_em DESC LIMIT 1
    ''', (token, email.lower().strip()))
    res = c.fetchone()
    conn.close()
    if not res:
        return False, "Esse link não é válido. Peça um novo, por favor."
    usuario_id, expira_em, usado = res
    if usado == 1:
        return False, "Esse link já foi usado. Peça um novo link."
    if agora > expira_em:
        return False, "Esse link já expirou. Peça um novo, é rápido!"
    return True, usuario_id

def redefinir_senha(token: str, email: str, nova_senha: str) -> tuple[bool, str]:
    if len(nova_senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres, tá?"
    valido, resp = validar_token(token, email)
    if not valido:
        return False, resp
    usuario_id = resp
    senha_hash = hash_senha(nova_senha)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (senha_hash, usuario_id))
    c.execute("UPDATE recuperacao_senha SET usado = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return True, "Pronto! Sua senha foi atualizada com sucesso. Agora é só fazer login com a senha nova. 💛"

# ==============================================
# 👤 FUNÇÕES DE USUÁRIO
# ==============================================
def criar_usuario(nome: str, email: str, senha: str) -> tuple[bool, str]:
    if not nome.strip():
        return False, "Por favor, digite seu nome."
    if not validar_email(email):
        return False, "Esse e-mail não parece estar certo. Pode conferir?"
    if len(senha) < 6:
        return False, "Para ficar mais seguro, a senha precisa ter pelo menos 6 letras ou números."
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        usuario_id = gerar_id_usuario()
        c.execute('''
            INSERT INTO usuarios (id, nome, email, senha_hash, data_cadastro)
            VALUES (?, ?, ?, ?, ?)
        ''', (usuario_id, nome.strip(), email.lower().strip(), hash_senha(senha), datetime.now().isoformat()))
        c.execute('''
            INSERT INTO preferencias (usuario_id, ativos_favoritos, capital_total)
            VALUES (?, ?, ?)
        ''', (usuario_id, json.dumps(["PETR4.SA", "VALE3.SA", "ITUB4.SA"]), 10000.0))
        conn.commit()
        return True, "Que bom que você chegou! 🎉 Sua conta foi criada. Agora é só fazer login."
    except sqlite3.IntegrityError:
        return False, "Esse e-mail já está cadastrado. Quer fazer login?"
    finally:
        conn.close()

def verificar_login(email: str, senha: str) -> tuple[bool, dict | str]:
    email = email.lower().strip()
    senha_hash = hash_senha(senha)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nome, email FROM usuarios WHERE email = ? AND senha_hash = ?", (email, senha_hash))
    res = c.fetchone()
    conn.close()
    if not res:
        return False, "E-mail ou senha não conferem. Pode conferir, por favor?"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?", (datetime.now().isoformat(), res[0]))
    conn.commit()
    conn.close()
    return True, {"id": res[0], "nome": res[1], "email": res[2]}

def carregar_preferencias(usuario_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ativos_favoritos, capital_total FROM preferencias WHERE usuario_id = ?", (usuario_id,))
    res = c.fetchone()
    conn.close()
    if res:
        return {
            "ativos_favoritos": json.loads(res[0]) if res[0] else ["PETR4.SA", "VALE3.SA", "ITUB4.SA"],
            "capital_total": res[1]
        }
    return {"ativos_favoritos": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"], "capital_total": 10000.0}

# ==============================================
# 📱 TELA DE RECUPERAÇÃO DE SENHA
# ==============================================
def tela_recuperacao():
    params = st.query_params
    token = params.get("token")
    email = params.get("email")
    st.markdown('<div class="caixa">', unsafe_allow_html=True)
    if token and email:
        st.subheader("🔑 Criar nova senha")
        st.write("Digite a nova senha que você quer usar.")
        valido, mensagem = validar_token(token, email)
        if not valido:
            st.warning(mensagem)
            st.write("Sem problemas! É só pedir um link novo aqui embaixo 👇")
            if st.button("🔄 Pedir novo link"):
                st.query_params.clear()
                st.rerun()
        else:
            with st.form("nova_senha"):
                senha1 = st.text_input("Nova senha", type="password", placeholder="Mínimo 6 caracteres")
                senha2 = st.text_input("Repita a senha", type="password", placeholder="Digite de novo")
                alterar = st.form_submit_button("✅ Salvar nova senha")
                if alterar:
                    if not senha1 or not senha2:
                        st.info("Por favor, preencha os dois campos, tá? 💛")
                    elif senha1 != senha2:
                        st.warning("As senhas não ficaram iguais. Pode conferir?")
                    else:
                        ok, msg = redefinir_senha(token, email, senha1)
                        if ok:
                            st.success(msg)
                            st.query_params.clear()
                            if st.button("🔑 Ir para o login"):
                                st.rerun()
                        else:
                            st.error(msg)
    else:
        st.subheader("🔑 Esqueci minha senha")
        st.write("Sem problemas! Digite seu e-mail que vamos te ajudar. 💛")
        with st.form("pedir_link"):
            email_rec = st.text_input("Seu e-mail cadastrado", placeholder="seu@email.com")
            enviar = st.form_submit_button("📤 Me mandar o link")
            if enviar:
                if not email_rec:
                    st.info("Digite seu e-mail, por favor.")
                elif not validar_email(email_rec):
                    st.warning("Esse e-mail não parece certo. Pode conferir?")
                else:
                    ok, msg = solicitar_recuperacao(email_rec)
                    st.success(msg)
    st.markdown("---")
    if st.button("🔐 Voltar para o login"):
        st.query_params.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="rodape">🏡 Meu Espaço Financeiro — Simples e tranquilo</div>', unsafe_allow_html=True)

# ==============================================
# 📱 TELA DE LOGIN
# ==============================================
def tela_login():
    st.markdown('<div class="caixa">', unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🏡 Meu Espaço Financeiro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Simples, tranquilo e seu espaço.</p>", unsafe_allow_html=True)
    aba_entrar, aba_cadastrar = st.tabs(["🔐 Entrar", "📝 Criar conta"])
    with aba_entrar:
        with st.form("entrar"):
            email = st.text_input("Seu e-mail", placeholder="seu@email.com")
            senha = st.text_input("Sua senha", type="password", placeholder="Digite sua senha")
            entrar = st.form_submit_button("🔑 Entrar")
            if entrar:
                if not email or not senha:
                    st.info("Por favor, preencha e-mail e senha. 💛")
                else:
                    ok, resp = verificar_login(email, senha)
                    if ok:
                        st.session_state.usuario = resp
                        st.session_state.logado = True
                        st.success(f"Bem-vindo de volta, {resp['nome']}! 🤗")
                        st.rerun()
                    else:
                        st.warning(resp)
        st.markdown("---")
        if st.button("🔑 Esqueci minha senha"):
            st.session_state.tela_recuperacao = True
            st.rerun()
    with aba_cadastrar:
        with st.form("cadastrar"):
            nome = st.text_input("Seu nome", placeholder="Como você quer ser chamado?")
            email = st.text_input("Seu e-mail", placeholder="seu@email.com")
            senha1 = st.text_input("Criar uma senha", type="password", placeholder="Mínimo 6 caracteres")
            senha2 = st.text_input("Repetir senha", type="password", placeholder="Digite de novo")
            cadastrar = st.form_submit_button("📝 Criar minha conta")
            if cadastrar:
                if not nome or not email or not senha1 or not senha2:
                    st.info("Por favor, preencha todos os campos, tá? 💛")
                elif senha1 != senha2:
                    st.warning("As senhas não ficaram iguais. Pode conferir?")
                else:
                    ok, msg = criar_usuario(nome, email, senha1)
                    if ok:
                        st.success(msg)
                    else:
                        st.warning(msg)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="rodape">🏡 Seus dados ficam protegidos. Senha sempre criptografada.</div>', unsafe_allow_html=True)

# ==============================================
# 🛡️ CONTROLE DE TELAS
# ==============================================
params = st.query_params
if "token" in params and "email" in params:
    tela_recuperacao()
    st.stop()
if "tela_recuperacao" in st.session_state and st.session_state.tela_recuperacao:
    tela_recuperacao()
    if st.button("🔐 Voltar para o login"):
        del st.session_state.tela_recuperacao
        st.rerun()
    st.stop()
if "logado" not in st.session_state or not st.session_state.logado:
    tela_login()
    st.stop()

# ==============================================
# ✅ ÁREA PRINCIPAL — USUÁRIO LOGADO
# ==============================================
if "preferencias" not in st.session_state:
    st.session_state.preferencias = carregar_preferencias(st.session_state.usuario["id"])

with st.sidebar:
    st.markdown(f"""
    <div style="padding: 1rem; background: #f1f5f9; border-radius: 10px; margin-bottom: 1rem;">
        <strong>👤 {st.session_state.usuario['nome']}</strong><br>
        <span style="font-size: 0.85rem; color: #64748b;">{st.session_state.usuario['email']}</span>
    </div>
    """, unsafe_allow_html=True)
    pagina = st.radio("O que você quer ver?", [
        "📊 Meus Investimentos",
        "💰 Meu Portfólio",
        "⚙️ Configurações",
        "🚪 Sair"
    ])
    st.divider()
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem;'>🏡 Sempre tranquilo</p>", unsafe_allow_html=True)

if pagina == "🚪 Sair":
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.query_params.clear()
    st.success("Até logo! Volte quando quiser. 👋")
    st.rerun()
elif pagina == "⚙️ Configurações":
    st.subheader("⚙️ Suas preferências")
    st.write("Aqui você pode ajustar como o app funciona para você. 💛")
    pref = st.session_state.preferencias
    novos_ativos = st.text_area("Seus ativos favoritos", value="\n".join(pref["ativos_favoritos"]), height=120)
    capital = st.number_input("Seu capital total (R$)", value=pref["capital_total"], min_value=0.0)
    if st.button("💾 Salvar minhas preferências"):
        st.success("Pronto! Suas preferências foram salvas. ✨")
        st.rerun()
elif pagina == "📊 Meus Investimentos":
    st.subheader("📊 Meus Investimentos")
    st.write("Aqui você acompanha seus ativos. Tranquilo e simples. 💛")
    st.info("Em breve: gráficos e preços em tempo real! 📈")
elif pagina == "💰 Meu Portfólio":
    st.subheader("💰 Meu Portfólio")
    st.write("Visão geral dos seus investimentos.")
    st.metric("💵 Capital total", f"R$ {st.session_state.preferencias['capital_total']:,.2f}")
    st.info("Em breve: distribuição e acompanhamento de cada ativo! 📊")

st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.9rem;">
    🏡 Meu Espaço Financeiro — Feito com carinho para ser simples e tranquilo.<br>
    ⚠️ Este app é uma ferramenta de acompanhamento, <strong>não é recomendação de investimento</strong>. Investimentos têm riscos.
</div>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import os
import altair as alt
import sqlite3
import json

# Configuração inicial
st.set_page_config(page_title="Duelo das Idades", layout="wide")

# 1️⃣ Banco de dados
DB_FILE = "predicoes.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS predicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idade_usuario INTEGER,
                profissao TEXT,
                respostas TEXT
            )
        """)
        conn.commit()

def salvar_predicao(idade_usuario, profissao, respostas):
    respostas_json = json.dumps(respostas)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO predicoes (idade_usuario, profissao, respostas) VALUES (?, ?, ?)",
            (idade_usuario, profissao, respostas_json)
        )
        conn.commit()

# Inicializa o banco
init_db()

# 2️⃣ Carregar CSV
dados = pd.read_csv('dados.csv')
if 'imagem' not in dados.columns:
    dados['imagem'] = [f"{i+1}.png" for i in range(len(dados))]
num_imagens = len(dados)

# 3️⃣ Inicializar estados
if 'pagina' not in st.session_state:
    st.session_state.pagina = "inicio"
if 'idade_usuario' not in st.session_state:
    st.session_state.idade_usuario = None
if 'profissao' not in st.session_state:
    st.session_state.profissao = ""
if 'respostas_usuario' not in st.session_state:
    st.session_state.respostas_usuario = [None] * num_imagens

# 4️⃣ Funções de navegação
def ir_para_respostas():
    st.session_state.pagina = "respostas"
def ir_para_resultado():
    st.session_state.pagina = "resultado"
def recomeçar():
    st.session_state.pagina = "inicio"
    st.session_state.idade_usuario = None
    st.session_state.profissao = ""
    st.session_state.respostas_usuario = [None] * num_imagens

# --------------------------
# Página INICIAL
# --------------------------
if st.session_state.pagina == "inicio":
    st.title('🎯 Duelo das Idades 👥🤖')
    st.subheader('Quem adivinha melhor a idade? Você ou a máquina?')

    with st.form("form_inicio"):
        idade = st.number_input('Sua idade', min_value=0, max_value=120, step=1)
        profissao = st.text_input('Sua profissão')
        enviar = st.form_submit_button('Começar')

        if enviar:
            st.session_state.idade_usuario = idade
            st.session_state.profissao = profissao
            ir_para_respostas()

# --------------------------
# Página de RESPOSTAS
# --------------------------
elif st.session_state.pagina == "respostas":
    st.title('📸 Estime as Idades nas Fotos')
    st.caption(f"Idade informada: {st.session_state.idade_usuario} | Profissão: {st.session_state.profissao}")

    st.markdown("---")
    st.write("📝 Digite seu palpite de idade para cada foto:")

    # Grid de imagens com inputs e bordas
    for i in range(0, num_imagens, 2):
        cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx < num_imagens:
                with cols[j].container(border=True):
                    st.image(
                        os.path.join('images', dados.loc[idx, 'imagem']),
                        width=300,
                        caption=f"Foto {idx+1}"
                    )
                    valor = st.number_input(
                        f"Seu palpite para Foto {idx+1}",
                        min_value=1,
                        max_value=120,
                        key=f"input_{idx}",
                        value=st.session_state.respostas_usuario[idx] if st.session_state.respostas_usuario[idx] else 18
                    )
                    st.session_state.respostas_usuario[idx] = valor

    st.markdown("---")
    if st.button("✅ Finalizar e Ver Resultado"):
        if any([resp is None or resp < 1 for resp in st.session_state.respostas_usuario]):
            st.warning("⚠️ Por favor, preencha TODAS as idades (mínimo 1) antes de finalizar!")
        else:
            ir_para_resultado()

# --------------------------
# Página de RESULTADO
# --------------------------
elif st.session_state.pagina == "resultado":
    st.title('📊 Resultado do Desafio')

    # Salvar no banco
    salvar_predicao(
        st.session_state.idade_usuario,
        st.session_state.profissao,
        st.session_state.respostas_usuario
    )

    # Calcular MAE do usuário
    erros_usuario = [abs(real - pred) for real, pred in zip(dados['idade_real'], st.session_state.respostas_usuario)]
    mae_usuario = sum(erros_usuario) / len(erros_usuario)

    maes_modelos = {}
    for modelo in ['modelo1_pred', 'modelo2_pred', 'modelo3_pred']:
        mae = (abs(dados[modelo] - dados['idade_real'])).mean()
        maes_modelos[modelo] = mae

    st.success(f"✅ Seu erro médio (MAE): **{mae_usuario:.2f} anos**")

    tabela_resultados = pd.DataFrame({
        'Modelo': ['Você'] + list(maes_modelos.keys()),
        'MAE': [mae_usuario] + list(maes_modelos.values())
    })
    st.subheader('📈 Comparação com os Modelos:')
    st.table(tabela_resultados)

    chart = alt.Chart(tabela_resultados).mark_bar().encode(
        x=alt.X('Modelo', sort=None),
        y='MAE',
        color=alt.condition(
            alt.datum.Modelo == 'Você',
            alt.value('orange'),
            alt.value('steelblue')
        )
    ).properties(
        width=600,
        height=400,
        title='Erro Médio Absoluto (MAE) - Comparação'
    )
    st.altair_chart(chart, use_container_width=True)

    st.success("✅ Experimento finalizado. Compare seu desempenho com a IA!")
    if st.button("🔄 Recomeçar"):
        recomeçar()

import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# ==============================================================================
# 1. FUNÇÕES DE NORMALIZAÇÃO E LEITURA
# ==============================================================================

def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    nome = str(nome).lower().strip()
    nome = unidecode(nome)
    nome = re.sub(r'[^a-z0-9 ]', '', nome)
    nome = re.sub(r'\s+', ' ', nome)
    return nome

def ler_csv(file):
    file.seek(0)
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ';'
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')

@st.cache_data
def carregar_depara(caminho="depara.csv"):
    try:
        if caminho.endswith(".csv"):
            df = pd.read_csv(caminho)
        else:
            df = pd.read_excel(caminho)
        df.columns = df.columns.str.strip().str.lower()
        df['veiculo_soudview'] = df['veiculo_soudview'].apply(normalizar_nome)
        df['veiculos boxnet'] = df['veiculos boxnet'].apply(normalizar_nome)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar De/Para: {e}")
        return pd.DataFrame(columns=['veiculo_soudview', 'veiculos boxnet'])

# ==============================================================================
# 2. FUNÇÕES DE MAPEAMENTO E COMPARAÇÃO
# ==============================================================================

def mapear_veiculo(nome, df_depara, veiculos_principais, limite_confiança=85):
    nome_norm = normalizar_nome(nome)
    if not nome_norm:
        return "NOME VAZIO", None, "⚪ Vazio"

    encontrado = df_depara[df_depara['veiculo_soudview'] == nome_norm]
    if not encontrado.empty:
        return encontrado['veiculos boxnet'].values[0], 100, "✅ De/Para"

    candidatos = df_depara['veiculo_soudview'].tolist()
    melhor, score, _ = process.extractOne(nome_norm, candidatos, scorer=fuzz.token_sort_ratio)
    if score >= limite_confiança:
        veiculo_boxnet = df_depara[df_depara['veiculo_soudview'] == melhor]['veiculos boxnet'].values[0]
        return veiculo_boxnet, score, "🤖 Fuzzy De/Para"

    veiculos_principais_norm = [normalizar_nome(v) for v in veiculos_principais]
    melhor2, score2, _ = process.extractOne(nome_norm, veiculos_principais_norm, scorer=fuzz.token_sort_ratio)
    if score2 >= limite_confiança:
        return melhor2, score2, "🤖 Fuzzy Checking"

    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

def comparar_planilhas(df_soud, df_checking, df_depara):
    col_soud_veiculo_orig = 'veiculo_soudview'
    col_soud_data = 'data'
    col_soud_horario = 'horario'
    col_check_veiculo = 'veículo boxnet'
    col_check_data = 'data veiculação'
    col_check_horario = 'hora veiculação'

    df_soud[col_soud_veiculo_orig] = df_soud[col_soud_veiculo_orig].apply(normalizar_nome)
    veiculos_principais = df_checking[col_check_veiculo].dropna().unique().tolist()
    resultados = df_soud[col_soud_veiculo_orig].apply(
        lambda x: mapear_veiculo(x, df_depara, veiculos_principais)
    )
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]

    df_soud['data_merge'] = pd.to_datetime(df_soud[col_soud_data], errors='coerce').dt.strftime('%Y-%m-%d')
    df_checking['data_merge'] = pd.to_datetime(df_checking[col_check_data], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_soud['horario_merge'] = pd.to_datetime(df_soud[col_soud_horario], errors='coerce').dt.strftime('%H:%M')
    df_checking['horario_merge'] = pd.to_datetime(df_checking[col_check_horario], errors='coerce').dt.strftime('%H:%M')

    df_soud.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking['veiculo_merge'] = df_checking[col_check_veiculo].apply(normalizar_nome)

    relatorio = pd.merge(
        df_soud,
        df_checking,
        left_on=['veiculo_mapeado', 'data_merge', 'horario_merge'],
        right_on=['veiculo_merge', 'data_merge', 'horario_merge'],
        how='left',
        indicator=True
    )

    relatorio['status'] = np.where(relatorio['_merge'] == 'both', '✅ Encontrado no Checking', '❌ Não encontrado no Checking')
    relatorio.rename(columns={col_check_veiculo: 'veiculo_checking_original'}, inplace=True)

    colunas_finais = [
        'veiculo_soudview', 'comercial_soudview', 'data', 'horario',
        'veiculo_mapeado', 'score_similaridade', 'tipo_match', 'status'
    ]
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]

    return relatorio[colunas_existentes]

# ==============================================================================
# 3. INTERFACE STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Validador de Checking", layout="wide")
st.title("Painel de Validação de Checking 🛠️")

df_depara = carregar_depara("depara.csv")

col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Passo 1: Upload da Planilha Principal (Checking)", type=["csv", "xlsx", "xls"])
with col2:
    soud_file = st.file_uploader("Passo 2: Upload da Planilha Soudview", type=["xlsx", "xls"])

campanha_selecionada = None
df_soud = None

if soud_file:
    try:
        df_soud = pd.read_excel(soud_file)
        df_soud.columns = df_soud.columns.str.strip().str.lower()

        if 'veiculo_soudview' not in df_soud.columns or 'comercial_soudview' not in df_soud.columns:
            st.error("A planilha Soudview não possui as colunas esperadas.")
            df_soud = None
        else:
            campanhas = sorted(df_soud['comercial_soudview'].dropna().unique())
            opcoes_campanha = ["**TODAS AS CAMPANHAS**"] + campanhas
            campanha_selecionada = st.selectbox("Passo 3: Selecione a campanha para analisar", options=opcoes_campanha)
    except Exception as e:
        st.error(f"Erro ao processar Soudview: {e}")

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file:
        st.warning("Por favor, faça o upload das duas planilhas.")
    elif df_soud is None or df_depara.empty:
        st.error("Erro ao carregar os dados.")
    else:
        with st.spinner("Analisando dados..."):
            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            else:
                df_checking = pd.read_excel(checking_file)
            df_checking.columns = df_checking.columns.str.strip().str.lower()

            if campanha_selecionada and campanha_selecionada != "**TODAS AS CAMPANHAS**":
                df_soud_filtrado = df_soud[df_soud['comercial_soudview'] == campanha_selecionada].copy()
            else:
                df_soud_filtrado = df_soud.copy()

            if df_soud_filtrado.empty:
                st.error("Nenhuma veiculação encontrada.")
            else:
                relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking, df_depara)

                if relatorio_final.empty:
                    st.error("O relatório final está vazio.")
                else:
                    st.subheader("🎉 Relatório Final da Comparação")
                    st.dataframe(relatorio_final)

                    output = io.BytesIO()

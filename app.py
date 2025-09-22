import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# Função de normalização
def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    nome = str(nome).lower().strip()
    nome = unidecode(nome)  # remove acentos
    nome = re.sub(r'[^a-z0-9 ]', '', nome)  # remove caracteres especiais
    nome = re.sub(r'\s+', ' ', nome)  # remove espaços extras
    return nome

# Função para ler CSV
def ler_csv(file):
    file.seek(0)
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ';'
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')

# Carregar De/Para
@st.cache_data
def carregar_depara(caminho="depara.csv"):
    if caminho.endswith(".csv"):
        df = pd.read_csv(caminho)
    else:
        df = pd.read_excel(caminho)
    df.columns = df.columns.str.strip().str.lower()
    df['veiculo_soudview'] = df.get('veiculo_soudview', "").apply(normalizar_nome)
    df['veiculos boxnet'] = df.get('veiculos boxnet', "").apply(normalizar_nome)
    return df

df_depara = carregar_depara("depara.csv")

# Função de mapeamento
def mapear_veiculo(nome, df_depara, veiculos_principais, limite_confiança=80):
    nome_norm = normalizar_nome(nome)

    # 1️⃣ Procura exata no de/para
    encontrado = df_depara[df_depara['veiculo_soudview'] == nome_norm]
    if not encontrado.empty:
        return encontrado['veiculos boxnet'].values[0], None, "✅ De/Para"

    # 2️⃣ Fuzzy match no de/para
    candidatos = df_depara['veiculo_soudview'].tolist()
    melhor, score, _ = process.extractOne(nome_norm, candidatos, scorer=fuzz.token_sort_ratio)
    if score >= limite_confiança:
        veiculo_boxnet = df_depara[df_depara['veiculo_soudview'] == melhor]['veiculos boxnet'].values[0]
        return veiculo_boxnet, score, "🤖 Fuzzy De/Para"

    # 3️⃣ Fuzzy match nos veículos principais
    veiculos_principais_norm = [normalizar_nome(v) for v in veiculos_principais]
    melhor2, score2, _ = process.extractOne(nome_norm, veiculos_principais_norm, scorer=fuzz.token_sort_ratio)
    if score2 >= limite_confiança:
        return melhor2, score2, "🤖 Fuzzy Checking"

    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

# Função de comparação
def comparar_planilhas(df_soud, df_checking):
    col_veiculo = 'veículo boxnet'
    col_data = 'data veiculação'
    col_horario = 'hora veiculação'

    # Normaliza nomes da Soudview
    df_soud['veiculo_soudview'] = df_soud['veiculo_soudview'].apply(normalizar_nome)

    # Veículos principais do Checking
    veiculos_principais = df_checking[col_veiculo].dropna().unique().tolist()

    # Aplica mapeamento
    resultados = df_soud['veiculo_soudview'].apply(lambda x: mapear_veiculo(x, df_depara, veiculos_principais))
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]

    # Normaliza data/hora para merge
    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['data_norm'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['horario_norm'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time

    # Merge
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['veiculo_mapeado', 'data', 'horario'],
        right_on=[col_veiculo, 'data_norm', 'horario_norm'],
        how='left',
        indicator=True
    )
    relatorio['status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    relatorio.rename(columns={col_veiculo: 'veiculo_principal_encontrado'}, inplace=True)

    colunas_finais = [
        'veiculo_soudview', 'comercial_soudview', 'data', 'horario',
        'veiculo_mapeado', 'score_similaridade', 'tipo_match',
        'status', 'veiculo_principal_encontrado'
    ]
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]

    return relatorio[colunas_existentes]

# ---------------- STREAMLIT ----------------
st.set_page_config(page_title="Validador de Checking", layout="centered") 
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
    checking_file = st.file_uploader("Passo 1: Upload da Planilha Principal", type=["csv", "xlsx", "xls"])
    soud_file = st.file_uploader("Passo 2: Upload da Planilha Soudview", type=["xlsx", "xls"])

    campanha_selecionada = None

    if soud_file:
        from soudview import parse_soudview
        soud_file.seek(0)
        df_soud = parse_soudview(pd.read_excel(soud_file, header=None, engine=None))
        df_soud.columns = df_soud.columns.str.strip().str.lower()
        df_soud['veiculo_soudview'] = df_soud['veiculo_soudview'].apply(normalizar_nome)
        campanhas = sorted(df_soud['comercial_soudview'].unique())
        opcoes_campanha = ["**TODAS AS CAMPANHAS**"] + campanhas
        campanha_selecionada = st.selectbox("Passo 3: Selecione a campanha para analisar", options=opcoes_campanha)

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True):
        if not checking_file or not soud_file:
            st.warning("Por favor, faça o upload das duas planilhas.")
        else:
            # Carregar Checking
            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            else:
                df_checking = pd.read_excel(checking_file)
            df_checking.columns = df_checking.columns.str.strip().str.lower()

            # Filtrar campanha
            if campanha_selecionada == "**TODAS AS CAMPANHAS**":
                df_soud_filtrado = df_soud
            else:
                df_soud_filtrado = df_soud[df_soud['comercial_soudview'] == campanha_selecionada]

            if df_soud_filtrado.empty:
                st.error("Nenhuma veiculação encontrada para a campanha selecionada.")
            else:
                st.success(f"{len(df_soud_filtrado)} veiculações extraídas para a(s) campanha(s) selecionada(s)!")
                relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking)

                if not relatorio_final.empty:
                    st.subheader("🎉 Relatório Final da Comparação")
                    st.dataframe(relatorio_final)

                    # Download Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                    st.download_button(
                        "📥 Baixar Relatório Final",
                        output.getvalue(),
                        "Relatorio_Final.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

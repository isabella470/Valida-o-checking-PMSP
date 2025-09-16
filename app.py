import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz

# Tenta importar a função especializada de soudview.py
try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()
    
# ---------------- Funções ----------------
def ler_csv(file):
    file.seek(0)
    # Tenta detectar o separador, mas usa ';' como padrão se falhar
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ';'
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')


def comparar_planilhas(df_soud, df_checking):
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'
    col_campanha_checking = 'TÍTULO PEÇA'

    for col in [col_veiculo, col_data, col_horario, col_campanha_checking]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame()

    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time
    df_checking_sp['HORARIO_MINUTO'] = df_checking_sp['HORARIO_NORM'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    
    df_checking_sp['VEICULO_LIMPO'] = df_checking_sp[col_veiculo].astype(str).str.strip().str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
    df_soud['VEICULO_LIMPO'] = df_soud['Veiculo_Soudview'].astype(str).str.strip().str.upper().str.replace(r'[^A-Z0-9]', '', regex=True)
    
    veiculos_soudview = df_soud['VEICULO_LIMPO'].dropna().unique()
    veiculos_checking = df_checking_sp['VEICULO_LIMPO'].dropna().unique()

    mapa_veiculos, mapa_scores = {}, {}
    for veiculo_soud in veiculos_soudview:
        res = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.ratio)
        if res:
            match, score, _ = res
            if score >= 85:
                original_checking_name = df_checking_sp.loc[df_checking_sp['VEICULO_LIMPO'] == match, col_veiculo].iloc[0]
                mapa_veiculos[veiculo_soud] = original_checking_name
                mapa_scores[veiculo_soud] = score
            else:
                mapa_veiculos[veiculo_soud], mapa_scores[veiculo_soud] = "NÃO MAPEADO", 0
        else:
            mapa_veiculos[veiculo_soud], mapa_scores[veiculo_soud] = "NÃO MAPEADO", 0
    
    df_soud['Veiculo_Mapeado'] = df_soud['VEICULO_LIMPO'].map(mapa_veiculos)
    df_soud['Score_Mapeamento'] = df_soud['VEICULO_LIMPO'].map(mapa_scores)
    df_soud['HORARIO_MINUTO'] = df_soud['Horario'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    
    relatorio = pd.merge(df_soud, df_checking_sp, left_on=['Veiculo_Mapeado', 'HORARIO_MINUTO'], right_on=[col_veiculo, 'HORARIO_MINUTO'], how='left', indicator=True)
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    
    return relatorio[['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Score_Mapeamento', 'Status']]

# ---------------- STREAMLIT ----------------
# A MUDANÇA É AQUI: layout="wide"
st.set_page_config(page_title="Validador de Checking", layout="wide") 

st.title("Painel de Validação de Checking 🛠️")
tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])
with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
    # Use colunas para organizar melhor os uploads
    col1, col2 = st.columns(2)
    with col1:
        checking_file = st.file_uploader("Passo 1: Upload da Planilha Principal", type=["csv", "xlsx", "xls"])
        soud_file = st.file_uploader("Passo 2: Upload da Planilha Soudview", type=["xlsx", "xls"])

    campanhas_selecionadas = []
    if soud_file:
        @st.cache_data
        def carregar_e_extrair_campanhas(arquivo):
            df = parse_soudview(pd.read_excel(arquivo, header=None, engine=None))
            if not df.empty:
                return sorted(df['Comercial_Soudview'].unique())
            return []

        soud_file.seek(0)
        lista_de_campanhas = carregar_e_extrair_campanhas(soud_file)
        
        if lista_de_campanhas:
            with col2:
                campanhas_selecionadas = st.multiselect(
                    "Passo 3: Selecione as campanhas para INCLUIR",
                    options=lista_de_campanhas,
                    default=lista_de_campanhas
                )
    
    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True):
        if not checking_file or not soud_file:
            st.warning("Por favor, faça o upload dos dois arquivos para iniciar a validação.")
        elif not campanhas_selecionadas:
            st.warning("Por favor, selecione pelo menos uma campanha para analisar.")
        else:
            with st.spinner("Analisando..."):
                try:
                    soud

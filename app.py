import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from thefuzz import process, fuzz

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()

# --- FUNÇÕES GLOBAIS ---
def transformar_url_para_csv(url: str, aba: str = "Relatórios"):
    # ... (código da função sem alteração)
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except: return None

def comparar_planilhas(df_soud, df_checking):
    # Dicionário de mapeamento. ESTA É A PARTE QUE PRECISAMOS CORRIGIR.
    mapa_colunas = {
        'VEICULO_BOXNET': 'VEICULO', 
        'DATA_CONTRATACAO': 'DATA',
        'HORA_VEICULACAO': 'HORARIO', 
        'TITULO_PECA': 'COMERCIAL'
    }
    
    original_cols = df_checking.columns.tolist()
    df_checking.columns = df_checking.columns.str.strip().str.upper()
    df_checking.rename(columns=mapa_colunas, inplace=True)
    
    for col in ['VEICULO', 'DATA', 'HORARIO']:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal após o mapeamento. Colunas originais encontradas: {original_cols}")
            return pd.DataFrame()

    df_checking_sp = df_checking[df_checking['VEICULO'].str.contains("/SÃO PAULO", case=False, na=False)].copy()
    if df_checking_sp.empty:
        st.warning("Nenhum veículo de '/SÃO PAULO' foi encontrado na planilha principal para comparação.")

    df_checking_sp['DATA'] = pd.to_datetime(df_checking_sp['DATA'], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO'] = pd.to_datetime(df_checking_sp['HORARIO'], errors='coerce').dt.time

    veiculos_soudview = df_soud['Veiculo_Soudview'].unique()
    veiculos_checking = df_checking_sp['VEICULO'].unique()
    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        if pd.notna(veiculo_soud) and veiculos_checking.size > 0:
            match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
            if match and match[1] >= 80:
                mapa_veiculos[veiculo_soud] = match[0]
            else:
                mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            
    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)
    relatorio = pd.merge(df_soud, df_checking_sp, left_on=['Veiculo_Mapeado', 'Data', 'Horario'], right_on=['VEICULO', 'DATA', 'HORARIO'], how='left', indicator=True)
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    colunas_finais = ['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Status']
    return relatorio[colunas_finais]

# --- LAYOUT DO STREAMLIT ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 🛠️")

# As abas foram removidas temporariamente para focar 100% em resolver o problema da Soudview.
# Depois que funcionar, nós as adicionamos de volta em 1 minuto.
st.header("Validação Soudview (Foco na Resolução)")

link_planilha_checking = st.text_input("Passo 1: Cole o link da Planilha Principal (Checking)", key="soud_link")
soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")
debug_mode = st.checkbox("🔍 Ativar Modo Depuração", value=True, key="debug_soud") # Deixei ativado por padrão

if st.button("▶️ Iniciar Validação", use_container_width=True, key="btn_soud"):
    if link_planilha_checking and soud_file:
        with st.spinner("Analisando..."):
            df_raw_soud = pd.read_excel(soud_file, header=None)
            df_soud = parse_soudview(df_raw_soud)

            st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
            
            url_csv = transformar_url_para_csv(link_planilha_checking)
            response = requests.get(url_csv)
            df_checking = pd.read_csv(io.StringIO(response.text))
            
            # --- SUPER DEPURAÇÃO ATIVADA ---
            if debug_mode:
                st.info("--- DEPURAÇÃO DA PLANILHA PRINCIPAL (CHECKING) ---")
                st.write("Abaixo estão as 5 primeiras linhas da sua planilha principal:")
                st.dataframe(df_checking.head())
                st.write("**E estes são os nomes EXATOS das colunas que ela contém:**")
                st.code(df_checking.columns.tolist())
                st.write("--- FIM DA DEPURAÇÃO ---")
            # --------------------------------

            if not df_soud.empty:
                relatorio_final = comparar_planilhas(df_soud, df_checking)
                
                st.subheader("Resultado da Comparação")
                st.dataframe(relatorio_final)
                
                # ... (lógica de download aqui) ...

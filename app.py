import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from thefuzz import process, fuzz

# Tenta importar a função do arquivo soudview.py
try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado. Por favor, certifique-se de que ele está na mesma pasta que o app.py.")
    st.stop()

# --- FUNÇÕES GLOBAIS ---

def transformar_url_para_csv(url: str, aba: str = "Relatórios"):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except: return None

def padronizar_colunas(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# --- LAYOUT PRINCIPAL DO APP ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

# ===================================================================
# CONTEÚDO DA ABA 1: VALIDAÇÃO CHECKING
# ===================================================================
with tab1:
    st.subheader("Validação entre Planilha de Relatórios e De/Para")

    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha de Relatórios", key="checking_link_tab1")
    planilha2_file = st.file_uploader("Passo 2: Faça upload da Planilha De/Para", type=["xlsx", "xls", "csv"], key="depara_file_tab1")

    if st.button("Iniciar Validação de Checking", use_container_width=True, key="btn_checking_tab1"):
        if link_planilha1 and planilha2_file:
            with st.spinner("Lendo e validando planilhas..."):
                url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
                if url_csv is None:
                    st.error("URL da Planilha de Relatórios é inválida.")
                else:
                    try:
                        response = requests.get(url_csv)
                        response.raise_for_status()
                        df1 = pd.read_csv(io.StringIO(response.text))

                        if planilha2_file.name.endswith('.csv'):
                            df2 = pd.read_csv(planilha2_file)
                        else:
                            df2 = pd.read_excel(planilha2_file)
                        
                        df1 = padronizar_colunas(df1)
                        df2 = padronizar_colunas(df2)
                        
                        # Sua lógica de comparação aqui...
                        st.success("Arquivos da Aba 1 lidos com sucesso! Lógica de comparação a ser implementada aqui.")
                        st.dataframe(df1.head())
                        st.dataframe(df2.head())

                    except Exception as e:
                        st.error(f"Ocorreu um erro durante o processamento: {e}")
        else:
            st.warning("Por favor, preencha o link e faça o upload do arquivo.")

# ===================================================================
# CONTEÚDO DA ABA 2: VALIDAÇÃO SOUDVIEW
# ===================================================================
with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")

    link_planilha_checking_soud = st.text_input("Passo 1: Cole o link da Planilha Principal (Checking)", key="soud_link_tab2")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file_tab2")
    debug_mode = st.checkbox("🔍 Ativar Modo Depuração", key="debug_soud_tab2")

    if st.button("Iniciar Validação Soudview", use_container_width=True, key="btn_soud_tab2"):
        if link_planilha_checking_soud and soud_file:
            with st.spinner("Processando Soudview..."):
                # Leitura Robusta
                df_raw = pd.read_excel(soud_file, header=None)
                
                if debug_mode:
                    st.info("--- MODO DEPURAÇÃO ATIVO ---")
                    st.write("Dados brutos lidos da planilha Soudview:")
                    st.dataframe(df_raw)
                    st.write("--- FIM DA DEPURAÇÃO ---")

                # Parsing
                df_soud = parse_soudview(df_raw)

                if df_soud.empty:
                    st.error("Não foi possível extrair dados da Soudview. Verifique o formato do arquivo com o Modo Depuração.")
                else:
                    st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                    st.dataframe(df_soud.head())

                    # Leitura da Planilha Principal
                    url_csv_checking = transformar_url_para_csv(link_planilha_checking_soud)
                    if url_csv_checking:
                        try:
                            response = requests.get(url_csv_checking)
                            response.raise_for_status()
                            df_checking = pd.read_csv(io.StringIO(response.text))
                            
                            st.info("Planilha principal lida. Iniciando comparação...")
                            # A lógica de comparação e relatório final vai aqui
                            # Exemplo:
                            # relatorio = comparar_planilhas(df_soud, df_checking)
                            # st.dataframe(relatorio)
                            
                        except Exception as e:
                            st.error(f"Erro ao ler ou processar a planilha principal: {e}")
                    else:
                        st.error("URL da planilha principal é inválida.")
        else:
            st.warning("Por favor, preencha o link e o arquivo da Soudview.")

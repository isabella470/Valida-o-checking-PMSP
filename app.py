import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests

# Assumindo que você tem o arquivo soudview.py na mesma pasta
from soudview import parse_soudview, normalizar_hora

# =============================
# FUNÇÃO NOVA E MAIS ROBUSTA PARA LER ARQUIVOS
# =============================
def ler_planilha(uploaded_file):
    """
    Lê um arquivo enviado pelo usuário, tentando diferentes formatos (Excel, CSV)
    para evitar erros de extensão incorreta.
    """
    try:
        # Tenta ler como Excel primeiro, deixando o Pandas escolher o motor
        df = pd.read_excel(uploaded_file, engine=None)
        st.info("Arquivo lido com sucesso como uma planilha Excel.")
        return df
    except Exception as e:
        # Se falhar com o erro "zip file", é um forte indício de que é um CSV com a extensão errada
        if "zip file" in str(e):
            st.warning("⚠️ O arquivo não parece ser um Excel válido. Tentando ler como CSV...")
            try:
                # Importante: voltar ao início do arquivo para uma nova tentativa de leitura
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
                st.info("Arquivo lido com sucesso como CSV.")
                return df
            except Exception as csv_error:
                st.error(f"Falha ao tentar ler como CSV. Erro: {csv_error}")
                return None
        # Se for outro tipo de erro, mostra o erro original
        else:
            st.error(f"Erro inesperado ao ler o arquivo: {e}")
            return None

# =============================
# Função para transformar Google Sheet em CSV
# =============================
def transformar_url_para_csv(url: str, aba: str = "Relatórios") -> str:
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except:
        pass
    return None

# =============================
# Padronizar colunas
# =============================
def padronizar_colunas(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# =============================
# Streamlit Layout
# =============================
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

# =============================
# ABA 1 - Checking
# =============================
with tab1:
    st.subheader("Validação de Checking 📊")

    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Relatórios)")
    planilha2_file = st.file_uploader("Passo 2: Faça upload da Planilha 2 (De/Para)", type=["xlsx", "xls", "csv"])

    if link_planilha1 and planilha2_file:
        url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
        if url_csv is None:
            st.error("URL de planilha inválida. Verifique o link.")
        else:
            df1 = pd.read_csv(url_csv)
            
            # Usando a nova função robusta para ler o arquivo enviado
            df2 = ler_planilha(planilha2_file)

            if df2 is not None: # Prosseguir somente se a leitura do arquivo for bem-sucedida
                df1 = padronizar_colunas(df1)
                df2 = padronizar_colunas(df2)
                
                # ... (o resto do seu código da Aba 1 continua aqui, sem alterações)
                # Ajuste de colunas com fallback
                col_veiculo_1 = "veiculo_boxnet" if "veiculo_boxnet" in df1.columns else df1.columns[0]
                # ... (etc)


# =============================
# ABA 2 - Soudview
# =============================
with tab2:
    st.subheader("Validação da Soudview 🎧")

    link_planilha1_soud = st.text_input("Passo 1: Cole o link da Planilha 1 (Checking principal)", key="soud_link")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")

    if link_planilha1_soud and soud_file:
        # Usando a nova função robusta para ler o arquivo Soudview
        df_raw = ler_planilha(soud_file)

        if df_raw is not None: # Prosseguir somente se a leitura for bem-sucedida
            try:
                df_soud = parse_soudview(df_raw)
                url_csv = transformar_url_para_csv(link_planilha1_soud, aba="Relatórios")
                df_checking = pd.read_csv(url_csv)

                # ... (o resto do seu código da Aba 2 continua aqui, sem alterações)
                # ...
            except Exception as e:
                st.error(f"Erro ao processar os dados das planilhas: {e}")

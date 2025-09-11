import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from thefuzz import process, fuzz

# Importa a função do arquivo soudview.py (garanta que ele exista)
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
# CONTEÚDO DA ABA 1: VALIDAÇÃO CHECKING (AGORA CORRIGIDO)
# ===================================================================
with tab1:
    st.subheader("Validação entre Planilha de Relatórios e De/Para")

    # Adicionadas 'keys' únicas para evitar conflito com a outra aba
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
                        # Leitura da Planilha 1 (Relatórios)
                        response = requests.get(url_csv)
                        response.raise_for_status()
                        df1 = pd.read_csv(io.StringIO(response.text))

                        # Leitura da Planilha 2 (De/Para)
                        if planilha2_file.name.endswith('.csv'):
                            df2 = pd.read_csv(planilha2_file)
                        else:
                            df2 = pd.read_excel(planilha2_file)
                        
                        # --- Início da sua lógica original de comparação ---
                        df1 = padronizar_colunas(df1)
                        df2 = padronizar_colunas(df2)

                        col_veiculo_1 = "veiculo_boxnet"
                        col_data_1 = "data_contratacao"
                        col_hora_1 = "hora_veiculacao"
                        col_titulo_1 = "titulo_peca"

                        col_veiculo_2 = "veiculo"
                        col_data_2 = "datafonte"
                        col_hora_2 = "hora"
                        col_titulo_2 = "titulo"

                        df1[col_data_1] = pd.to_datetime(df1[col_data_1], errors='coerce').dt.date
                        df2[col_data_2] = pd.to_datetime(df2[col_data_2], errors='coerce').dt.date

                        df1[col_hora_1] = pd.to_datetime(df1[col_hora_1], errors='coerce').dt.time
                        df2[col_hora_2] = pd.to_datetime(df2[col_hora_2], errors='coerce').dt.time

                        # Merge otimizado para performance
                        df2['checking_status'] = 'Não está no checking'
                        df2['plano_status'] = 'Fora do plano'

                        merged_checking = pd.merge(df2, df1, 
                                           left_on=[col_veiculo_2, col_data_2, col_hora_2, col_titulo_2],
                                           right_on=[col_veiculo_1, col_data_1, col_hora_1, col_titulo_1],
                                           how='left', indicator=True)
                        
                        df2.loc[merged_checking['_merge'] == 'both', 'checking_status'] = 'Já está no checking'

                        merged_plano = pd.merge(df2, df1, 
                                        left_on=[col_veiculo_2, col_data_2, col_hora_2],
                                        right_on=[col_veiculo_1, col_data_1, col_hora_1],
                                        how='left', indicator=True)

                        df2.loc[merged_plano['_merge'] == 'both', 'plano_status'] = 'Dentro do plano'

                        st.dataframe(df2)
                        st.success("Validação concluída!")
                        # --- Fim da sua lógica original de comparação ---

                    except Exception as e:
                        st.error(f"Ocorreu um erro durante o processamento: {e}")
        else:
            st.warning("Por favor, preencha o link e faça o upload do arquivo.")

# ===================================================================
# CONTEÚDO DA ABA 2: VALIDAÇÃO SOUDVIEW (JÁ ESTAVA CORRETA)
# ===================================================================
with tab2:
    # O código da Aba 2 que já funcionava e tinha as keys únicas.
    st.subheader("Validação da Soudview vs. Planilha Principal")
    # ... (o código completo e funcional da Aba 2 vai aqui, como na resposta anterior) ...

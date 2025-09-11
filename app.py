import streamlit as st
import pandas as pd
import numpy as np
import io # Importa a biblioteca io
import re
import requests
from thefuzz import process, fuzz
from soudview import parse_soudview

# --- FUNÇÕES GLOBAIS ---
def transformar_url_para_csv(url: str, aba: str = "Relatórios"):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            # A codificação da aba aqui está correta, o problema é como o pandas a usa
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except: return None

# ... (outras funções globais como padronizar_colunas, etc., se você as tiver) ...

# --- LAYOUT PRINCIPAL DO APP ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

# ===================================================================
# CONTEÚDO DA ABA 1: VALIDAÇÃO CHECKING
# ===================================================================
with tab1:
    st.subheader("Validação entre Planilha de Relatórios e De/Para")
    # ... (seu código para os widgets da Aba 1) ...
    # Lembre-se de colocar aqui a lógica completa da sua primeira aba.

# ===================================================================
# CONTEÚDO DA ABA 2: VALIDAÇÃO SOUDVIEW
# ===================================================================
with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")

    link_planilha_checking = st.text_input("Passo 1: Cole o link da Planilha Principal (Checking)", key="soud_link")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")
    debug_mode = st.checkbox("🔍 Ativar Modo Depuração", key="debug_soud")

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, key="btn_soud"):
        if link_planilha_checking and soud_file:
            with st.spinner("Analisando planilhas..."):
                # --- Leitura da Soudview (sem alteração) ---
                df_raw = pd.read_excel(soud_file, header=None)
                if debug_mode:
                    st.info("--- MODO DEPURAÇÃO ATIVADO ---")
                    st.dataframe(df_raw)
                    st.write("--- FIM DA DEPURAÇÃO ---")
                
                df_soud = parse_soudview(df_raw)

                if df_soud.empty:
                    st.error("Não foi possível extrair dados da Soudview. Verifique o formato do arquivo.")
                else:
                    st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                    
                    # --- Leitura da Planilha Principal (CHECKING) ---
                    url_csv = transformar_url_para_csv(link_planilha_checking, aba="Relatórios")
                    if url_csv:
                        try:
                            # MUDANÇA AQUI: Usando requests para baixar o conteúdo primeiro
                            response = requests.get(url_csv)
                            response.raise_for_status() # Verifica se o download teve sucesso
                            
                            # Agora o pandas lê o conteúdo em texto, não mais a URL
                            df_checking = pd.read_csv(io.StringIO(response.text))

                            # A partir daqui, o resto do seu código de comparação funciona normalmente
                            # ... (chamar a função de comparação, exibir o relatório, etc.)
                            st.info("Planilha principal lida com sucesso. Iniciando comparação...")

                        except requests.exceptions.RequestException as e:
                            st.error(f"Erro ao acessar a URL do Google Sheets: {e}")
                        except Exception as e:
                            st.error(f"Erro ao processar a planilha principal: {e}")
                    else:
                        st.error("URL da planilha principal é inválida.")
        else:
            st.warning("Por favor, preencha o link e faça o upload do arquivo para continuar.")

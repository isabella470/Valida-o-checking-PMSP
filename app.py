import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from thefuzz import process, fuzz
import datetime

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()

# --- FUNÇÕES (sem alterações) ---
def comparar_planilhas(df_soud, df_checking, df_depara):
    # ... (toda a lógica desta função permanece a mesma)
    col_veiculo_principal = 'VEÍCULO BOXNET'
    col_data_principal = 'DATA VEICULAÇÃO'
    col_horario_principal = 'HORA VEICULAÇÃO'
    col_soudview_depara = 'Nome_Soudview'
    col_principal_depara = 'Nome_Planilha_Principal'
    for col in [col_veiculo_principal, col_data_principal, col_horario_principal]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na Planilha Principal.")
            return pd.DataFrame()
    for col in [col_soudview_depara, col_principal_depara]:
        if col not in df_depara.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na sua planilha De/Para.")
            return pd.DataFrame()
    df_soud_mapeado = pd.merge(df_soud, df_depara, left_on='Veiculo_Soudview', right_on=col_soudview_depara, how='left')
    df_soud_mapeado[col_principal_depara].fillna("NÃO MAPEADO NO DE/PARA", inplace=True)
    df_checking_sp = df_checking[df_checking[col_veiculo_principal].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data_principal], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario_principal], errors='coerce').dt.time
    relatorio = pd.merge(df_soud_mapeado, df_checking_sp, left_on=[col_principal_depara, 'Data', 'Horario'], right_on=[col_veiculo_principal, 'DATA_NORM', 'HORARIO_NORM'], how='left', indicator=True)
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    relatorio.rename(columns={col_principal_depara: 'Veiculo_Mapeado_Principal'}, inplace=True)
    return relatorio[['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado_Principal', 'Status']]

# --- LAYOUT DO STREAMLIT ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
    checking_file = st.file_uploader("Passo 1: Faça upload da Planilha Principal (Checking)", type=["xlsx", "xls", "csv"], key="checking_file")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")
    depara_file = st.file_uploader("Passo 3: Faça upload da sua Planilha De/Para de Veículos", type=["xlsx", "xls", "csv"], key="depara_file")

    campanhas_selecionadas = []
    if soud_file:
        # --- MUDANÇA AQUI ---
        # 1. Determinamos o motor com base no nome do arquivo
        engine_soudview = 'xlrd' if soud_file.name.endswith('.xls') else 'openpyxl'
        
        # 2. Passamos o motor para a função em cache
        @st.cache_data
        def carregar_dados_soudview(arquivo, engine):
            df = parse_soudview(pd.read_excel(arquivo, header=None, engine=engine))
            return df

        # Lemos os bytes do arquivo para o cache funcionar melhor
        soud_file_bytes = soud_file.getvalue()
        df_soud_completo = carregar_dados_soudview(soud_file_bytes, engine=engine_soudview)
        
        if not df_soud_completo.empty:
            lista_de_campanhas = sorted(df_soud_completo['Comercial_Soudview'].unique())
            campanhas_selecionadas = st.multiselect(
                "Passo 4: Selecione as campanhas que deseja INCLUIR",
                options=lista_de_campanhas,
                default=lista_de_campanhas
            )

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, key="btn_soud"):
        if checking_file and soud_file and depara_file:
            with st.spinner("Analisando..."):
                try:
                    # --- MUDANÇA AQUI TAMBÉM ---
                    # Reutilizamos a lógica que já determinou o motor correto
                    soud_file.seek(0) # Volta o leitor para o início do arquivo
                    soud_file_bytes_process = soud_file.getvalue()
                    engine_soudview_process = 'xlrd' if soud_file.name.endswith('.xls') else 'openpyxl'
                    df_soud_original = carregar_dados_soudview(soud_file_bytes_process, engine=engine_soudview_process)

                    df_soud_filtrado = df_soud_original[df_soud_original['Comercial_Soudview'].isin(campanhas_selecionadas)]

                    if df_soud_filtrado.empty:
                        st.error("Nenhuma veiculação encontrada para as campanhas selecionadas.")
                    else:
                        st.success(f"{len(df_soud_filtrado)} veiculações de {len(campanhas_selecionadas)} campanhas selecionadas para análise!")
                        
                        df_checking = pd.read_excel(checking_file)
                        df_depara = pd.read_excel(depara_file)

                        relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking, df_depara)
                        
                        if not relatorio_final.empty:
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                            st.download_button("📥 Baixar Relatório Final", output.getvalue(), "Relatorio_Final.xlsx", "application/vnd.openxmlformats-officedocument-spreadsheetml-sheet", use_container_width=True)

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")
                    st.exception(e)
        else:
            st.warning("Por favor, faça o upload dos três arquivos para iniciar a validação.")

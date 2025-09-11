# Arquivo: app.py (VERSÃO FINAL E MAIS ROBUSTA)
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
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado. Por favor, certifique-se de que ele está na mesma pasta que o app.py.")
    st.stop()

# --- FUNÇÕES GLOBAIS ---
def comparar_planilhas(df_soud, df_checking):
    # Nomes exatos das colunas que esperamos na planilha principal
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'
    
    # Verifica se as colunas essenciais existem.
    for col in [col_veiculo, col_data, col_horario]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na sua planilha principal.")
            st.info(f"As colunas que foram encontradas são: {df_checking.columns.tolist()}")
            st.warning("Verifique se o arquivo que você subiu tem exatamente esses nomes de coluna.")
            return pd.DataFrame()

    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    if df_checking_sp.empty:
        st.warning("Nenhum veículo de 'SÃO PAULO' foi encontrado na planilha principal para comparação.")

    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time

    veiculos_soudview = df_soud['Veiculo_Soudview'].unique()
    veiculos_checking = df_checking_sp[col_veiculo].unique()
    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        if pd.notna(veiculo_soud) and veiculos_checking.size > 0:
            match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
            if match and match[1] >= 80:
                mapa_veiculos[veiculo_soud] = match[0]
            else: mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
        else: mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            
    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)
    relatorio = pd.merge(df_soud, df_checking_sp, left_on=['Veiculo_Mapeado', 'Data', 'Horario'], right_on=[col_veiculo, 'DATA_NORM', 'HORARIO_NORM'], how='left', indicator=True)
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    return relatorio[['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Status']]

# --- LAYOUT DO STREAMLIT ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
    # --- MUDANÇA PRINCIPAL AQUI ---
    # Trocamos o input do link por um uploader de arquivo
    checking_file = st.file_uploader("Passo 1: Faça upload da Planilha Principal (Checking)", type=["xlsx", "xls", "csv"], key="checking_file")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, key="btn_soud"):
        if checking_file and soud_file:
            with st.spinner("Analisando..."):
                try:
                    # Leitura da Soudview (sem alteração)
                    df_raw_soud = pd.read_excel(soud_file, header=None)
                    df_soud = parse_soudview(df_raw_soud)

                    if df_soud.empty:
                        st.error("Não foi possível extrair dados da Soudview.")
                    else:
                        st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                        
                        # Leitura da Planilha Principal (agora do arquivo)
                        if checking_file.name.endswith('.csv'):
                            df_checking = pd.read_csv(checking_file)
                        else:
                            df_checking = pd.read_excel(checking_file)

                        # Comparação
                        relatorio_final = comparar_planilhas(df_soud, df_checking)
                        
                        if not relatorio_final.empty:
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                            st.download_button("📥 Baixar Relatório Final", output.getvalue(), "Relatorio_Final.xlsx", "application/vnd.openxmlformats-officedocument-spreadsheetml-sheet", use_container_width=True)

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")
        else:
            st.warning("Por favor, faça o upload dos dois arquivos para iniciar a validação.")

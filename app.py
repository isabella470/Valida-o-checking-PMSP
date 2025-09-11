# Arquivo: app.py (VERSÃO FINAL COM TRANSFORMAÇÃO DE DADOS)
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

# --- FUNÇÕES GLOBAIS ---
def transformar_url_para_csv(url: str, aba: str = "Relatórios"):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except: return None

def transformar_checking(df_checking_raw):
    """
    Função que transforma a planilha principal de matriz para lista,
    usando os nomes de coluna que sabemos que existem.
    """
    # Identifica as colunas que são fixas (não são datas como '01/08')
    id_vars = [col for col in df_checking_raw.columns if not re.match(r'\d{2}/\d{2}', str(col))]
    
    # Identifica as colunas que são datas
    date_vars = [col for col in df_checking_raw.columns if re.match(r'\d{2}/\d{2}', str(col))]
    
    if not date_vars:
        st.error("Nenhuma coluna no formato de data (ex: '01/08') foi encontrada na planilha principal.")
        return pd.DataFrame()
        
    # Transforma (unpivot) a tabela
    df_tidy = df_checking_raw.melt(
        id_vars=id_vars,
        value_vars=date_vars,
        var_name='DIA_MES',
        value_name='HORARIO'
    )
    
    df_tidy.dropna(subset=['HORARIO'], inplace=True)
    df_tidy = df_tidy[df_tidy['HORARIO'].astype(str).str.strip() != '']

    # Cria a coluna de Data completa
    ano_atual = datetime.datetime.now().year
    df_tidy['DATA'] = pd.to_datetime(df_tidy['DIA_MES'] + f'/{ano_atual}', format='%d/%m/%Y', errors='coerce')
    
    # Renomeia a coluna do veículo para um nome padrão
    df_tidy.rename(columns={'EMISSORA': 'VEICULO'}, inplace=True)
    
    return df_tidy[['VEICULO', 'DATA', 'HORARIO']]


def comparar_planilhas(df_soud, df_checking_transformada):
    df_checking_sp = df_checking_transformada[df_checking_transformada['VEICULO'].str.contains("SÃO PAULO", case=False, na=False)].copy()
    if df_checking_sp.empty:
        st.warning("Nenhum veículo de 'SÃO PAULO' foi encontrado na planilha principal para comparação.")

    df_checking_sp['DATA'] = pd.to_datetime(df_checking_sp['DATA'], errors='coerce').dt.date
    df_checking_sp['HORARIO'] = pd.to_datetime(df_checking_sp['HORARIO'], errors='coerce').dt.time

    veiculos_soudview = df_soud['Veiculo_Soudview'].unique()
    veiculos_checking = df_checking_sp['VEICULO'].unique()
    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        if pd.notna(veiculo_soud) and veiculos_checking.size > 0:
            match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
            if match and match[1] >= 80:
                mapa_veiculos[veiculo_soud] = match[0]
            else: mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
        else: mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            
    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)
    relatorio = pd.merge(df_soud, df_checking_sp, left_on=['Veiculo_Mapeado', 'Data', 'Horario'], right_on=['VEICULO', 'DATA', 'HORARIO'], how='left', indicator=True)
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
    link_planilha_checking = st.text_input("Passo 1: Cole o link da Planilha Principal (Checking)", key="soud_link")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"], key="soud_file")

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, key="btn_soud"):
        if link_planilha_checking and soud_file:
            with st.spinner("Analisando..."):
                df_raw_soud = pd.read_excel(soud_file, header=None)
                df_soud = parse_soudview(df_raw_soud)

                if df_soud.empty:
                    st.error("Não foi possível extrair dados da Soudview.")
                else:
                    st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                    url_csv = transformar_url_para_csv(link_planilha_checking)
                    try:
                        response = requests.get(url_csv)
                        response.raise_for_status()
                        
                        # PASSO 1: Pular linhas de cabeçalho
                        # IMPORTANTE: Você talvez precise ajustar este número (tente 1, 2, 3 ou 4)
                        df_checking_raw = pd.read_csv(io.StringIO(response.text), skiprows=2)

                        # PASSO 2: Transformar a planilha de matriz para lista
                        df_checking_transformada = transformar_checking(df_checking_raw)

                        # PASSO 3: Comparar!
                        if not df_checking_transformada.empty:
                            relatorio_final = comparar_planilhas(df_soud, df_checking_transformada)
                            
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            # Download
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                            st.download_button("📥 Baixar Relatório Final", output.getvalue(), "Relatorio_Final.xlsx", "application/vnd.openxmlformats-officedocument-spreadsheetml-sheet", use_container_width=True)
                        else:
                            st.warning("A planilha principal foi transformada, mas resultou em uma tabela vazia. Verifique o conteúdo e o formato do arquivo.")

                    except Exception as e:
                        st.error(f"Ocorreu um erro ao processar a planilha principal: {e}")
        else:
            st.warning("Por favor, preencha os dois campos.")

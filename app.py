import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
import datetime

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()

# --- O SEU DE/PARA ESTÁ AQUI ---
# Chave (esquerda): Nome EXATO da planilha Soudview.
# Valor (direita): Nome EXATO da Planilha Principal.
DE_PARA_VEICULOS = {
    "105 FM São Paulo": "105 FM/SÃO PAULO",
    "89 FM São Paulo": "89 FM A RÁDIO ROCK/SÃO PAULO",
    "Adore FM": "ADORE FM/SÃO PAULO",
    "Aguia Dourada FM São Paulo": "AGUIA DOURADA FM/SÃO PAULO"
    # Adicione todos os outros pares de veículos aqui...
}
# ----------------------------------------------

# --- Funções ----------------
def ler_csv(file):
    file.seek(0)
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

    for col in [col_veiculo, col_data, col_horario]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            return pd.DataFrame()

    # Mapeia os veículos usando o dicionário interno
    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(DE_PARA_VEICULOS)
    df_soud['Veiculo_Mapeado'].fillna("NÃO MAPEADO NO CÓDIGO", inplace=True)
    
    # Prepara a planilha principal
    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time
    
    # Faz o merge final
    relatorio = pd.merge(df_soud, df_checking_sp, left_on=['Veiculo_Mapeado', 'Data', 'Horario'], right_on=[col_veiculo, 'DATA_NORM', 'HORARIO_NORM'], how='left', indicator=True)
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    
    # Adiciona colunas de comparativo
    relatorio.rename(columns={col_veiculo: 'Veiculo_Principal_Encontrado'}, inplace=True)
    colunas_finais = ['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Status', 'Veiculo_Principal_Encontrado']
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]
    
    return relatorio[colunas_existentes]

# ---------------- STREAMLIT ----------------
st.set_page_config(page_title="Validador de Checking", layout="wide")
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
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
            st.warning("Por favor, faça o upload dos dois arquivos.")
        elif not campanhas_selecionadas:
            st.warning("Por favor, selecione pelo menos uma campanha.")
        else:
            with st.spinner("Analisando..."):
                try:
                    soud_file.seek(0)
                    df_soud = parse_soudview(pd.read_excel(soud_file, header=None, engine=None))
                    df_soud_filtrado = df_soud[df_soud['Comercial_Soudview'].isin(campanhas_selecionadas)]

                    if checking_file.name.endswith('.csv'):
                        df_checking = ler_csv(checking_file)
                    else:
                        df_checking = pd.read_excel(checking_file)

                    if df_soud_filtrado.empty:
                        st.error("Nenhuma veiculação encontrada para as campanhas selecionadas.")
                    else:
                        st.success(f"{len(df_soud_filtrado)} veiculações extraídas para as campanhas selecionadas!")
                        relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking)
                        
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

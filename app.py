import streamlit as st
import pandas as pd
import numpy as np
import io
from thefuzz import process, fuzz
import csv

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()


# ---------------- Funções auxiliares ---------------- #
def detectar_separador(file):
    """Detecta automaticamente o separador do CSV."""
    file.seek(0)
    sample = file.read(1024).decode('utf-8', errors='ignore')
    file.seek(0)
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample).delimiter
    except csv.Error:
        return ';'  # Padrão se não conseguir detectar


def ler_csv(file):
    sep = detectar_separador(file)
    return pd.read_csv(file, sep=sep, encoding='utf-8')


def comparar_planilhas(df_soud, df_checking):
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'

    # Verifica se todas as colunas necessárias existem
    for col in [col_veiculo, col_data, col_horario]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame()

    # Filtra só veículos de São Paulo
    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time

    # Fuzzy match dos veículos (idêntico ao código original que funcionava)
    veiculos_soudview = df_soud['Veiculo_Soudview'].dropna().astype(str).str.strip().unique()
    veiculos_checking = df_checking_sp[col_veiculo].dropna().astype(str).str.strip().unique()

    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
        if match and match[1] >= 80:
            mapa_veiculos[veiculo_soud] = match[0]
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"

    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)

    # Merge para verificar status
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['Veiculo_Mapeado', 'Data', 'Horario'],
        right_on=[col_veiculo, 'DATA_NORM', 'HORARIO_NORM'],
        how='left',
        indicator=True
    )

    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    return relatorio[['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Status']]


# ---------------- Streamlit ---------------- #
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")

    checking_file = st.file_uploader("Passo 1: Faça upload da Planilha Principal (CSV)", type=["csv"])
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview (CSV)", type=["csv"])

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True):
        if not checking_file or not soud_file:
            st.warning("Por favor, faça o upload dos dois arquivos para iniciar a validação.")
        else:
            with st.spinner("Analisando..."):
                try:
                    # Lê os CSVs de forma robusta
                    df_raw_soud = ler_csv(soud_file)
                    df_checking = ler_csv(checking_file)

                    df_soud = parse_soudview(df_raw_soud)
                    if df_soud.empty:
                        st.error("Não foi possível extrair dados da Soudview.")
                    else:
                        st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")

                        # Comparação
                        relatorio_final = comparar_planilhas(df_soud, df_checking)
                        if not relatorio_final.empty:
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            # Exporta Excel
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")

                            st.download_button(
                                "📥 Baixar Relatório Final",
                                output.getvalue(),
                                "Relatorio_Final.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {e}")
                    st.exception(e)

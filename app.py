import streamlit as st
import pandas as pd
import numpy as np
import io
from thefuzz import process, fuzz
import chardet  # Para detectar encoding automaticamente
import csv

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()


def detectar_encoding(file):
    rawdata = file.read()
    file.seek(0)
    result = chardet.detect(rawdata)
    return result['encoding']


def detectar_separador(file, encoding):
    file.seek(0)
    sample = file.read(1024).decode(encoding)
    file.seek(0)
    sniffer = csv.Sniffer()
    return sniffer.sniff(sample).delimiter


def ler_csv(file):
    encoding = detectar_encoding(file)
    sep = detectar_separador(file, encoding)
    return pd.read_csv(file, sep=sep, encoding=encoding)


def comparar_planilhas(df_soud, df_checking):
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'

    for col in [col_veiculo, col_data, col_horario]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame()

    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time

    veiculos_soudview = df_soud['Veiculo_Soudview'].dropna().unique()
    veiculos_checking = df_checking_sp[col_veiculo].dropna().unique()

    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio) if veiculos_checking.size > 0 else None
        mapa_veiculos[veiculo_soud] = match[0] if match and match[1] >= 80 else "NÃO MAPEADO"

    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)

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


# ---------------- STREAMLIT ---------------- #
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

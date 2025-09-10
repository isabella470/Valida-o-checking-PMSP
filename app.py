import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import io
import re

st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

# =============================
# Função para transformar Google Sheet em CSV
# =============================
def transformar_url_para_csv(url: str) -> str:
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except:
        pass
    return None

# =============================
# Inputs
# =============================
link_planilha1 = st.text_input(
    "Passo 1: Cole o link da Planilha 1 (Relatórios)"
)

planilha2_file = st.file_uploader(
    "Passo 2: Faça upload da Planilha 2 (De/Para)", type=["xlsx"]
)

# =============================
# Processamento
# =============================
if link_planilha1 and planilha2_file:
    url_csv = transformar_url_para_csv(link_planilha1)
    if url_csv is None:
        st.error("URL de planilha inválida. Verifique o link.")
    else:
        with st.spinner("Lendo Planilha 1..."):
            try:
                df1 = pd.read_csv(url_csv)
            except Exception as e:
                st.error(f"Erro ao ler Planilha 1: {e}")
                st.stop()

            df2 = pd.read_excel(planilha2_file, engine="openpyxl")

            # Padronizar colunas
            df1 = df1.rename(columns={
                "VEÍCULO BOXNET": "Veículo",
                "DATA CONTRATAÇÃO": "Data",
                "HORA VEICULAÇÃO": "Hora",
                "TÍTULO PEÇA": "Título"
            })
            df2 = df2.rename(columns={
                "Veículo": "Veículo",
                "DataFonte": "Data",
                "Hora": "Hora",
                "Título": "Título"
            })

            # Converter datas e horas
            df1['Data'] = pd.to_datetime(df1['Data'])
            df2['Data'] = pd.to_datetime(df2['Data'])
            df1['Hora'] = pd.to_datetime(df1['Hora'], format='%H:%M').dt.time
            df2['Hora'] = pd.to_datetime(df2['Hora'], format='%H:%M').dt.time

            # =============================
            # Funções de verificação
            # =============================
            def verificar_checking(row):
                cond = (
                    (df1['Veículo'] == row['Veículo']) &
                    (df1['Data'] == row['Data']) &
                    (df1['Hora'] == row['Hora']) &
                    (df1['Título'] == row['Título'])
                )
                return "Já está no checking" if cond.any() else "Não está no checking"

            def verificar_plano(row):
                cond = (
                    (df1['Veículo'] == row['Veículo']) &
                    (df1['Data'] == row['Data']) &
                    (df1['Hora'] == row['Hora'])
                )
                return "Dentro do plano" if cond.any() else "Fora do plano"

            # =============================
            # Aplicar verificações
            # =============================
            df2['Já na checking'] = df2.apply(verificar_checking, axis=1)
            df2['Plano'] = df2.apply(verificar_plano, axis=1)

            # =============================
            # Gerar Excel com cores
            # =============================
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df2.to_excel(writer, index=False, sheet_name="Planilha 3")
                workbook = writer.book
                worksheet = writer.sheets["Planilha 3"]

                verde = workbook.add_format({'bg_color': '#C6EFCE'})
                vermelho = workbook.add_format({'bg_color': '#FFC7CE'})

                # Colunas
                checking_col = df2.columns.get_loc("Já na checking")
                plano_col = df2.columns.get_loc("Plano")

                # Cores
                for row_num, value in enumerate(df2["Já na checking"], 1):
                    if value == "Já está no checking":
                        worksheet.write(row_num, checking_col, value, verde)

                for row_num, value in enumerate(df2["Plano"], 1):
                    if value == "Dentro do plano":
                        worksheet.write(row_num, plano_col, value, verde)
                    else:
                        worksheet.write(row_num, plano_col, value, vermelho)

            dados_excel = output.getvalue()

            st.success("✅ Planilha 3 gerada com sucesso!")
            st.download_button(
                label="📥 Baixar Planilha 3",
                data=dados_excel,
                file_name="planilha3.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


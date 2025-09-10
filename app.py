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
def transformar_url_para_csv(url: str, aba: str = "Relatórios") -> str:
    """
    Converte link de Google Sheets para CSV direto, de uma aba específica
    """
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
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
    url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
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
            df1 = padronizar_colunas(df1)
            df2 = padronizar_colunas(df2)

            # =============================
            # Converter datas e horas
            # =============================
            # Ajuste dos nomes padronizados
            col_veiculo_1 = "veiculo_boxnet" if "veiculo_boxnet" in df1.columns else df1.columns[0]
            col_data_1 = "data_contratacao" if "data_contratacao" in df1.columns else df1.columns[1]
            col_hora_1 = "hora_veiculacao" if "hora_veiculacao" in df1.columns else df1.columns[2]
            col_titulo_1 = "titulo_peca" if "titulo_peca" in df1.columns else df1.columns[3]

            col_veiculo_2 = "veiculo" if "veiculo" in df2.columns else df2.columns[0]
            col_data_2 = "datafonte" if "datafonte" in df2.columns else df2.columns[1]
            col_hora_2 = "hora" if "hora" in df2.columns else df2.columns[2]
            col_titulo_2 = "titulo" if "titulo" in df2.columns else df2.columns[3]

            df1[col_data_1] = pd.to_datetime(df1[col_data_1], errors='coerce')
            df2[col_data_2] = pd.to_datetime(df2[col_data_2], errors='coerce')

            df1[col_hora_1] = pd.to_datetime(df1[col_hora_1], format='%H:%M', errors='coerce').dt.time
            df2[col_hora_2] = pd.to_datetime(df2[col_hora_2], format='%H:%M', errors='coerce').dt.time

            # =============================
            # Funções de verificação
            # =============================
            def verificar_checking(row):
                cond = (
                    (df1[col_veiculo_1] == row[col_veiculo_2]) &
                    (df1[col_data_1] == row[col_data_2]) &
                    (df1[col_hora_1] == row[col_hora_2]) &
                    (df1[col_titulo_1] == row[col_titulo_2])
                )
                return "Já está no checking" if cond.any() else "Não está no checking"

            def verificar_plano(row):
                cond = (
                    (df1[col_veiculo_1] == row[col_veiculo_2]) &
                    (df1[col_data_1] == row[col_data_2]) &
                    (df1[col_hora_1] == row[col_hora_2])
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


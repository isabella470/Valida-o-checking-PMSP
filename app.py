import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests

from soudview import parse_soudview, normalizar_hora  # ← Import ajustado

# =============================
# Função para transformar Google Sheet em CSV
# =============================
def transformar_url_para_csv(url: str, aba: str = "Relatórios") -> str:
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
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
# Streamlit Layout
# =============================
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

# =============================
# ABA 1 - Checking
# =============================
with tab1:
    st.subheader("Validação de Checking 📊")

    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Relatórios)")
    planilha2_file = st.file_uploader("Passo 2: Faça upload da Planilha 2 (De/Para)", type=["xlsx"])

    if link_planilha1 and planilha2_file:
        url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
        if url_csv is None:
            st.error("URL de planilha inválida. Verifique o link.")
        else:
            try:
                df1 = pd.read_csv(url_csv, encoding='utf-8')
            except UnicodeDecodeError:
                df1 = pd.read_csv(url_csv, encoding='latin1')

            df2 = pd.read_excel(planilha2_file, engine="openpyxl")

            df1 = padronizar_colunas(df1)
            df2 = padronizar_colunas(df2)

            # Ajuste de colunas com fallback
            col_veiculo_1 = "veiculo_boxnet" if "veiculo_boxnet" in df1.columns else df1.columns[0]
            col_data_1 = "data_contratacao" if "data_contratacao" in df1.columns else df1.columns[1]
            col_hora_1 = "hora_veiculacao" if "hora_veiculacao" in df1.columns else df1.columns[2]
            col_titulo_1 = "titulo_peca" if "titulo_peca" in df1.columns else df1.columns[3]

            col_veiculo_2 = "veiculo" if "veiculo" in df2.columns else df2.columns[0]
            col_data_2 = "datafonte" if "datafonte" in df2.columns else df2.columns[1]
            col_hora_2 = "hora" if "hora" in df2.columns else df2.columns[2]
            col_titulo_2 = "titulo" if "titulo" in df2.columns else df2.columns[3]

            # Converter datas e horas
            df1[col_data_1] = pd.to_datetime(df1[col_data_1], errors='coerce')
            df2[col_data_2] = pd.to_datetime(df2[col_data_2], errors='coerce')

            df1[col_hora_1] = pd.to_datetime(df1[col_hora_1], format='%H:%M', errors='coerce').dt.time
            df2[col_hora_2] = pd.to_datetime(df2[col_hora_2], format='%H:%M', errors='coerce').dt.time

            # Funções de verificação
            def zerar_segundos(t):
                return t.replace(second=0) if pd.notnull(t) else t

            def verificar_checking(row):
                hora2 = zerar_segundos(row[col_hora_2])
                cond = (
                    (df1[col_veiculo_1] == row[col_veiculo_2]) &
                    (df1[col_data_1] == row[col_data_2]) &
                    (df1[col_titulo_1] == row[col_titulo_2]) &
                    (df1[col_hora_1].apply(zerar_segundos) == hora2)
                )
                return "Já está no checking" if cond.any() else "Não está no checking"

            def verificar_plano(row):
                hora2 = zerar_segundos(row[col_hora_2])
                cond = (
                    (df1[col_veiculo_1] == row[col_veiculo_2]) &
                    (df1[col_data_1] == row[col_data_2]) &
                    (df1[col_hora_1].apply(zerar_segundos) == hora2)
                )
                return "Dentro do plano" if cond.any() else "Fora do plano"

            df2['Já na checking'] = df2.apply(verificar_checking, axis=1)
            df2['Plano'] = df2.apply(verificar_plano, axis=1)

            # Gerar Excel com cores
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df2.to_excel(writer, index=False, sheet_name="Planilha 3")
                workbook = writer.book
                worksheet = writer.sheets["Planilha 3"]

                verde = workbook.add_format({'bg_color': '#C6EFCE'})
                vermelho = workbook.add_format({'bg_color': '#FFC7CE'})

                checking_col = df2.columns.get_loc("Já na checking")
                plano_col = df2.columns.get_loc("Plano")

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

# =============================
# ABA 2 - Soudview
# =============================
with tab2:
    st.subheader("Validação da Soudview 🎧")

    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Checking principal)", key="soud_link")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx"], key="soud_file")

    if link_planilha1 and soud_file:
        try:
            df_raw = pd.read_excel(soud_file, header=None, engine="openpyxl")
            df_soud = parse_soudview(df_raw)

            url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
            df_checking = pd.read_csv(url_csv)

            df_checking["hora_norm"] = df_checking["hora_veiculacao"].apply(normalizar_hora)
            df_checking["data_norm"] = pd.to_datetime(df_checking["data_contratacao"], errors="coerce")

            def verificar(row):
                cond = (
                    (df_checking["veiculo_boxnet"].str.contains(row["veiculo"].split()[0], case=False, na=False)) &
                    (df_checking["data_norm"] == row["data"]) &
                    (df_checking["hora_norm"] == row["hora"])
                )
                return "Já no Checking" if cond.any() else "Não encontrado"

            df_soud["status"] = df_soud.apply(verificar, axis=1)

            st.dataframe(df_soud.head(30))

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_soud.to_excel(writer, index=False, sheet_name="Planilha 4")
                workbook = writer.book
                worksheet = writer.sheets["Planilha 4"]

                verde = workbook.add_format({'bg_color': '#C6EFCE'})
                vermelho = workbook.add_format({'bg_color': '#FFC7CE'})

                status_col = df_soud.columns.get_loc("status")

                for row_num, value in enumerate(df_soud["status"], 1):
                    if value == "Já no Checking":
                        worksheet.write(row_num, status_col, value, verde)
                    else:
                        worksheet.write(row_num, status_col, value, vermelho)

            dados_excel = output.getvalue()

            st.success("✅ Planilha 4 gerada com sucesso!")
            st.download_button(
                label="📥 Baixar Planilha 4",
                data=dados_excel,
                file_name="planilha4.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Erro ao processar a planilha: {e}")


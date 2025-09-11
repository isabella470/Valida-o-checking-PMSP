import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from rapidfuzz import fuzz, process

st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

# =============================
# Função para transformar Google Sheet em CSV
# =============================
def transformar_url_para_csv(url: str, aba: str = "Relatórios") -> str:
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            aba_codificada = requests.utils.quote(aba)  # codifica caracteres especiais
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
    except Exception as e:
        st.error(f"Erro ao processar URL: {e}")
    return None

# =============================
# Padronizar colunas
# =============================
def padronizar_colunas(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

# =============================
# Normalizar hora (só HH:MM)
# =============================
def normalizar_hora(h):
    try:
        t = pd.to_datetime(str(h), errors="coerce")
        return t.strftime("%H:%M") if pd.notnull(t) else None
    except:
        return None

# =============================
# Parsing da planilha Soudview
# =============================
def parse_soudview(df):
    dados = []
    veiculo_atual = None
    comercial_atual = None
    data_atual = None

    for _, row in df.iterrows():
        linha = row.astype(str).tolist()
        linha_str = " ".join(linha)

        if "Veículo:" in linha_str:
            veiculo_atual = linha_str.split("Veículo:")[-1].strip()

        if "Comercial:" in linha_str:
            comercial_atual = linha_str.split("Comercial:")[-1].strip()

        # Datas e horários
        if re.match(r"^\d{2}/\d{2}/\d{4}", linha_str.strip()):
            partes = linha_str.strip().split()
            data_atual = partes[0]
            horarios = partes[1:]
            for h in horarios:
                hora_norm = normalizar_hora(h)
                if veiculo_atual and comercial_atual and data_atual and hora_norm:
                    dados.append([veiculo_atual, comercial_atual, pd.to_datetime(data_atual, dayfirst=True), hora_norm])

    return pd.DataFrame(dados, columns=["veiculo", "comercial", "data", "hora"])

# =============================
# Inputs gerais
# =============================
link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Relatórios)")

# Tabs
aba1, aba2 = st.tabs(["Validação Checking", "Validação Soudview"])

with aba1:
    planilha2_file = st.file_uploader("Passo 2: Faça upload da Planilha 2 (De/Para)", type=["xlsx"], key="depara")

    if link_planilha1 and planilha2_file:
        url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
        if url_csv is None:
            st.error("URL de planilha inválida. Verifique o link.")
        else:
            with st.spinner("Lendo Planilha 1..."):
                try:
                    df1 = pd.read_csv(url_csv, encoding='utf-8')
                except UnicodeDecodeError:
                    df1 = pd.read_csv(url_csv, encoding='latin1')

                df2 = pd.read_excel(planilha2_file, engine="openpyxl")
                df1 = padronizar_colunas(df1)
                df2 = padronizar_colunas(df2)

                if df1.empty:
                    st.error("❌ A aba 'Relatórios' está vazia ou não existe na planilha fornecida.")
                    st.stop()

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

                df1[col_hora_1] = df1[col_hora_1].apply(normalizar_hora)
                df2[col_hora_2] = df2[col_hora_2].apply(normalizar_hora)

                def verificar_checking(row):
                    cond = (
                        (df1[col_veiculo_1].str.lower() == str(row[col_veiculo_2]).lower()) &
                        (df1[col_data_1] == row[col_data_2]) &
                        (df1[col_titulo_1].str.lower() == str(row[col_titulo_2]).lower()) &
                        (df1[col_hora_1] == row[col_hora_2])
                    )
                    return "Já está no checking" if cond.any() else "Não está no checking"

                def verificar_plano(row):
                    cond = (
                        (df1[col_veiculo_1].str.lower() == str(row[col_veiculo_2]).lower()) &
                        (df1[col_data_1] == row[col_data_2]) &
                        (df1[col_hora_1] == row[col_hora_2])
                    )
                    return "Dentro do plano" if cond.any() else "Fora do plano"

                df2['Já na checking'] = df2.apply(verificar_checking, axis=1)
                df2['Plano'] = df2.apply(verificar_plano, axis=1)

                st.subheader("Pré-visualização dos resultados:")
                st.dataframe(df2.head(20))

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

                    worksheet.freeze_panes(1, 0)
                    worksheet.autofilter(0, 0, len(df2), len(df2.columns)-1)

                dados_excel = output.getvalue()

                st.success("✅ Planilha 3 gerada com sucesso!")
                st.download_button(
                    label="📥 Baixar Planilha 3",
                    data=dados_excel,
                    file_name="planilha3.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

with aba2:
    planilha_soud = st.file_uploader("Upload da Planilha Soudview", type=["xlsx"], key="soud")

    if link_planilha1 and planilha_soud:
        url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
        if url_csv is None:
            st.error("URL de planilha inválida. Verifique o link.")
        else:
            try:
                df1 = pd.read_csv(url_csv, encoding='utf-8')
            except UnicodeDecodeError:
                df1 = pd.read_csv(url_csv, encoding='latin1')

            df1 = padronizar_colunas(df1)
            col_veiculo_1 = "veiculo_boxnet" if "veiculo_boxnet" in df1.columns else df1.columns[0]
            col_data_1 = "data_contratacao" if "data_contratacao" in df1.columns else df1.columns[1]
            col_hora_1 = "hora_veiculacao" if "hora_veiculacao" in df1.columns else df1.columns[2]

            df1[col_data_1] = pd.to_datetime(df1[col_data_1], errors='coerce')
            df1[col_hora_1] = df1[col_hora_1].apply(normalizar_hora)

            df_soud_raw = pd.read_excel(planilha_soud, header=None)
            df_soud = parse_soudview(df_soud_raw)

            # Comparação veículo (fuzzy match)
            def match_veiculo(v_soud, lista_principal):
                v_soud_norm = v_soud.lower().replace("são paulo", "").strip()
                candidatos = [x for x in lista_principal if "/são paulo" in x.lower()]
                melhor, score = process.extractOne(v_soud_norm, candidatos, scorer=fuzz.partial_ratio)
                return melhor if score > 70 else None

            df_soud['veiculo_match'] = df_soud['veiculo'].apply(lambda v: match_veiculo(v, df1[col_veiculo_1].unique()))

            def verificar_soud(row):
                if pd.isnull(row['veiculo_match']):
                    return "Veículo não encontrado"
                cond = (
                    (df1[col_veiculo_1] == row['veiculo_match']) &
                    (df1[col_data_1] == row['data']) &
                    (df1[col_hora_1] == row['hora'])
                )
                return "Já está no checking" if cond.any() else "Não está no checking"

            df_soud['Status'] = df_soud.apply(verificar_soud, axis=1)

            st.subheader("Pré-visualização da Soudview tratada:")
            st.dataframe(df_soud.head(20))

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_soud.to_excel(writer, index=False, sheet_name="Planilha 4")
                workbook = writer.book
                worksheet = writer.sheets["Planilha 4"]

                verde = workbook.add_format({'bg_color': '#C6EFCE'})
                vermelho = workbook.add_format({'bg_color': '#FFC7CE'})

                status_col = df_soud.columns.get_loc("Status")
                for row_num, value in enumerate(df_soud["Status"], 1):
                    if value == "Já está no checking":
                        worksheet.write(row_num, status_col, value, verde)
                    elif value == "Não está no checking":
                        worksheet.write(row_num, status_col, value, vermelho)

                worksheet.freeze_panes(1, 0)
                worksheet.autofilter(0, 0, len(df_soud), len(df_soud.columns)-1)

            dados_excel = output.getvalue()

            st.success("✅ Planilha 4 gerada com sucesso!")
            st.download_button(
                label="📥 Baixar Planilha 4",
                data=dados_excel,
                file_name="planilha4.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

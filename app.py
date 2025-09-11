import streamlit as st
import pandas as pd
import io
from Soudview import parse_soudview, normalizar_hora, transformar_url_para_csv

st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 📝")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

# =========================
# ABA 1 - Checking (seu código atual)
# =========================
with tab1:
    # aqui você mantém exatamente o código que já tem
    # (aquele fluxo de Planilha 1 vs De/Para)
    # nada muda

# =========================
# ABA 2 - Soudview
# =========================
with tab2:
    st.subheader("Validação da Soudview 🎧")

    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Checking principal)", key="soud_link")
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx"], key="soud_file")

    if link_planilha1 and soud_file:
        try:
            # 1. Ler Soudview e reestruturar
            df_raw = pd.read_excel(soud_file, header=None, engine="openpyxl")
            df_soud = parse_soudview(df_raw)

            # 2. Carregar Checking
            url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
            df_checking = pd.read_csv(url_csv)

            # 3. Normalizar Checking
            df_checking["hora_norm"] = df_checking["hora_veiculacao"].apply(normalizar_hora)
            df_checking["data_norm"] = pd.to_datetime(df_checking["data_contratacao"], errors="coerce")

            # 4. Comparação
            def verificar(row):
                cond = (
                    (df_checking["veiculo_boxnet"].str.contains(row["veiculo"].split()[0], case=False, na=False)) &
                    (df_checking["data_norm"] == row["data"]) &
                    (df_checking["hora_norm"] == row["hora"])
                )
                return "Já no Checking" if cond.any() else "Não encontrado"

            df_soud["status"] = df_soud.apply(verificar, axis=1)

            # Preview na tela
            st.dataframe(df_soud.head(30))

            # 5. Exportar Excel (Planilha 4)
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

import streamlit as st
import pandas as pd
import gdown
import os
from io import BytesIO

st.set_page_config(page_title="Gerador Planilha 3", layout="wide")
st.title("Gerador de Planilha 3 - Verificação de Planos")

# Criar pasta de saída se não existir
if not os.path.exists("outputs"):
    os.makedirs("outputs")

# Input do link da Planilha 1 (Google Drive)
link_drive = st.text_input("Cole o link da Planilha 1 (Google Drive)")

# Upload da Planilha 2
planilha2_file = st.file_uploader("Escolha a Planilha 2 (De/Para)", type=["xlsx"])

if link_drive and planilha2_file:
    try:
        # Extrair ID do Google Drive
        if "drive.google.com" in link_drive:
            try:
                file_id = link_drive.split("/d/")[1].split("/")[0]
            except:
                st.error("Link inválido do Google Drive")
                st.stop()
            download_link = f"https://drive.google.com/uc?id={file_id}"
        else:
            download_link = link_drive

        # Baixar Planilha 1 com gdown
        output_path_1 = "planilha1_temp.xlsx"
        gdown.download(download_link, output_path_1, quiet=False)

        # Ler planilhas
        df1 = pd.read_excel(output_path_1, engine="openpyxl")
        df2 = pd.read_excel(planilha2_file, engine="openpyxl")

        # Padronização de colunas
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

        # Funções de verificação
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

        # Aplicar verificações
        df2['Já na checking'] = df2.apply(verificar_checking, axis=1)
        df2['Plano'] = df2.apply(verificar_plano, axis=1)

        # Gerar Planilha 3 com cores
        output_path = "outputs/planilha3.xlsx"
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df2.to_excel(writer, index=False, sheet_name='Planilha 3')
            workbook = writer.book
            worksheet = writer.sheets['Planilha 3']

            # Formatação
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

        st.success("Planilha 3 gerada com sucesso!")
        st.download_button(
            label="Baixar Planilha 3",
            data=open(output_path, "rb").read(),
            file_name="planilha3.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erro ao processar as planilhas: {e}")

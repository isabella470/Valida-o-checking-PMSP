import streamlit as st
import pandas as pd

# Título do app
st.title("Gerador de Planilha 3 - Verificação de Planos")

# Upload das planilhas
planilha1_file = st.file_uploader("Escolha a Planilha 1 (Relatórios)", type=["xlsx"])
planilha2_file = st.file_uploader("Escolha a Planilha 2 (De/Para)", type=["xlsx"])

if planilha1_file and planilha2_file:
    # Leitura das planilhas
    df1 = pd.read_excel(planilha1_file)
    df2 = pd.read_excel(planilha2_file)

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

    # Converter datas e horas para datetime
    df1['Data'] = pd.to_datetime(df1['Data'])
    df2['Data'] = pd.to_datetime(df2['Data'])
    df1['Hora'] = pd.to_datetime(df1['Hora'], format='%H:%M').dt.time
    df2['Hora'] = pd.to_datetime(df2['Hora'], format='%H:%M').dt.time

    # Função para verificar se já está no checking
    def verificar_checking(row):
        cond = (
            (df1['Veículo'] == row['Veículo']) &
            (df1['Data'] == row['Data']) &
            (df1['Hora'] == row['Hora']) &
            (df1['Título'] == row['Título'])
        )
        return "Já está no checking" if cond.any() else "Não está no checking"

    # Função para verificar plano
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

        # Colunas
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

import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from thefuzz import process, fuzz

# Importa a nova função do arquivo soudview.py
from soudview import parse_soudview

# --- FUNÇÕES AUXILIARES ---

def ler_planilha(uploaded_file):
    """Lê um arquivo enviado pelo usuário, tentando diferentes formatos."""
    try:
        # Tenta ler como Excel, engine=None deixa o pandas decidir entre xlrd e openpyxl
        df = pd.read_excel(uploaded_file, header=None, engine=None)
        return df
    except Exception as e:
        if "zip file" in str(e).lower() or "not a valid excel file" in str(e).lower():
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, header=None)
                return df
            except Exception as csv_error:
                st.error(f"Falha ao ler como Excel ou CSV. Erro: {csv_error}")
                return None
        else:
            st.error(f"Erro inesperado ao ler o arquivo: {e}")
            return None

def transformar_url_para_csv(url: str, aba: str = "Relatórios"):
    """Converte URL do Google Sheets para um link de download CSV."""
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
    except:
        return None

def comparar_planilhas(df_soud, df_checking):
    """Compara as planilhas Soudview e Checking usando fuzzy matching."""
    
    # 1. Padronizar nomes das colunas da planilha principal
    df_checking.columns = df_checking.columns.str.strip().str.upper()
    
    # Renomear colunas esperadas para um padrão
    # ATENÇÃO: Verifique se os nomes das colunas na sua planilha principal batem com estes
    mapa_colunas = {
        'VEICULO_BOXNET': 'VEICULO', 'DATA_CONTRATACAO': 'DATA',
        'HORA_VEICULACAO': 'HORARIO', 'TITULO_PECA': 'COMERCIAL'
    }
    df_checking.rename(columns=mapa_colunas, inplace=True)
    
    # 2. Filtrar a planilha principal para considerar apenas veículos de SP
    df_checking_sp = df_checking[df_checking['VEICULO'].str.contains("/SÃO PAULO", case=False, na=False)].copy()
    
    # 3. Normalizar dados da planilha principal
    df_checking_sp['DATA'] = pd.to_datetime(df_checking_sp['DATA'], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO'] = pd.to_datetime(df_checking_sp['HORARIO'], format='%H:%M:%S', errors='coerce').dt.time

    # 4. Mapeamento Fuzzy dos Nomes dos Veículos
    veiculos_soudview = df_soud['Veiculo_Soudview'].unique()
    veiculos_checking = df_checking_sp['VEICULO'].unique()

    mapa_veiculos = {}
    for veiculo_soud in veiculos_soudview:
        # Usa token_set_ratio que é ótimo para nomes com palavras extras
        match = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
        if match and match[1] >= 80:  # Score de similaridade de 80% ou mais
            mapa_veiculos[veiculo_soud] = match[0]
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            
    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)

    # 5. Merge para encontrar correspondências
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['Veiculo_Mapeado', 'Data', 'Horario'],
        right_on=['VEICULO', 'DATA', 'HORARIO'],
        how='left',
        indicator=True
    )
    
    # 6. Criar a coluna de Status
    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    
    # 7. Limpar e organizar o relatório final
    colunas_finais = ['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Mapeado', 'Status']
    return relatorio[colunas_finais]


# --- LAYOUT DO STREAMLIT ---
st.set_page_config(page_title="Validador de Checking", layout="centered")
st.title("Painel de Validação de Checking 🛠️")

# --- ABA DE VALIDAÇÃO SOUDVIEW ---
st.subheader("Validação da Soudview 🎧")

link_planilha_checking = st.text_input("Passo 1: Cole o link da Planilha Principal (Checking)")
soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview", type=["xlsx", "xls", "csv"])

if st.button("▶️ Iniciar Validação Soudview", use_container_width=True):
    if link_planilha_checking and soud_file:
        with st.spinner("Mapeando a galáxia de dados... 🚀"):
            
            # --- Leitura e Parsing ---
            st.info("1. Lendo e decodificando a planilha Soudview...")
            df_raw = ler_planilha(soud_file)
            if df_raw is not None:
                df_soud = parse_soudview(df_raw)
                
                if df_soud.empty:
                    st.error("Não foi possível extrair nenhum dado da planilha Soudview. Verifique o formato do arquivo.")
                else:
                    st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                    st.dataframe(df_soud.head())

                    # --- Comparação ---
                    st.info("2. Lendo a planilha principal e comparando os dados...")
                    url_csv_checking = transformar_url_para_csv(link_planilha_checking)
                    if url_csv_checking:
                        try:
                            df_checking = pd.read_csv(url_csv_checking)
                            
                            # Chamar a função principal de comparação
                            relatorio_final = comparar_planilhas(df_soud, df_checking)

                            st.success("3. Comparação finalizada! Aqui está o relatório:")
                            st.dataframe(relatorio_final)

                            # --- Download do Relatório ---
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio_Soudview")
                                workbook = writer.book
                                worksheet = writer.sheets["Relatorio_Soudview"]
                                verde = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                                vermelho = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                                
                                status_col_index = relatorio_final.columns.get_loc("Status")
                                for i, status in enumerate(relatorio_final['Status']):
                                    if status == '✅ Já no Checking':
                                        worksheet.write(i + 1, status_col_index, status, verde)
                                    else:
                                        worksheet.write(i + 1, status_col_index, status, vermelho)

                            st.download_button(
                                label="📥 Baixar Relatório Final em Excel",
                                data=output.getvalue(),
                                file_name="Relatorio_Final_Soudview.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

                        except Exception as e:
                            st.error(f"Ocorreu um erro ao processar a planilha principal: {e}")
                    else:
                        st.error("URL da planilha principal inválida.")

    else:
        st.warning("Por favor, preencha o link e faça o upload do arquivo para continuar.")

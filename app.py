import streamlit as st
import pandas as pd
import numpy as np
import io
from rapidfuzz import process, fuzz
import csv
import datetime

try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO: O arquivo 'soudview.py' não foi encontrado.")
    st.stop()

# ---------------- FUNÇÕES ----------------

def ler_csv(file):
    file.seek(0)
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ';'
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')


@st.cache_data
def carregar_depara(caminho="depara.csv"):
    if caminho.endswith(".csv"):
        df = pd.read_csv(caminho)
    else:
        df = pd.read_excel(caminho)
    df['Veiculo_Soudview'] = df['Veiculo_Soudview'].str.lower().str.strip()
    df['Veiculos Boxnet'] = df['Veiculos Boxnet'].str.strip()
    return df

def mapear_veiculo(nome, df_depara, limite_confiança=80):
    nome_norm = nome.lower().strip()
    # 1. Procura exata no de/para
    encontrado = df_depara[df_depara['Veiculo_Soudview'] == nome_norm]
    if not encontrado.empty:
        return encontrado['Veiculos Boxnet'].values[0], None, "✅ De/Para"
    
    # 2. Se não achar, fuzzy match
    candidatos = df_depara['Veiculo_Soudview'].tolist()
    melhor, score, _ = process.extractOne(nome_norm, candidatos, scorer=fuzz.token_sort_ratio)
    if score >= limite_confiança:
        veiculo_boxnet = df_depara[df_depara['Veiculo_Soudview'] == melhor]['Veiculos Boxnet'].values[0]
        return veiculo_boxnet, score, "🤖 Fuzzy"
    
    return "NÃO ENCONTRADO", None, "❌ Não encontrado"


def comparar_planilhas(df_soud, df_checking, df_depara):
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'

    # Normaliza os nomes da Soudview
    df_soud['Veiculo_Normalizado'] = df_soud['Veiculo_Soudview'].str.lower().str.strip()

    # Aplica mapeamento
    resultados = df_soud['Veiculo_Normalizado'].apply(lambda x: mapear_veiculo(x, df_depara))
    df_soud['Veiculo_Mapeado'] = [r[0] for r in resultados]
    df_soud['Score_Similaridade'] = [r[1] for r in resultados]
    df_soud['Tipo_Match'] = [r[2] for r in resultados]

    # Normaliza data/hora
    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce').dt.time

    # Merge
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['Veiculo_Mapeado', 'Data', 'Horario'],
        right_on=[col_veiculo, 'DATA_NORM', 'HORARIO_NORM'],
        how='left',
        indicator=True
    )

    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    relatorio.rename(columns={col_veiculo: 'Veiculo_Principal_Encontrado'}, inplace=True)

    colunas_finais = [
        'Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario',
        'Veiculo_Mapeado', 'Score_Similaridade', 'Tipo_Match',
        'Status', 'Veiculo_Principal_Encontrado'
    ]
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]
    
    return relatorio[colunas_existentes]


# ---------------- STREAMLIT ----------------

st.set_page_config(page_title="Validador de Checking", layout="centered") 
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")
    
    checking_file = st.file_uploader("Passo 1: Upload da Planilha Principal", type=["csv", "xlsx", "xls"])
    soud_file = st.file_uploader("Passo 2: Upload da Planilha Soudview", type=["xlsx", "xls"])
    depara_file = st.file_uploader("Upload do De/Para (CSV ou XLSX)", type=["csv", "xlsx"])

    campanha_selecionada = None

    if soud_file:
        @st.cache_data
        def carregar_e_extrair_campanhas(arquivo):
            df = parse_soudview(pd.read_excel(arquivo, header=None, engine=None))
            if not df.empty:
                return sorted(df['Comercial_Soudview'].unique())
            return []

        soud_file.seek(0)
        lista_de_campanhas = carregar_e_extrair_campanhas(soud_file)
        
        if lista_de_campanhas:
            opcoes_campanha = ["**TODAS AS CAMPANHAS**"] + lista_de_campanhas
            campanha_selecionada = st.selectbox(
                "Passo 3: Selecione a campanha para analisar",
                options=opcoes_campanha
            )

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True):
        if not checking_file or not soud_file or not depara_file:
            st.warning("Por favor, faça o upload das três planilhas: Checking, Soudview e De/Para.")
        elif not campanha_selecionada:
            st.warning("Aguarde a análise das campanhas ou suba um arquivo válido.")
        else:
            with st.spinner("Analisando..."):
                try:
                    # Carrega de/para
                    if depara_file.name.endswith(".csv"):
                        df_depara = pd.read_csv(depara_file)
                    else:
                        df_depara = pd.read_excel(depara_file)
                    df_depara['Veiculo_Soudview'] = df_depara['Veiculo_Soudview'].str.lower().str.strip()
                    df_depara['Veiculos Boxnet'] = df_depara['Veiculos Boxnet'].str.strip()

                    # Carrega Soudview
                    soud_file.seek(0)
                    df_soud = parse_soudview(pd.read_excel(soud_file, header=None, engine=None))
                    
                    if campanha_selecionada == "**TODAS AS CAMPANHAS**":
                        df_soud_filtrado = df_soud
                    else:
                        df_soud_filtrado = df_soud[df_soud['Comercial_Soudview'] == campanha_selecionada]

                    # Carrega Checking
                    if checking_file.name.endswith('.csv'):
                        df_checking = ler_csv(checking_file)
                    else:
                        df_checking = pd.read_excel(checking_file)

                    if df_soud_filtrado.empty:
                        st.error("Nenhuma veiculação encontrada para a campanha selecionada.")
                    else:
                        st.success(f"{len(df_soud_filtrado)} veiculações extraídas para a(s) campanha(s) selecionada(s)!")
                        relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking, df_depara)
                        
                        if not relatorio_final.empty:
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            # Download Excel
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

import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# ==============================================================================
# 1. FUNÇÕES DE LIMPEZA DE DADOS (Sem alterações)
# ==============================================================================
def pre_limpeza(nome):
    nome = str(nome).lower()
    substituicoes = {'s.paulo': 'sao paulo', 'sp': 'sao paulo', 'rj': 'rio de janeiro', 'r.': 'radio'}
    for antigo, novo in substituicoes.items():
        nome = re.sub(r'\b' + re.escape(antigo) + r'\b', novo, nome)
    return nome

def remover_ruido(nome):
    nome = re.sub(r'\d+[\.,]\d+', '', nome)
    palavras_ruido = ['ltda', 's/a', 'eireli', 'radio', 'tv', 'jornal', 'emissora', 'rede', 'fm', 'am']
    for palavra in palavras_ruido:
        nome = re.sub(r'\b' + palavra + r'\b', '', nome)
    return re.sub(r'\s+', ' ', nome).strip()

def normalizar_nome_avancado(nome):
    if pd.isna(nome): return ""
    nome_limpo = pre_limpeza(nome)
    nome_limpo = remover_ruido(nome_limpo)
    nome_final = unidecode(nome_limpo)
    nome_final = re.sub(r'[^a-z0-9 ]', '', nome_final)
    nome_final = re.sub(r'\s+', ' ', nome_final).strip()
    return nome_final

# ==============================================================================
# 2. FUNÇÕES DE LEITURA, MAPEAMENTO E COMPARAÇÃO (Sem alterações)
# ==============================================================================
def ler_csv(file):
    file.seek(0)
    try:
        dialect = csv.Sniffer().sniff(file.read(2048).decode('utf-8', errors='ignore'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ','
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')

def mapear_veiculo(nome, veiculos_principais, limite_confianca):
    nome_norm = normalizar_nome_avancado(nome)
    if not nome_norm: return "NOME VAZIO", None, "⚪ Vazio"
    veiculos_principais_norm = [normalizar_nome_avancado(v) for v in veiculos_principais]
    if veiculos_principais_norm:
        melhor_match, score, _ = process.extractOne(nome_norm, veiculos_principais_norm, scorer=fuzz.WRatio)
        if score >= limite_confianca:
            return melhor_match, score, "🤖 Fuzzy Match"
    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

def comparar_planilhas(df_soud, df_checking, limite_confianca):
    if df_soud.empty: return pd.DataFrame()
    col_emissora = 'emissora'
    col_data = next((c for c in ['data', 'data veiculação'] if c in df_checking.columns), None)
    col_hora = next((c for c in ['hora', 'horario', 'hora veiculação'] if c in df_checking.columns), None)
    if not all([col_emissora, col_data, col_hora]):
        raise KeyError("Não foi possível encontrar as colunas necessárias na Planilha Principal (emissora, data, hora).")
    veiculos_principais = df_checking[col_emissora].dropna().unique().tolist()
    resultados = df_soud['veiculo_soudview'].apply(lambda x: mapear_veiculo(x, veiculos_principais, limite_confianca))
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]
    df_soud_norm = df_soud.copy()
    df_checking_norm = df_checking.copy()
    df_soud_norm['data_merge'] = pd.to_datetime(df_soud_norm['data'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_checking_norm['data_merge'] = pd.to_datetime(df_checking_norm[col_data], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_soud_norm['horario_merge'] = pd.to_datetime(df_soud_norm['horario'], errors='coerce').dt.strftime('%H:%M')
    df_checking_norm['horario_merge'] = pd.to_datetime(df_checking_norm[col_hora], errors='coerce').dt.strftime('%H:%M')
    df_soud_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking_norm['veiculo_merge'] = df_checking_norm[col_emissora].apply(normalizar_nome_avancado)
    relatorio = pd.merge(df_soud_norm, df_checking_norm, left_on=['veiculo_mapeado', 'data_merge', 'horario_merge'], right_on=['veiculo_merge', 'data_merge', 'horario_merge'], how='left', indicator=True)
    relatorio['status'] = np.where(relatorio['_merge'] == 'both', '✅ Encontrado', '❌ Não Encontrado')
    colunas_finais = ['veiculo_soudview', 'comercial_soudview', 'data', 'horario', 'veiculo_mapeado', 'score_similaridade', 'tipo_match', 'status']
    return relatorio[colunas_finais]

# ==============================================================================
# 3. INTERFACE DO STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Validador de Checking", layout="wide") 
st.title("Painel de Validação de Checking 🛠️")

st.sidebar.header("⚙️ Controles de Match")
limite_confianca = st.sidebar.slider("Nível de Confiança para Similaridade (%)", 60, 100, 85, 1)

st.header("1. Carregue os Arquivos")
col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Planilha Principal (Checking)", type=["csv", "xlsx"])
with col2:
    soud_file = st.file_uploader("Planilha Soudview (formato 'wide')", type=["csv", "xlsx"])

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file:
        st.warning("Por favor, carregue a Planilha Principal e a Planilha Soudview.")
    else:
        try:
            from soudview import parse_soudview
            
            soud_file.seek(0)
            if soud_file.name.endswith('.csv'):
                # <<< CORREÇÃO DEFINITIVA AQUI >>>
                # Forçando o uso do ponto-e-vírgula (;) como separador.
                df_soud_bruto = pd.read_csv(soud_file, header=None, sep=';', on_bad_lines='skip')
            else:
                df_soud_bruto = pd.read_excel(soud_file, engine="openpyxl", header=None)

            # A partir daqui, o resto do código já estava correto.
            df_soud, parse_log = parse_soudview(df_soud_bruto)

            with st.expander("🔍 Diagnóstico da Extração da Soudview", expanded=True):
                st.text_area("Log de Processamento do 'soudview.py':", "".join(parse_log), height=300)
                st.info(f"A função de extração da Soudview retornou **{len(df_soud)} linhas**.")
                if df_soud.empty:
                    st.error("Nenhum dado extraído. Analise o log acima para ver por que as linhas foram ignoradas.")
                    st.stop()
                else:
                    st.success("Amostra dos dados extraídos:")
                    st.dataframe(df_soud.head())

            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            else:
                df_checking = pd.read_excel(checking_file, engine="openpyxl")
            df_checking.columns = df_checking.columns.str.strip().str.lower()
            
            with st.spinner("🔎 Comparando planilhas..."):
                relatorio_final = comparar_planilhas(df_soud, df_checking, limite_confianca)

            st.header("2. Relatório da Comparação")
            st.dataframe(relatorio_final)
            
            if not relatorio_final.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                st.download_button("📥 Baixar Relatório Final", output.getvalue(), "Relatorio_Final.xlsx", use_container_width=True)

        except ImportError:
            st.error("Erro Crítico: O arquivo `soudview.py` não foi encontrado na mesma pasta.")
        except KeyError as e:
            st.error(f"❌ Erro de Coluna: {e}. Verifique os cabeçalhos das planilhas.")
        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado.")
            st.exception(e)

import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# ==============================================================================
# 1. FUNÇÕES DE NORMALIZAÇÃO E LEITURA DE ARQUIVOS
# ==============================================================================

def normalizar_nome(nome):
    """Converte um nome para um formato padronizado e limpo."""
    if pd.isna(nome):
        return ""
    nome = str(nome).lower().strip()
    nome = unidecode(nome)  # Remove acentos (ex: "são paulo" -> "sao paulo")
    nome = re.sub(r'[^a-z0-9 ]', '', nome)  # Remove caracteres especiais
    nome = re.sub(r'\s+', ' ', nome)  # Remove espaços extras
    return nome

def ler_csv(file):
    """Lê um arquivo CSV, tentando detectar o separador (vírgula ou ponto e vírgula)."""
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
    """Carrega e normaliza o arquivo De/Para que mapeia nomes de veículos."""
    st.info(f"Carregando arquivo de mapeamento: {caminho}")
    try:
        if caminho.endswith(".csv"):
            df = pd.read_csv(caminho)
        else:
            df = pd.read_excel(caminho)
        
        df.columns = df.columns.str.strip().str.lower()
        df['veiculo_soudview'] = df['veiculo_soudview'].apply(normalizar_nome)
        df['veiculos boxnet'] = df['veiculos boxnet'].apply(normalizar_nome)
        st.success("Arquivo De/Para carregado com sucesso!")
        return df
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{caminho}' não foi encontrado. Verifique se ele está na mesma pasta que o script.")
        return pd.DataFrame(columns=['veiculo_soudview', 'veiculos boxnet'])

# ==============================================================================
# 2. FUNÇÕES DE MAPEAMENTO E COMPARAÇÃO
# ==============================================================================

def mapear_veiculo(nome, df_depara, veiculos_principais, limite_confiança=85):
    """Encontra o nome correspondente de um veículo usando uma lógica de 3 passos."""
    nome_norm = normalizar_nome(nome)
    if not nome_norm:
        return "NOME VAZIO", None, "⚪ Vazio"

    # 1️⃣ Procura exata no De/Para
    encontrado = df_depara[df_depara['veiculo_soudview'] == nome_norm]
    if not encontrado.empty:
        return encontrado['veiculos boxnet'].values[0], 100, "✅ De/Para"

    # 2️⃣ Fuzzy match no De/Para
    candidatos = df_depara['veiculo_soudview'].tolist()
    melhor, score, _ = process.extractOne(nome_norm, candidatos, scorer=fuzz.token_sort_ratio)
    if score >= limite_confiança:
        veiculo_boxnet = df_depara[df_depara['veiculo_soudview'] == melhor]['veiculos boxnet'].values[0]
        return veiculo_boxnet, score, "🤖 Fuzzy De/Para"

    # 3️⃣ Fuzzy match nos veículos principais do Checking
    veiculos_principais_norm = [normalizar_nome(v) for v in veiculos_principais]
    melhor2, score2, _ = process.extractOne(nome_norm, veiculos_principais_norm, scorer=fuzz.token_sort_ratio)
    if score2 >= limite_confiança:
        return melhor2, score2, "🤖 Fuzzy Checking"

    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

def comparar_planilhas(df_soud, df_checking, df_depara):
    """Função principal que orquestra a comparação entre as planilhas."""
    # Definição dos nomes das colunas
    col_soud_veiculo_orig = 'veiculo_soudview'
    col_soud_data = 'data'
    col_soud_horario = 'horario'
    col_check_veiculo = 'veículo boxnet'
    col_check_data = 'data veiculação'
    col_check_horario = 'hora veiculação'
    
    # 1. Normaliza e mapeia os veículos da planilha Soudview
    df_soud[col_soud_veiculo_orig] = df_soud[col_soud_veiculo_orig].apply(normalizar_nome)
    veiculos_principais = df_checking[col_check_veiculo].dropna().unique().tolist()
    resultados = df_soud[col_soud_veiculo_orig].apply(
        lambda x: mapear_veiculo(x, df_depara, veiculos_principais)
    )
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]
    
    # 4. PREPARAÇÃO PARA O MERGE (COM A CORREÇÃO DO ValueError)
    df_soud_norm = df_soud.copy()
    df_checking_norm = df_checking.copy()

    # CORREÇÃO: Converte as chaves de data e hora para string padronizada
    # Isso evita o ValueError causado por tipos de dados mistos (date/time + None)
    df_soud_norm['data_merge'] = pd.to_datetime(df_soud_norm[col_soud_data], errors='coerce').dt.strftime('%Y-%m-%d')
    df_checking_norm['data_merge'] = pd.to_datetime(df_checking_norm[col_check_data], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_soud_norm['horario_merge'] = pd.to_datetime(df_soud_norm[col_soud_horario], errors='coerce').dt.strftime('%H:%M:%S')
    df_checking_norm['horario_merge'] = pd.to_datetime(df_checking_norm[col_check_horario], errors='coerce').dt.strftime('%H:%M:%S')

    # Substitui possíveis valores nulos ('NaT') por uma string vazia para consistência
    df_soud_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)

    df_checking_norm['veiculo_merge'] = df_checking_norm[col_check_veiculo].apply(normalizar_nome)

    # 5. Merge seguro utilizando colunas de string
    relatorio = pd.merge(
        df_soud_norm,
        df_checking_norm,
        left_on=['veiculo_mapeado', 'data_merge', 'horario_merge'],
        right_on=['veiculo_merge', 'data_merge', 'horario_merge'],
        how='left',
        indicator=True
    )

    # 6. Limpeza e organização do relatório final
    relatorio['status'] = np.where(relatorio['_merge'] == 'both', '✅ Encontrado no Checking', '❌ Não encontrado no Checking')
    relatorio.rename(columns={col_check_veiculo: 'veiculo_checking_original'}, inplace=True)

    colunas_finais = [
        'veiculo_soudview', 'comercial_soudview', 'data', 'horario',
        'veiculo_mapeado', 'score_similaridade', 'tipo_match', 'status'
    ]
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]

    return relatorio[colunas_existentes]


# ==============================================================================
# 3. INTERFACE DO STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Validador de Checking", layout="wide") 
st.title("Painel de Validação de Checking 🛠️")

df_depara = carregar_depara("depara.csv")

st.subheader("Validação da Soudview vs. Planilha Principal")

col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Passo 1: Upload da Planilha Principal (Checking)", type=["csv", "xlsx", "xls"])
with col2:
    soud_file = st.file_uploader("Passo 2: Upload da Planilha Soudview", type=["xlsx", "xls"])

campanha_selecionada = None
df_soud = None

if soud_file:
    try:
        from soudview import parse_soudview 
        soud_file.seek(0)
        df_soud = parse_soudview(pd.read_excel(soud_file, header=None))
        df_soud.columns = df_soud.columns.str.strip().str.lower()
        
        if 'veiculo_soudview' not in df_soud.columns or 'comercial_soudview' not in df_soud.columns:
            st.error("A planilha Soudview não foi processada corretamente. Verifique as colunas geradas.")
            df_soud = None
        else:
            campanhas = sorted(df_soud['comercial_soudview'].dropna().unique())
            opcoes_campanha = ["**TODAS AS CAMPANHAS**"] + campanhas
            campanha_selecionada = st.selectbox("Passo 3: Selecione a campanha para analisar", options=opcoes_campanha)
    except ImportError:
        st.error("Erro: Não foi possível encontrar a função `parse_soudview`. Verifique se o arquivo `soudview.py` está na mesma pasta.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo Soudview: {e}")

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file:
        st.warning("Por favor, faça o upload das duas planilhas.")
    elif df_soud is None or df_depara.empty:
        st.error("A validação não pode continuar. Verifique os erros de carregamento dos arquivos acima.")
    else:
        with st.spinner("Analisando dados... Isso pode levar alguns segundos."):
            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            else:
                df_checking = pd.read_excel(checking_file)
            df_checking.columns = df_checking.columns.str.strip().str.lower()

            if campanha_selecionada and campanha_selecionada != "**TODAS AS CAMPANHAS**":
                df_soud_filtrado = df_soud[df_soud['comercial_soudview'] == campanha_selecionada].copy()
            else:
                df_soud_filtrado = df_soud.copy()

            if df_soud_filtrado.empty:
                st.error("Nenhuma veiculação encontrada para a campanha selecionada.")
            else:
                st.success(f"{len(df_soud_filtrado)} veiculações da Soudview prontas para análise!")
                
                relatorio_final = comparar_planilhas(df_soud_filtrado, df_checking, df_depara)

                if relatorio_final.empty:
                    st.error("O relatório final está vazio. Nenhum dado para exibir.")
                else:
                    st.subheader("🎉 Relatório Final da Comparação")
                    st.dataframe(relatorio_final)

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio_Validacao")
                    
                    st.download_button(
                        label="📥 Baixar Relatório Final em Excel",
                        data=output.getvalue(),
                        file_name="Relatorio_Validacao_Soudview.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# =======================================================================
# 1. FUNÇÕES DE LIMPEZA AVANÇADA DE DADOS
# =======================================================================
def pre_limpeza(nome):
    nome = str(nome).lower()
    substituicoes = {
        's.paulo': 'sao paulo', 'sp': 'sao paulo',
        'rj': 'rio de janeiro', 'r.': 'radio',
    }
    for antigo, novo in substituicoes.items():
        nome = re.sub(r'\b' + re.escape(antigo) + r'\b', novo, nome)
    return nome

def remover_ruido(nome):
    nome = re.sub(r'\d+[\.,]\d+', '', nome)
    palavras_ruido = [
        'ltda', 's/a', 'eireli', 'radio', 'tv',
        'jornal', 'emissora', 'rede', 'fm', 'am'
    ]
    for palavra in palavras_ruido:
        nome = re.sub(r'\b' + palavra + r'\b', '', nome)
    return re.sub(r'\s+', ' ', nome).strip()

def normalizar_nome_avancado(nome):
    if pd.isna(nome):
        return ""
    nome_limpo = pre_limpeza(nome)
    nome_limpo = remover_ruido(nome_limpo)
    nome_final = unidecode(nome_limpo)
    nome_final = re.sub(r'[^a-z0-9 ]', '', nome_final)
    nome_final = re.sub(r'\s+', ' ', nome_final).strip()
    return nome_final

# =======================================================================
# 2. FUNÇÃO INTERNA DE PARSING DA SOUDVIEW WIDE FORMAT
# =======================================================================
def parse_soudview(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Parser para planilhas Soudview no formato wide:
    Retorna: veiculo_soudview | comercial_soudview | data | horario
    """
    df = df_bruto.dropna(how="all").reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    veiculo = None
    comercial = None
    resultados = []

    for i, row in df.iterrows():
        # Detecta linha com veículo
        if any(re.search(r"\b(FM|AM|TV)\b", str(cell)) for cell in row):
            veiculo = str(row[0]).strip()
            continue

        # Detecta linha com comercial
        if any(re.search(r"(SPOT|COMERCIAL|ANÚNCIO|ANUNCIO)", str(cell), re.I) for cell in row):
            comercial = str(row[0]).strip()
            continue

        # Detecta linha com datas e horários
        data_str = row[0] if pd.notna(row[0]) else None
        if data_str and re.match(r"\d{2}/\d{2}/\d{2,4}", str(data_str)):
            for col in row.index[1:]:
                horario = row[col]
                if pd.notna(horario):
                    # Normaliza horário e data
                    try:
                        hora_dt = pd.to_datetime(str(horario), errors='coerce')
                        data_dt = pd.to_datetime(str(data_str), dayfirst=True, errors='coerce')
                        resultados.append({
                            "veiculo_soudview": veiculo,
                            "comercial_soudview": comercial,
                            "data": data_dt.strftime("%Y-%m-%d") if pd.notna(data_dt) else None,
                            "horario": hora_dt.strftime("%H:%M:%S") if pd.notna(hora_dt) else None
                        })
                    except:
                        continue

    return pd.DataFrame(resultados)

# =======================================================================
# 3. FUNÇÕES DE LEITURA E MAPEAMENTO
# =======================================================================
def ler_csv(file):
    file.seek(0)
    try:
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        sep = dialect.delimiter
    except (csv.Error, UnicodeDecodeError):
        sep = ';'
    file.seek(0)
    return pd.read_csv(file, sep=sep, encoding='utf-8')

def mapear_veiculo(nome, veiculos_principais, limite_confianca):
    """Função de match que opera apenas por similaridade."""
    nome_norm = normalizar_nome_avancado(nome)
    if not nome_norm:
        return "NOME VAZIO", None, "⚪ Vazio"
    veiculos_principais_norm = [normalizar_nome_avancado(v) for v in veiculos_principais]
    if veiculos_principais_norm:
        melhor_match, score, _ = process.extractOne(
            nome_norm, veiculos_principais_norm, scorer=fuzz.WRatio
        )
        if score >= limite_confianca:
            return melhor_match, score, "🤖 Fuzzy Match"
    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

def comparar_planilhas(df_soud, df_checking, limite_confianca):
    """Orquestra todo o processo de comparação sem usar De/Para."""
    if df_soud.empty:
        return pd.DataFrame()

    veiculos_principais = df_checking['emissora'].dropna().unique().tolist()
    resultados = df_soud['veiculo_soudview'].apply(
        lambda x: mapear_veiculo(x, veiculos_principais, limite_confianca)
    )
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]

    df_soud_norm = df_soud.copy()
    df_checking_norm = df_checking.copy()

    df_soud_norm['data_merge'] = pd.to_datetime(
        df_soud_norm['data'], errors='coerce'
    ).dt.strftime('%Y-%m-%d')
    df_checking_norm['data_merge'] = pd.to_datetime(
        df_checking_norm['data veiculação'], dayfirst=True, errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    df_soud_norm['horario_merge'] = pd.to_datetime(
        df_soud_norm['horario'], errors='coerce'
    ).dt.strftime('%H:%M')
    df_checking_norm['horario_merge'] = pd.to_datetime(
        df_checking_norm['hora veiculação'], errors='coerce'
    ).dt.strftime('%H:%M')

    df_soud_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)

    df_checking_norm['veiculo_merge'] = df_checking_norm['emissora'].apply(
        normalizar_nome_avancado
    )

    relatorio = pd.merge(
        df_soud_norm,
        df_checking_norm,
        left_on=['veiculo_mapeado', 'data_merge', 'horario_merge'],
        right_on=['veiculo_merge', 'data_merge', 'horario_merge'],
        how='left',
        indicator=True,
    )

    relatorio['status'] = np.where(
        relatorio['_merge'] == 'both', '✅ Encontrado', '❌ Não Encontrado'
    )

    colunas_finais = [
        'veiculo_soudview', 'comercial_soudview', 'data', 'horario',
        'veiculo_mapeado', 'score_similaridade', 'tipo_match', 'status'
    ]
    colunas_existentes = [c for c in colunas_finais if c in relatorio.columns]

    return relatorio[colunas_existentes]

# =======================================================================
# 4. INTERFACE STREAMLIT
# =======================================================================
st.set_page_config(page_title="Validador de Checking", layout="wide")
st.title("Painel de Validação de Checking 🛠️")

st.sidebar.header("⚙️ Controles de Match")
limite_confianca = st.sidebar.slider(
    "Nível de Confiança para Similaridade (%)",
    min_value=60, max_value=100, value=85, step=1,
    help="Define o quão parecido um nome deve ser para dar 'match' automático."
)

st.header("1. Carregue os Arquivos")
col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Planilha Principal (Checking)", type=["csv", "xlsx"])
with col2:
    soud_file = st.file_uploader("Planilha Soudview", type=["csv", "xlsx"])

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file:
        st.warning("Por favor, carregue a Planilha Principal e a Planilha Soudview.")
    else:
        try:
            # === Ler Soudview ===
            soud_file.seek(0)
            if soud_file.name.endswith('.csv'):
                df_soud_bruto = ler_csv(soud_file)
            elif soud_file.name.endswith('.xlsx'):
                df_soud_bruto = pd.read_excel(soud_file, engine="openpyxl", header=None)
            else:
                st.error("❌ Formato não suportado. Use apenas .csv ou .xlsx para Soudview.")
                st.stop()

            df_soud = parse_soudview(df_soud_bruto)

            with st.expander("🔍 Diagnóstico da Extração da Soudview", expanded=True):
                st.info(f"A função parse_soudview retornou **{len(df_soud)} linhas**.")
                if df_soud.empty:
                    st.error("Tabela vazia. Ajuste a lógica de parsing.")
                    st.stop()
                else:
                    st.success("Dados extraídos com sucesso! Amostra abaixo:")
                    st.dataframe(df_soud.head())

            df_soud.columns = df_soud.columns.str.strip().str.lower()

            # === Ler Checking ===
            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            elif checking_file.name.endswith('.xlsx'):
                df_checking = pd.read_excel(checking_file, engine="openpyxl")
            else:
                st.error("❌ Formato não suportado. Use apenas .csv ou .xlsx para Checking.")
                st.stop()

            df_checking.columns = df_checking.columns.str.strip().str.lower()

            # === Comparação ===
            with st.spinner("🔎 Analisando por similaridade..."):
                relatorio_final = comparar_planilhas(df_soud, df_checking, limite_confianca)

            # === Resultado ===
            st.header("2. Relatório da Comparação")
            if relatorio_final.empty:
                st.warning("O relatório está vazio. Verifique os dados e horários.")
            else:
                st.dataframe(relatorio_final)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                st.download_button(
                    "📥 Baixar Relatório Final",
                    output.getvalue(),
                    "Relatorio_Final.xlsx",
                    use_container_width=True
                )

        except KeyError as e:
            st.error(f"❌ Erro de Coluna: {e}. Confira os cabeçalhos das planilhas.")
        except Exception as e:
            st.error(f"❌ Erro durante a execução: {e}")
            st.exception(e)

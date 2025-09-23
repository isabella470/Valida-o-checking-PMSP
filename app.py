import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz
from unidecode import unidecode
import re

# ==============================================================================
# 1. FUNÇÕES DE LIMPEZA AVANÇADA DE DADOS
# ==============================================================================

def pre_limpeza(nome):
    """Padroniza abreviações e termos comuns ANTES da normalização principal."""
    nome = str(nome).lower()
    # A correção do NameError está aqui: a variável agora se chama 'substituicoes' nos dois lugares.
    substituicoes = {
        's.paulo': 'sao paulo',
        'sp': 'sao paulo',
        'rj': 'rio de janeiro',
        'r.': 'radio',
        # Adicione outras substituições que você identificar aqui
    }
    for antigo, novo in substituicoes.items():
        nome = re.sub(r'\b' + re.escape(antigo) + r'\b', novo, nome)
    return nome

def remover_ruido(nome):
    """Remove informações que mais atrapalham do que ajudam na comparação."""
    nome = re.sub(r'\d+[\.,]\d+', '', nome)
    palavras_ruido = ['ltda', 's/a', 'eireli', 'radio', 'tv', 'jornal', 'emissora', 'rede', 'fm', 'am']
    for palavra in palavras_ruido:
        nome = re.sub(r'\b' + palavra + r'\b', '', nome)
    return re.sub(r'\s+', ' ', nome).strip()

def normalizar_nome_avancado(nome):
    """Pipeline completo de limpeza e normalização de nomes."""
    if pd.isna(nome):
        return ""
    nome_limpo = pre_limpeza(nome)
    nome_limpo = remover_ruido(nome_limpo)
    nome_final = unidecode(nome_limpo)
    nome_final = re.sub(r'[^a-z0-9 ]', '', nome_final)
    nome_final = re.sub(r'\s+', ' ', nome_final).strip()
    return nome_final

# ==============================================================================
# 2. FUNÇÕES DE LEITURA, MAPEAMENTO E COMPARAÇÃO
# ==============================================================================

def ler_csv(file):
    """Lê um arquivo CSV, tentando detectar o separador."""
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
    """Carrega e normaliza o arquivo De/Para."""
    try:
        df = pd.read_csv(caminho)
        df.columns = df.columns.str.strip().str.lower()
        df['veiculo_soudview'] = df['veiculo_soudview'].apply(normalizar_nome_avancado)
        df['veiculos boxnet'] = df['veiculos boxnet'].apply(normalizar_nome_avancado)
        return df
    except FileNotFoundError:
        st.error(f"Erro: O arquivo de mapeamento '{caminho}' não foi encontrado.")
        return pd.DataFrame(columns=['veiculo_soudview', 'veiculos boxnet'])

def mapear_veiculo(nome, df_depara, veiculos_principais, limite_confianca):
    """Função central de match, usando a normalização avançada."""
    nome_norm = normalizar_nome_avancado(nome)
    if not nome_norm:
        return "NOME VAZIO", None, "⚪ Vazio"

    encontrado = df_depara[df_depara['veiculo_soudview'] == nome_norm]
    if not encontrado.empty:
        return encontrado['veiculos boxnet'].values[0], 100, "✅ De/Para"

    veiculos_principais_norm = [normalizar_nome_avancado(v) for v in veiculos_principais]
    if veiculos_principais_norm:
        melhor_checking, score_checking, _ = process.extractOne(nome_norm, veiculos_principais_norm, scorer=fuzz.WRatio)
        if score_checking >= limite_confianca:
            return melhor_checking, score_checking, "🤖 Fuzzy Checking"

    return "NÃO ENCONTRADO", None, "❌ Não encontrado"

def comparar_planilhas(df_soud, df_checking, df_depara, limite_confianca):
    """Orquestra todo o processo de comparação."""
    veiculos_principais = df_checking['veículo boxnet'].dropna().unique().tolist()
    
    resultados = df_soud['veiculo_soudview'].apply(
        lambda x: mapear_veiculo(x, df_depara, veiculos_principais, limite_confianca)
    )
    df_soud['veiculo_mapeado'] = [r[0] for r in resultados]
    df_soud['score_similaridade'] = [r[1] for r in resultados]
    df_soud['tipo_match'] = [r[2] for r in resultados]
    
    df_soud_norm = df_soud.copy()
    df_checking_norm = df_checking.copy()
    
    df_soud_norm['data_merge'] = pd.to_datetime(df_soud_norm['data'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_checking_norm['data_merge'] = pd.to_datetime(df_checking_norm['data veiculação'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
    df_soud_norm['horario_merge'] = pd.to_datetime(df_soud_norm['horario'], errors='coerce').dt.strftime('%H:%M')
    df_checking_norm['horario_merge'] = pd.to_datetime(df_checking_norm['hora veiculação'], errors='coerce').dt.strftime('%H:%M')
    
    df_soud_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    df_checking_norm.fillna({'data_merge': '', 'horario_merge': ''}, inplace=True)
    
    df_checking_norm['veiculo_merge'] = df_checking_norm['veículo boxnet'].apply(normalizar_nome_avancado)
    
    relatorio = pd.merge(df_soud_norm, df_checking_norm, left_on=['veiculo_mapeado', 'data_merge', 'horario_merge'], right_on=['veiculo_merge', 'data_merge', 'horario_merge'], how='left', indicator=True)
    relatorio['status'] = np.where(relatorio['_merge'] == 'both', '✅ Encontrado', '❌ Não Encontrado')
    
    colunas_finais = ['veiculo_soudview', 'comercial_soudview', 'data', 'horario', 'veiculo_mapeado', 'score_similaridade', 'tipo_match', 'status']
    colunas_existentes = [col for col in colunas_finais if col in relatorio.columns]
    
    return relatorio[colunas_existentes]

# ==============================================================================
# 3. INTERFACE DO STREAMLIT
# ==============================================================================

st.set_page_config(page_title="Validador de Checking", layout="wide") 
st.title("Painel de Validação de Checking 🛠️")

st.sidebar.header("⚙️ Controles de Match")
limite_confianca = st.sidebar.slider(
    "Nível de Confiança para Similaridade (%)",
    min_value=60, max_value=100, value=85, step=1,
    help="Define o quão parecido um nome deve ser para dar 'match' automático. Se a pontuação for menor, será 'Não Encontrado'."
)

st.header("1. Carregue os Arquivos")
df_depara = carregar_depara("depara.csv")

col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Planilha Principal (Checking)", type=["csv", "xlsx", "xls"])
with col2:
    soud_file = st.file_uploader("Planilha Soudview", type=["xlsx", "xls"])

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file or (df_depara is not None and df_depara.empty):
        st.warning("Por favor, carregue a Planilha Principal, a Planilha Soudview e verifique se o arquivo 'depara.csv' existe e não está vazio.")
    else:
        try:
            from soudview import parse_soudview
            soud_file.seek(0)
            df_soud = parse_soudview(pd.read_excel(soud_file, header=None))
            df_soud.columns = df_soud.columns.str.strip().str.lower()

            if checking_file.name.endswith('.csv'):
                df_checking = ler_csv(checking_file)
            else:
                df_checking = pd.read_excel(checking_file)
            df_checking.columns = df_checking.columns.str.strip().str.lower()
            
            with st.spinner("Analisando... A nova limpeza avançada pode levar um pouco mais de tempo."):
                relatorio_final = comparar_planilhas(df_soud, df_checking, df_depara, limite_confianca)

            st.header("2. Relatório da Comparação")
            st.dataframe(relatorio_final)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
            st.download_button("📥 Baixar Relatório Final", output.getvalue(), "Relatorio_Final.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

            nao_encontrados = relatorio_final[relatorio_final['status'] == '❌ Não Encontrado']
            if not nao_encontrados.empty:
                st.header("3. Diagnóstico de Itens Não Encontrados ('Raio-X')")
                st.warning("Use esta análise para encontrar os problemas e melhorar seu arquivo `depara.csv`.")
                
                veiculos_falharam = nao_encontrados['veiculo_soudview'].unique()
                veiculos_checking = df_checking['veículo boxnet'].dropna().unique()
                
                veiculos_checking_norm_map = {normalizar_nome_avancado(v): v for v in veiculos_checking}

                for veiculo in veiculos_falharam:
                    with st.expander(f"🔍 Análise para: **{veiculo}**"):
                        nome_normalizado = normalizar_nome_avancado(veiculo)
                        st.write(f"Nome após limpeza avançada: `{nome_normalizado}`")
                        st.write("Abaixo estão os 5 candidatos mais próximos da sua Planilha Principal (Checking):")
                        
                        candidatos = process.extract(
                            nome_normalizado, 
                            veiculos_checking_norm_map.keys(), 
                            scorer=fuzz.WRatio, 
                            limit=5
                        )
                        
                        if candidatos:
                            nomes_originais = [veiculos_checking_norm_map[c[0]] for c in candidatos]
                            scores = [round(c[1], 2) for c in candidatos]
                            df_candidatos = pd.DataFrame({
                                "Candidato na Planilha Principal": nomes_originais,
                                "Pontuação de Similaridade (%)": scores
                            })
                            st.dataframe(df_candidatos, use_container_width=True)
                            st.info(f"**Ação recomendada:** Se um dos candidatos (ex: '{nomes_originais[0]}') estiver correto, adicione uma linha no seu `depara.csv` com '{veiculo}' na primeira coluna e '{nomes_originais[0]}' na segunda.")
                        else:
                            st.write("Nenhum candidato razoável encontrado.")

        except ImportError:
            st.error("Erro Crítico: Não foi possível encontrar a função `parse_soudview`. Verifique se o arquivo `soudview.py` está na mesma pasta do seu app.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado durante a execução: {e}")

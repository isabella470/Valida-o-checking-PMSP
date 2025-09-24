# app.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz

# Tenta importar parse_soudview do arquivo local
try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO CRÍTICO: O arquivo 'soudview.py' não foi encontrado no mesmo diretório.")
    st.stop()

# ---------------- Funções ----------------
def detectar_separador(file):
    file.seek(0)
    try:
        sample = file.read(1024).decode('utf-8', errors='ignore')
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
    except (csv.Error, UnicodeDecodeError):
        delimiter = ';' # Padrão caso a detecção falhe
    finally:
        file.seek(0)
    return delimiter

def ler_csv(file):
    sep = detectar_separador(file)
    return pd.read_csv(file, sep=sep, encoding='utf-8', engine='python')

def comparar_planilhas(df_soud, df_checking):
    # Ajusta nomes de colunas do Checking
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'
    col_campanha_checking = 'CAMPANHA'

    # Validação de colunas essenciais
    for col in [col_veiculo, col_data, col_horario, col_campanha_checking]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame()

    # --- PREPARAÇÃO DF_CHECKING ---
    df_checking_sp = df_checking[df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)].copy()
    
    # Normaliza datas e horários (robusto contra erros)
    df_checking_sp['data_norm'] = pd.to_datetime(df_checking_sp[col_data], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['horario_norm'] = pd.to_datetime(df_checking_sp[col_horario], errors='coerce', format='%H:%M:%S').dt.time
    df_checking_sp['horario_minuto'] = df_checking_sp['horario_norm'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    
    # Limpeza de veículos: remover espaços, quebras, padronizar string
    df_checking_sp[col_veiculo] = df_checking_sp[col_veiculo].astype(str).str.strip().str.replace(r'\s+', '', regex=True)

    # --- PREPARAÇÃO DF_SOUDVIEW ---
    # **CORREÇÃO**: Usa os nomes de coluna corretos (lowercase) retornados pelo parser
    df_soud['veiculo_soudview_norm'] = df_soud['veiculo_soudview'].astype(str).str.strip().str.replace(r'\s+', '', regex=True)
    df_soud['horario_minuto'] = df_soud['horario'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    df_soud['data_norm'] = pd.to_datetime(df_soud['data']).dt.date

    veiculos_soudview = df_soud['veiculo_soudview_norm'].dropna().unique()
    veiculos_checking = df_checking_sp[col_veiculo].dropna().unique()

    # --- FUZZY MATCHING ---
    mapa_veiculos = {}
    mapa_scores = {}
    for veiculo_soud in veiculos_soudview:
        res = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
        if res:
            match, score, _ = res
            if score >= 80:
                mapa_veiculos[veiculo_soud] = match
                mapa_scores[veiculo_soud] = score
            else:
                mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
                mapa_scores[veiculo_soud] = score # Guarda o score baixo para referência
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            mapa_scores[veiculo_soud] = 0

    df_soud['veiculo_mapeado'] = df_soud['veiculo_soudview_norm'].map(mapa_veiculos)
    df_soud['score_mapeamento'] = df_soud['veiculo_soudview_norm'].map(mapa_scores)

    # --- MERGE ---
    # **CORREÇÃO**: Usa as colunas normalizadas para o merge
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['veiculo_mapeado', 'data_norm', 'horario_minuto', 'comercial_soudview'],
        right_on=[col_veiculo, 'data_norm', 'horario_minuto', col_campanha_checking],
        how='left',
        indicator=True
    )

    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já no Checking', '❌ Não encontrado')
    
    # Renomeia colunas para clareza
    relatorio.rename(columns={
        'veiculo_soudview': 'Veiculo_Soudview_Original',
        'comercial_soudview': 'Comercial_Soudview',
        'data': 'Data_Soudview',
        'horario': 'Horario_Soudview',
        'veiculo_mapeado': 'Veiculo_Mapeado_Checking',
        'score_mapeamento': 'Score_Mapeamento',
    }, inplace=True)
    
    return relatorio[[
        'Veiculo_Soudview_Original',
        'Comercial_Soudview',
        'Data_Soudview',
        'Horario_Soudview',
        'Veiculo_Mapeado_Checking',
        'Score_Mapeamento',
        'Status'
    ]]

# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="Validador de Checking", layout="wide")
st.title("Painel de Validação de Checking 🛠️")

tab1, tab2 = st.tabs(["Validação Checking", "Validação Soudview"])

with tab1:
    st.info("Funcionalidade da Aba 1 a ser implementada.")

with tab2:
    st.subheader("Validação da Soudview vs. Planilha Principal")

    col1, col2 = st.columns(2)
    with col1:
        checking_file = st.file_uploader("Passo 1: Faça upload da Planilha Principal (CSV)", type=["csv"])
    with col2:
        soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview (CSV)", type=["csv"])

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, type="primary"):
        if not checking_file or not soud_file:
            st.warning("Por favor, faça o upload dos dois arquivos para iniciar a validação.")
        else:
            with st.spinner("Analisando arquivos... Por favor, aguarde."):
                try:
                    df_raw_soud = ler_csv(soud_file)
                    df_checking = ler_csv(checking_file)

                    # **CORREÇÃO**: Captura os dois valores retornados pela função
                    df_soud, log_soudview = parse_soudview(df_raw_soud)
                    
                    # **MELHORIA**: Mostra o log de diagnóstico
                    with st.expander("Ver Log de Processamento da Planilha Soudview"):
                        st.code('\n'.join(log_soudview))

                    if df_soud.empty:
                        st.error("Não foi possível extrair dados da planilha Soudview. Verifique o log acima e o formato do arquivo.")
                    else:
                        st.success(f"{len(df_soud)} veiculações extraídas com sucesso da Soudview!")

                        relatorio_final = comparar_planilhas(df_soud, df_checking)
                        
                        if not relatorio_final.empty:
                            st.subheader("🎉 Relatório Final da Comparação")
                            st.dataframe(relatorio_final)

                            # Exporta para Excel
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                            
                            output.seek(0) # Volta ao início do buffer
                            st.download_button(
                                label="📥 Baixar Relatório Final em Excel",
                                data=output,
                                file_name="Relatorio_Validacao_Soudview.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado durante o processamento.")
                    st.exception(e)

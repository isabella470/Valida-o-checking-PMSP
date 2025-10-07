import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
from rapidfuzz import process, fuzz

# Tenta importar a função do arquivo soudview.py
try:
    from soudview import parse_soudview
except ImportError:
    st.error("ERRO CRÍTICO: O arquivo 'soudview.py' não foi encontrado. Certifique-se de que ele está na mesma pasta que o 'app.py'.")
    st.stop()

# ---------------- Funções do App ----------------
def detectar_separador(file):
    """Detecta o separador (vírgula ou ponto e vírgula) de um arquivo CSV."""
    file.seek(0)
    # Lê uma amostra maior para aumentar a chance de detecção correta
    sample = file.read(2048).decode('utf-8', errors='ignore')
    file.seek(0)
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample).delimiter
    except csv.Error:
        # Retorna ';' como padrão se a detecção falhar
        return ';'

def ler_csv(file):
    """Lê um arquivo CSV usando o separador detectado."""
    sep = detectar_separador(file)
    return pd.read_csv(file, sep=sep, encoding='utf-8', on_bad_lines='warn')

def comparar_planilhas(df_soud, df_checking):
    """Compara os dataframes da Soudview e do Checking principal."""
    # Nomes das colunas esperadas na planilha principal
    col_veiculo_checking = 'VEÍCULO BOXNET'
    col_data_checking = 'DATA VEICULAÇÃO'
    col_horario_checking = 'HORA VEICULAÇÃO'
    col_campanha_checking = 'CAMPANHA'

    # Verifica se as colunas essenciais existem
    for col in [col_veiculo_checking, col_data_checking, col_horario_checking, col_campanha_checking]:
        if col not in df_checking.columns:
            st.error(f"Erro Crítico: A coluna '{col}' não foi encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame(), pd.DataFrame() # Retorna dataframes vazios

    # Filtra apenas registros de SÃO PAULO
    df_checking_sp = df_checking[df_checking[col_veiculo_checking].str.contains("SÃO PAULO", case=False, na=False)].copy()
    if df_checking_sp.empty:
        st.warning("Nenhum veículo contendo 'SÃO PAULO' foi encontrado na planilha principal.")
        return pd.DataFrame(), pd.DataFrame()

    # Normalização de Datas e Horários
    df_checking_sp['DATA_NORM'] = pd.to_datetime(df_checking_sp[col_data_checking], dayfirst=True, errors='coerce').dt.date
    df_checking_sp['HORARIO_NORM'] = pd.to_datetime(df_checking_sp[col_horario_checking], errors='coerce').dt.time
    df_checking_sp['HORARIO_MINUTO'] = df_checking_sp['HORARIO_NORM'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    df_soud['HORARIO_MINUTO'] = df_soud['Horario'].apply(lambda x: x.strftime('%H:%M') if pd.notna(x) else np.nan)
    
    # Limpeza dos nomes dos veículos para melhorar o matching
    df_checking_sp['VEICULO_LIMPO'] = df_checking_sp[col_veiculo_checking].astype(str).str.strip().str.replace(r'\s+', '', regex=True).str.upper()
    df_soud['VEICULO_LIMPO'] = df_soud['Veiculo_Soudview'].astype(str).str.strip().str.replace(r'\s+', '', regex=True).str.upper()

    veiculos_soudview = df_soud['VEICULO_LIMPO'].dropna().unique()
    veiculos_checking = df_checking_sp['VEICULO_LIMPO'].dropna().unique()

    # Mapeamento de veículos usando Fuzzy Matching
    mapa_veiculos = {}
    mapa_scores = {}
    for veiculo_soud in veiculos_soudview:
        res = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
        if res:
            match, score, _ = res
            if score >= 80: # Limite de confiança
                mapa_veiculos[veiculo_soud] = match
                mapa_scores[veiculo_soud] = score
            else:
                mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
                mapa_scores[veiculo_soud] = score
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            mapa_scores[veiculo_soud] = 0

    df_soud['Veiculo_Mapeado'] = df_soud['VEICULO_LIMPO'].map(mapa_veiculos)
    df_soud['Score_Mapeamento'] = df_soud['VEICULO_LIMPO'].map(mapa_scores)
    
    # Merge para encontrar correspondências
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['Veiculo_Mapeado', 'HORARIO_MINUTO', 'Comercial_Soudview'],
        right_on=['VEICULO_LIMPO', 'HORARIO_MINUTO', col_campanha_checking],
        how='left',
        indicator=True
    )

    relatorio['Status'] = np.where(relatorio['_merge'] == 'both', '✅ Já está no Checking', '❌ Não encontrado')

    # Cria um dataframe de resumo do mapeamento para exibição
    df_mapeamento = pd.DataFrame(list(mapa_veiculos.items()), columns=['Veiculo_Soudview_Limpo', 'Veiculo_Checking_Correspondente'])
    df_mapeamento['Score'] = df_mapeamento['Veiculo_Soudview_Limpo'].map(mapa_scores)
    df_mapeamento.sort_values(by='Score', ascending=False, inplace=True)
    
    return relatorio[[
        'Veiculo_Soudview',
        'Comercial_Soudview',
        'Data',
        'Horario',
        'Veiculo_Mapeado',
        'Score_Mapeamento',
        'Status'
    ]], df_mapeamento

# ---------------- Interface do Streamlit ----------------
st.set_page_config(page_title="Validador de Checking", layout="wide")
st.title("Painel de Validação de Checking 🛠️")

st.subheader("Validação da Soudview vs. Planilha Principal")

col1, col2 = st.columns(2)
with col1:
    checking_file = st.file_uploader("Passo 1: Faça upload da Planilha Principal (CSV)", type=["csv"])
with col2:
    soud_file = st.file_uploader("Passo 2: Faça upload da Planilha Soudview (CSV)", type=["csv"])

if st.button("▶️ Iniciar Validação", use_container_width=True, type="primary"):
    if not checking_file or not soud_file:
        st.warning("Por favor, faça o upload dos dois arquivos para iniciar a validação.")
    else:
        with st.spinner("Analisando arquivos... Por favor, aguarde."):
            try:
                # Leitura dos arquivos
                df_raw_soud = ler_csv(soud_file)
                df_checking = ler_csv(checking_file)

                # Parsing do arquivo Soudview
                df_soud, log_soud = parse_soudview(df_raw_soud)
                
                if df_soud.empty:
                    st.error("Nenhum dado válido foi extraído da planilha Soudview.")
                    st.text_area("Log da Análise Soudview", "".join(log_soud), height=200)
                else:
                    st.success(f"{len(df_soud)} veiculações extraídas da Soudview!")
                    
                    # Comparação das planilhas
                    relatorio_final, df_mapeamento = comparar_planilhas(df_soud, df_checking)
                    
                    if not relatorio_final.empty:
                        st.subheader("🎉 Relatório Final da Comparação")
                        st.dataframe(relatorio_final)
                        
                        # Botão de Download
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                            relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio_Comparacao")
                            df_mapeamento.to_excel(writer, index=False, sheet_name="Mapeamento_Veiculos")
                        
                        st.download_button(
                            "📥 Baixar Relatório Completo (Excel)",
                            output.getvalue(),
                            "Relatorio_Validacao.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                        # Expander para detalhes técnicos
                        with st.expander("Ver detalhes do processamento"):
                            st.subheader("Mapeamento de Veículos")
                            st.write("Esta tabela mostra como os veículos da Soudview foram mapeados para a planilha principal.")
                            st.dataframe(df_mapeamento)
                            st.subheader("Log da Análise Soudview")
                            st.text_area("Log:", "".join(log_soud), height=300)

            except Exception as e:
                st.error(f"Ocorreu um erro inesperado durante o processamento.")
                st.exception(e)

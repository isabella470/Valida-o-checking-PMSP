import streamlit as st
import pandas as pd
import numpy as np
import io
import csv
import re
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
        delimiter = ';'
    finally:
        file.seek(0)
    return delimiter

def ler_csv(file):
    sep = detectar_separador(file)
    return pd.read_csv(file, sep=sep, encoding='utf-8', engine='python')

def normalizar_veiculo(texto):
    """Normaliza nome do veículo mantendo espaços importantes"""
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    # Remove múltiplos espaços mas mantém um espaço simples
    texto = re.sub(r'\s+', ' ', texto)
    # Remove caracteres especiais mas mantém letras, números e espaços
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto

def comparar_planilhas(df_soud, df_checking):
    """Compara planilhas com validações robustas"""
    
    # Mostra informações de debug
    st.info(f"🔍 Debug: Soudview tem {len(df_soud)} registros")
    st.info(f"🔍 Debug: Colunas Soudview: {df_soud.columns.tolist()}")
    
    # Validação do DataFrame Soudview
    colunas_esperadas_soud = ['veiculo_soudview', 'comercial_soudview', 'data', 'horario']
    colunas_faltantes = [col for col in colunas_esperadas_soud if col not in df_soud.columns]
    
    if colunas_faltantes:
        st.error(f"❌ Colunas faltando na Soudview: {colunas_faltantes}")
        st.info(f"Colunas encontradas: {df_soud.columns.tolist()}")
        return pd.DataFrame()
    
    # Validação do DataFrame Checking
    col_veiculo = 'VEÍCULO BOXNET'
    col_data = 'DATA VEICULAÇÃO'
    col_horario = 'HORA VEICULAÇÃO'
    col_campanha_checking = 'CAMPANHA'

    st.info(f"🔍 Debug: Colunas Checking: {df_checking.columns.tolist()}")
    
    for col in [col_veiculo, col_data, col_horario, col_campanha_checking]:
        if col not in df_checking.columns:
            st.error(f"❌ Coluna '{col}' não encontrada na planilha principal.")
            st.info(f"Colunas encontradas: {df_checking.columns.tolist()}")
            return pd.DataFrame()

    # --- PREPARAÇÃO DF_CHECKING ---
    df_checking_sp = df_checking[
        df_checking[col_veiculo].str.contains("SÃO PAULO", case=False, na=False)
    ].copy()
    
    if df_checking_sp.empty:
        st.warning("⚠️ Nenhum registro de São Paulo encontrado na planilha principal.")
        return pd.DataFrame()
    
    # Normaliza datas e horários
    df_checking_sp['data_norm'] = pd.to_datetime(
        df_checking_sp[col_data], dayfirst=True, errors='coerce'
    ).dt.date
    
    df_checking_sp['horario_norm'] = pd.to_datetime(
        df_checking_sp[col_horario], errors='coerce', format='%H:%M:%S'
    ).dt.time
    
    df_checking_sp['horario_minuto'] = df_checking_sp['horario_norm'].apply(
        lambda x: x.strftime('%H:%M') if pd.notna(x) else None
    )
    
    # Normaliza veículos
    df_checking_sp['veiculo_norm'] = df_checking_sp[col_veiculo].apply(normalizar_veiculo)

    # --- PREPARAÇÃO DF_SOUDVIEW ---
    df_soud = df_soud.copy()
    
    # Normaliza campos da Soudview
    df_soud['veiculo_norm'] = df_soud['veiculo_soudview'].apply(normalizar_veiculo)
    
    df_soud['horario_minuto'] = df_soud['horario'].apply(
        lambda x: x.strftime('%H:%M') if pd.notna(x) else None
    )
    
    df_soud['data_norm'] = pd.to_datetime(df_soud['data'], errors='coerce').dt.date

    # Remove registros inválidos
    df_soud = df_soud.dropna(subset=['data_norm', 'horario_minuto'])
    
    if df_soud.empty:
        st.error("❌ Nenhum registro válido encontrado na Soudview após normalização.")
        return pd.DataFrame()

    # --- FUZZY MATCHING DE VEÍCULOS ---
    veiculos_soudview = df_soud['veiculo_norm'].dropna().unique()
    veiculos_checking = df_checking_sp['veiculo_norm'].dropna().unique()

    st.info(f"🔍 Comparando {len(veiculos_soudview)} veículos da Soudview com {len(veiculos_checking)} do Checking")

    mapa_veiculos = {}
    mapa_scores = {}
    
    for veiculo_soud in veiculos_soudview:
        if not veiculo_soud or veiculo_soud == "VEÍCULO NÃO IDENTIFICADO":
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            mapa_scores[veiculo_soud] = 0
            continue
            
        res = process.extractOne(veiculo_soud, veiculos_checking, scorer=fuzz.token_set_ratio)
        
        if res:
            match, score, _ = res
            if score >= 80:
                mapa_veiculos[veiculo_soud] = match
                mapa_scores[veiculo_soud] = score
            else:
                mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
                mapa_scores[veiculo_soud] = score
        else:
            mapa_veiculos[veiculo_soud] = "NÃO MAPEADO"
            mapa_scores[veiculo_soud] = 0

    df_soud['veiculo_mapeado'] = df_soud['veiculo_norm'].map(mapa_veiculos)
    df_soud['score_mapeamento'] = df_soud['veiculo_norm'].map(mapa_scores)

    # --- MERGE ---
    relatorio = pd.merge(
        df_soud,
        df_checking_sp,
        left_on=['veiculo_mapeado', 'data_norm', 'horario_minuto', 'comercial_soudview'],
        right_on=['veiculo_norm', 'data_norm', 'horario_minuto', col_campanha_checking],
        how='left',
        indicator=True
    )

    relatorio['Status'] = np.where(
        relatorio['_merge'] == 'both', 
        '✅ Já no Checking', 
        '❌ Não encontrado'
    )
    
    # Renomeia e seleciona colunas finais
    colunas_finais = {
        'veiculo_soudview': 'Veiculo_Soudview',
        'comercial_soudview': 'Comercial_Soudview',
        'data': 'Data_Soudview',
        'horario': 'Horario_Soudview',
        'veiculo_mapeado': 'Veiculo_Mapeado',
        'score_mapeamento': 'Score_Match',
        'Status': 'Status'
    }
    
    relatorio = relatorio.rename(columns=colunas_finais)
    
    return relatorio[list(colunas_finais.values())]

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
        checking_file = st.file_uploader(
            "Passo 1: Faça upload da Planilha Principal (CSV)", 
            type=["csv"]
        )
    with col2:
        soud_file = st.file_uploader(
            "Passo 2: Faça upload da Planilha Soudview (CSV)", 
            type=["csv"]
        )

    if st.button("▶️ Iniciar Validação Soudview", use_container_width=True, type="primary"):
        if not checking_file or not soud_file:
            st.warning("⚠️ Por favor, faça o upload dos dois arquivos para iniciar a validação.")
        else:
            with st.spinner("🔄 Analisando arquivos... Por favor, aguarde."):
                try:
                    # Lê os arquivos
                    df_raw_soud = ler_csv(soud_file)
                    df_checking = ler_csv(checking_file)

                    # Processa Soudview
                    df_soud, log_soudview = parse_soudview(df_raw_soud)
                    
                    # Mostra log de diagnóstico
                    with st.expander("📋 Ver Log de Processamento da Soudview"):
                        st.code('\n'.join(log_soudview))

                    if df_soud.empty:
                        st.error("❌ Não foi possível extrair dados da planilha Soudview.")
                        st.info("💡 Verifique o log acima e o formato do arquivo.")
                    else:
                        st.success(f"✅ {len(df_soud)} veiculações extraídas com sucesso da Soudview!")
                        
                        # Mostra prévia dos dados extraídos
                        with st.expander("👀 Prévia dos Dados Extraídos da Soudview"):
                            st.dataframe(df_soud.head(10))

                        # Compara planilhas
                        relatorio_final = comparar_planilhas(df_soud, df_checking)
                        
                        if not relatorio_final.empty:
                            # Estatísticas
                            total = len(relatorio_final)
                            encontrados = (relatorio_final['Status'] == '✅ Já no Checking').sum()
                            nao_encontrados = total - encontrados
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Total de Registros", total)
                            col2.metric("Encontrados no Checking", encontrados, 
                                       delta=f"{(encontrados/total*100):.1f}%")
                            col3.metric("Não Encontrados", nao_encontrados,
                                       delta=f"{(nao_encontrados/total*100):.1f}%",
                                       delta_color="inverse")
                            
                            st.subheader("📊 Relatório Final da Comparação")
                            
                            # Filtros
                            col1, col2 = st.columns(2)
                            with col1:
                                filtro_status = st.multiselect(
                                    "Filtrar por Status:",
                                    options=relatorio_final['Status'].unique(),
                                    default=relatorio_final['Status'].unique()
                                )
                            with col2:
                                filtro_veiculo = st.multiselect(
                                    "Filtrar por Veículo:",
                                    options=relatorio_final['Veiculo_Soudview'].unique()
                                )
                            
                            # Aplica filtros
                            df_filtrado = relatorio_final[
                                relatorio_final['Status'].isin(filtro_status)
                            ]
                            if filtro_veiculo:
                                df_filtrado = df_filtrado[
                                    df_filtrado['Veiculo_Soudview'].isin(filtro_veiculo)
                                ]
                            
                            st.dataframe(df_filtrado, use_container_width=True)

                            # Exporta para Excel
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                                relatorio_final.to_excel(writer, index=False, sheet_name="Relatorio")
                                
                                # Adiciona estatísticas em outra aba
                                stats = pd.DataFrame({
                                    'Métrica': ['Total de Registros', 'Encontrados', 'Não Encontrados'],
                                    'Valor': [total, encontrados, nao_encontrados],
                                    'Percentual': [100, encontrados/total*100, nao_encontrados/total*100]
                                })
                                stats.to_excel(writer, index=False, sheet_name="Estatisticas")
                            
                            output.seek(0)
                            st.download_button(
                                label="📥 Baixar Relatório Final em Excel",
                                data=output,
                                file_name="Relatorio_Validacao_Soudview.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.warning("⚠️ Não foi possível gerar o relatório de comparação.")
                            
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro inesperado durante o processamento.")
                    st.exception(e)

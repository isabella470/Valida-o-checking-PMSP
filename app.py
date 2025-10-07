import streamlit as st
import pandas as pd
import io
import csv
import logging
from datetime import datetime

# Importa módulos locais
try:
    from soudview import parse_soudview
    from comparador import ComparadorPlanilhas
except ImportError as e:
    st.error(f"❌ Erro ao importar módulos: {e}")
    st.info("Certifique-se de que 'soudview.py' e 'comparador.py' estão no mesmo diretório.")
    st.stop()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================== FUNÇÕES AUXILIARES ==================

def detectar_separador(file) -> str:
    """Detecta o separador de um arquivo CSV"""
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

def ler_csv(file) -> pd.DataFrame:
    """Lê arquivo CSV detectando automaticamente o separador"""
    sep = detectar_separador(file)
    return pd.read_csv(file, sep=sep, encoding='utf-8', engine='python')

def exportar_excel(df_resultado: pd.DataFrame, stats: dict) -> bytes:
    """
    Exporta resultado e estatísticas para Excel
    
    Args:
        df_resultado: DataFrame com resultado da comparação
        stats: Dicionário com estatísticas
        
    Returns:
        Bytes do arquivo Excel
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Aba principal com resultados
        df_resultado.to_excel(writer, index=False, sheet_name="Resultado")
        
        # Aba com estatísticas gerais
        df_stats = pd.DataFrame({
            'Métrica': ['Total de Registros', 'Encontrados', 'Não Encontrados', 'Taxa de Match (%)'],
            'Valor': [
                stats['total'], 
                stats['encontrados'], 
                stats['nao_encontrados'],
                stats['taxa_match']
            ]
        })
        df_stats.to_excel(writer, index=False, sheet_name="Estatisticas_Gerais")
        
        # Aba com estatísticas por veículo
        if 'por_veiculo' in stats and stats['por_veiculo']:
            df_veiculos = pd.DataFrame.from_dict(
                stats['por_veiculo'], 
                orient='index'
            ).reset_index()
            df_veiculos.columns = ['Veículo', 'Encontrados', 'Total', 'Taxa_Match (%)']
            df_veiculos.to_excel(writer, index=False, sheet_name="Por_Veiculo")
        
        # Formatação
        workbook = writer.book
        
        # Formato para percentuais
        percent_format = workbook.add_format({'num_format': '0.00"%"'})
        
        # Aplica formatação condicional
        worksheet = writer.sheets['Resultado']
        worksheet.set_column('G:G', 15)  # Coluna Status
        
    output.seek(0)
    return output.getvalue()

def criar_visualizacao_stats(stats: dict):
    """Cria visualização das estatísticas"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Total de Registros", 
            f"{stats['total']:,}".replace(',', '.')
        )
    
    with col2:
        st.metric(
            "✅ Encontrados", 
            f"{stats['encontrados']:,}".replace(',', '.'),
            delta=f"{stats['taxa_match']:.1f}%"
        )
    
    with col3:
        st.metric(
            "❌ Não Encontrados", 
            f"{stats['nao_encontrados']:,}".replace(',', '.'),
            delta=f"{100 - stats['taxa_match']:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "🎯 Taxa de Match",
            f"{stats['taxa_match']:.1f}%"
        )

# ================== CONFIGURAÇÃO STREAMLIT ==================

st.set_page_config(
    page_title="Validador de Checking",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# ================== SIDEBAR ==================

with st.sidebar:
    st.title("⚙️ Configurações")
    
    st.subheader("Parâmetros de Comparação")
    threshold_match = st.slider(
        "Score mínimo para match de veículos",
        min_value=60,
        max_value=100,
        value=85,
        step=5,
        help="Quanto maior, mais rigorosa a comparação (recomendado: 80-90)"
    )
    
    filtro_local = st.text_input(
        "Filtro de localização",
        value="SÃO PAULO",
        help="Texto para filtrar registros do Checking"
    )
    
    st.divider()
    
    st.subheader("📝 Sobre")
    st.info(
        """
        **Validador de Checking v2.0**
        
        Compara dados da Soudview com a planilha principal
        de checking usando:
        - Fuzzy matching para veículos
        - Correspondência exata de data/hora
        - Normalização de texto
        """
    )

# ================== INTERFACE PRINCIPAL ==================

st.title("🛠️ Painel de Validação de Checking")

tab1, tab2 = st.tabs(["📋 Validação Soudview", "📊 Análise de Dados"])

# ========== TAB 1: VALIDAÇÃO SOUDVIEW ==========

with tab1:
    st.header("Validação da Soudview vs. Planilha Principal")
    
    # Upload de arquivos
    col1, col2 = st.columns(2)
    
    with col1:
        checking_file = st.file_uploader(
            "📁 Planilha Principal (Checking)",
            type=["csv"],
            help="Faça upload da planilha de checking em formato CSV"
        )
        if checking_file:
            st.success(f"✓ Arquivo carregado: {checking_file.name}")
    
    with col2:
        soud_file = st.file_uploader(
            "📁 Planilha Soudview",
            type=["csv"],
            help="Faça upload da planilha Soudview em formato CSV"
        )
        if soud_file:
            st.success(f"✓ Arquivo carregado: {soud_file.name}")
    
    st.divider()
    
    # Botão de processamento
    if st.button(
        "🚀 Iniciar Validação",
        use_container_width=True,
        type="primary",
        disabled=not (checking_file and soud_file)
    ):
        
        with st.spinner("🔄 Processando arquivos... Isso pode levar alguns instantes."):
            try:
                # ===== ETAPA 1: Leitura dos arquivos =====
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("📖 Lendo arquivos...")
                df_raw_soud = ler_csv(soud_file)
                df_checking = ler_csv(checking_file)
                progress_bar.progress(20)
                
                # ===== ETAPA 2: Parse da Soudview =====
                status_text.text("🔍 Processando Soudview...")
                df_soud, log_soudview = parse_soudview(df_raw_soud)
                progress_bar.progress(40)
                
                # Mostra log de processamento
                with st.expander("📋 Ver Log de Processamento da Soudview"):
                    st.code('\n'.join(log_soudview), language='text')
                
                if df_soud.empty:
                    st.error("❌ Não foi possível extrair dados da planilha Soudview.")
                    st.info("💡 Verifique o log acima e o formato do arquivo.")
                    st.stop()
                
                st.success(f"✅ {len(df_soud)} veiculações extraídas da Soudview!")
                
                # ===== ETAPA 3: Comparação =====
                status_text.text("⚖️ Comparando planilhas...")
                comparador = ComparadorPlanilhas(threshold_match=threshold_match)
                
                try:
                    df_resultado = comparador.comparar(df_soud, df_checking)
                    progress_bar.progress(80)
                    
                    # ===== ETAPA 4: Estatísticas =====
                    status_text.text("📊 Gerando estatísticas...")
                    stats = comparador.gerar_estatisticas(df_resultado)
                    progress_bar.progress(100)
                    
                    status_text.empty()
                    progress_bar.empty()
                    
                    # ===== RESULTADOS =====
                    st.success("✅ Validação concluída com sucesso!")
                    
                    st.divider()
                    
                    # Métricas principais
                    st.subheader("📈 Resumo Geral")
                    criar_visualizacao_stats(stats)
                    
                    st.divider()
                    
                    # Tabela de resultados
                    st.subheader("📊 Resultados Detalhados")
                    
                    # Filtros
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        filtro_status = st.multiselect(
                            "Filtrar por Status:",
                            options=df_resultado['Status'].unique(),
                            default=df_resultado['Status'].unique()
                        )
                    
                    with col2:
                        veiculos_disponiveis = sorted(df_resultado['Veiculo_Original'].unique())
                        filtro_veiculo = st.multiselect(
                            "Filtrar por Veículo:",
                            options=veiculos_disponiveis
                        )
                    
                    with col3:
                        filtro_data = st.date_input(
                            "Filtrar por Data:",
                            value=None
                        )
                    
                    # Aplica filtros
                    df_filtrado = df_resultado[df_resultado['Status'].isin(filtro_status)]
                    
                    if filtro_veiculo:
                        df_filtrado = df_filtrado[
                            df_filtrado['Veiculo_Original'].isin(filtro_veiculo)
                        ]
                    
                    if filtro_data:
                        df_filtrado = df_filtrado[
                            pd.to_datetime(df_filtrado['Data']).dt.date == filtro_data
                        ]
                    
                    # Exibe tabela
                    st.dataframe(
                        df_filtrado,
                        use_container_width=True,
                        height=400
                    )
                    
                    st.caption(f"Mostrando {len(df_filtrado)} de {len(df_resultado)} registros")
                    
                    # Estatísticas por veículo
                    if stats['por_veiculo']:
                        with st.expander("📊 Estatísticas por Veículo"):
                            df_stats_veiculo = pd.DataFrame.from_dict(
                                stats['por_veiculo'],
                                orient='index'
                            ).reset_index()
                            df_stats_veiculo.columns = ['Veículo', 'Encontrados', 'Total', 'Taxa Match (%)']
                            df_stats_veiculo = df_stats_veiculo.sort_values('Taxa Match (%)', ascending=False)
                            
                            st.dataframe(df_stats_veiculo, use_container_width=True)
                    
                    st.divider()
                    
                    # Exportação
                    st.subheader("💾 Exportar Resultado")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nome_arquivo = f"Relatorio_Validacao_{timestamp}.xlsx"
                    
                    with col2:
                        excel_data = exportar_excel(df_resultado, stats)
                        st.download_button(
                            label="📥 Baixar Excel",
                            data=excel_data,
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                except Exception as e:
                    st.error(f"❌ Erro durante a comparação: {str(e)}")
                    logger.exception("Erro durante comparação")
                    with st.expander("🔍 Detalhes do erro"):
                        st.exception(e)
                
            except Exception as e:
                st.error(f"❌ Erro durante o processamento: {str(e)}")
                logger.exception("Erro durante processamento")
                with st.expander("🔍 Detalhes do erro"):
                    st.exception(e)

# ========== TAB 2: ANÁLISE DE DADOS ==========

with tab2:
    st.header("📊 Análise de Dados")
    st.info("🚧 Funcionalidade em desenvolvimento")
    
    st.markdown("""
    ### Próximas funcionalidades:
    - 📈 Gráficos de tendência temporal
    - 🎯 Análise de taxa de match por período
    - 📊 Dashboard interativo
    - 📉 Identificação de padrões de erro
    """)

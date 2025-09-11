# ==============================================================================
# 1. IMPORTAÇÕES - Todas as bibliotecas para as duas abas

pip install thefuzz python-levenshtein
import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import requests
from io import BytesIO
from thefuzz import process, fuzz

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA - Deve ser o primeiro comando Streamlit
# ==============================================================================
st.set_page_config(page_title="Validador de Checking", layout="wide")

# ==============================================================================
# 2. FUNÇÕES DA ABA 1 (SEU CÓDIGO ORIGINAL)
# ==============================================================================
def pagina_validacao_checking():
    """
    Esta função contém todo o seu código original para a validação de checking.
    """
    st.title("Painel de Validação de Checking (Relatórios vs De/Para) 📝")

    # --- Funções auxiliares da sua aba ---
    def transformar_url_para_csv(url: str, aba: str = "Relatórios") -> str:
        try:
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
            if match:
                sheet_id = match.group(1)
                aba_codificada = requests.utils.quote(aba)
                return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba_codificada}"
        except:
            pass
        return None

    def padronizar_colunas(df):
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df

    # --- Inputs do usuário ---
    link_planilha1 = st.text_input("Passo 1: Cole o link da Planilha 1 (Relatórios)")
    planilha2_file = st.file_uploader("Passo 2: Faça upload da Planilha 2 (De/Para)", type=["xlsx"])

    # --- Processamento ---
    if st.button("Iniciar Validação de Checking", use_container_width=True):
        if link_planilha1 and planilha2_file:
            url_csv = transformar_url_para_csv(link_planilha1, aba="Relatórios")
            if url_csv is None:
                st.error("URL de planilha inválida. Verifique o link.")
            else:
                with st.spinner("Lendo e processando as planilhas..."):
                    try:
                        df1 = pd.read_csv(url_csv, encoding='utf-8')
                    except UnicodeDecodeError:
                        df1 = pd.read_csv(url_csv, encoding='latin1')

                    df2 = pd.read_excel(planilha2_file, engine="openpyxl")

                    df1 = padronizar_colunas(df1)
                    df2 = padronizar_colunas(df2)

                    col_veiculo_1 = "veiculo_boxnet" if "veiculo_boxnet" in df1.columns else df1.columns[0]
                    col_data_1 = "data_contratacao" if "data_contratacao" in df1.columns else df1.columns[1]
                    col_hora_1 = "hora_veiculacao" if "hora_veiculacao" in df1.columns else df1.columns[2]
                    col_titulo_1 = "titulo_peca" if "titulo_peca" in df1.columns else df1.columns[3]

                    col_veiculo_2 = "veiculo" if "veiculo" in df2.columns else df2.columns[0]
                    col_data_2 = "datafonte" if "datafonte" in df2.columns else df2.columns[1]
                    col_hora_2 = "hora" if "hora" in df2.columns else df2.columns[2]
                    col_titulo_2 = "titulo" if "titulo" in df2.columns else df2.columns[3]
                    
                    df1[col_data_1] = pd.to_datetime(df1[col_data_1], errors='coerce')
                    df2[col_data_2] = pd.to_datetime(df2[col_data_2], errors='coerce')

                    df1[col_hora_1] = pd.to_datetime(df1[col_hora_1], format='%H:%M:%S', errors='coerce').dt.time
                    df2[col_hora_2] = pd.to_datetime(df2[col_hora_2], format='%H:%M', errors='coerce').dt.time
                    
                    def zerar_segundos(t):
                        return t.replace(second=0, microsecond=0) if pd.notnull(t) else t

                    df1['hora_ajustada'] = df1[col_hora_1].apply(zerar_segundos)
                    df2['hora_ajustada'] = df2[col_hora_2].apply(zerar_segundos)

                    # Criar chaves para merge
                    df1['chave'] = df1[col_veiculo_1].astype(str) + df1[col_data_1].dt.strftime('%Y-%m-%d').astype(str) + df1['hora_ajustada'].astype(str)
                    df2['chave'] = df2[col_veiculo_2].astype(str) + df2[col_data_2].dt.strftime('%Y-%m-%d').astype(str) + df2['hora_ajustada'].astype(str)
                    
                    # Merge para 'Plano'
                    df_plano_merged = pd.merge(df2, df1[['chave']], on='chave', how='left', indicator=True)
                    df2['Plano'] = np.where(df_plano_merged['_merge'] == 'both', 'Dentro do plano', 'Fora do plano')
                    
                    # Merge para 'Já na checking'
                    df1['chave_checking'] = df1['chave'] + df1[col_titulo_1].astype(str)
                    df2['chave_checking'] = df2['chave'] + df2[col_titulo_2].astype(str)
                    df_checking_merged = pd.merge(df2, df1[['chave_checking']], on='chave_checking', how='left', indicator=True)
                    df2['Já na checking'] = np.where(df_checking_merged['_merge'] == 'both', 'Já está no checking', 'Não está no checking')

                    df2.drop(columns=['hora_ajustada', 'chave', 'chave_checking'], inplace=True)

                    # --- Gerar Excel com cores ---
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        df2.to_excel(writer, index=False, sheet_name="Planilha 3")
                        workbook = writer.book
                        worksheet = writer.sheets["Planilha 3"]
                        verde = workbook.add_format({'bg_color': '#C6EFCE'})
                        vermelho = workbook.add_format({'bg_color': '#FFC7CE'})
                        checking_col = df2.columns.get_loc("Já na checking")
                        plano_col = df2.columns.get_loc("Plano")
                        for row_num, value in enumerate(df2["Já na checking"], 1):
                            if value == "Já está no checking":
                                worksheet.write(row_num, checking_col, value, verde)
                        for row_num, value in enumerate(df2["Plano"], 1):
                            if value == "Dentro do plano":
                                worksheet.write(row_num, plano_col, value, verde)
                            else:
                                worksheet.write(row_num, plano_col, value, vermelho)
                    dados_excel = output.getvalue()
                    st.success("✅ Planilha 3 gerada com sucesso!")
                    st.download_button(
                        label="📥 Baixar Planilha 3",
                        data=dados_excel,
                        file_name="planilha3.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        else:
            st.warning("Por favor, forneça o link e o arquivo para iniciar.")


# ==============================================================================
# 3. FUNÇÕES DA ABA 2 (NOVA FUNCIONALIDADE SOUDVIEW)
# ==============================================================================
def pagina_validacao_soudview():
    st.title("🔎 Validação de Checking: Soudview vs. Principal")

    # --- Funções auxiliares da aba Soudview ---
    def processar_planilha_soudview(uploaded_file):
        try:
            df = pd.read_excel(uploaded_file, header=None)
            dados_estruturados = []
            veiculo_atual = None
            for index, row in df.iterrows():
                valor_celula = str(row.iloc[0]).strip()
                if pd.isna(row.iloc[0]): continue
                if 'Comercial:' in valor_celula:
                    nome_comercial = valor_celula.split('Comercial:')[1].strip()
                    if index + 1 < len(df):
                        data_str = str(df.iloc[index + 1, 0])
                        try:
                            data = pd.to_datetime(data_str, dayfirst=True).date()
                        except (ValueError, TypeError): continue
                        if index + 2 < len(df):
                            horarios_row = df.iloc[index + 2]
                            for horario in horarios_row:
                                if pd.notna(horario):
                                    dados_estruturados.append({
                                        'Veiculo_Soudview': veiculo_atual,
                                        'Comercial_Soudview': nome_comercial,
                                        'Data': data,
                                        'Horario': horario
                                    })
                elif ':' not in valor_celula and '/' not in valor_celula and len(valor_celula) > 3:
                    if index > 0 and 'Comercial:' not in str(df.iloc[index - 1, 0]):
                        veiculo_atual = valor_celula
            return pd.DataFrame(dados_estruturados)
        except Exception as e:
            st.error(f"Erro ao processar a planilha Soudview: {e}")
            return pd.DataFrame()

    def comparar_dados(df_soudview, df_principal):
        col_veiculo_principal = 'VEICULO' # IMPORTANTE: Ajuste se o nome da coluna for diferente
        if col_veiculo_principal not in df_principal.columns:
            st.error(f"A planilha Principal precisa ter uma coluna chamada '{col_veiculo_principal}'")
            return pd.DataFrame()
        df_principal_sp = df_principal[df_principal[col_veiculo_principal].str.contains("/SÃO PAULO", case=False, na=False)].copy()
        veiculos_unicos_principal_sp = df_principal_sp[col_veiculo_principal].unique()
        mapa_veiculos = {
            veiculo_soud: process.extractOne(veiculo_soud, veiculos_unicos_principal_sp, scorer=fuzz.token_set_ratio)[0]
            if process.extractOne(veiculo_soud, veiculos_unicos_principal_sp, scorer=fuzz.token_set_ratio) and process.extractOne(veiculo_soud, veiculos_unicos_principal_sp, scorer=fuzz.token_set_ratio)[1] > 80 else "NÃO MAPEADO"
            for veiculo_soud in df_soudview['Veiculo_Soudview'].unique()
        }
        df_soudview['Veiculo_Principal_Mapeado'] = df_soudview['Veiculo_Soudview'].map(mapa_veiculos)
        df_soudview['Data'] = pd.to_datetime(df_soudview['Data'])
        
        # IMPORTANTE: Ajuste o nome das colunas da sua planilha principal aqui
        df_principal_sp['Data'] = pd.to_datetime(df_principal_sp['DATA'])
        df_principal_sp['Horario_Principal'] = pd.to_datetime(df_principal_sp['HORARIO'], format='%H:%M:%S', errors='coerce').dt.time
        
        # Merge
        relatorio_final = pd.merge(
            df_soudview,
            df_principal_sp,
            left_on=['Veiculo_Principal_Mapeado', 'Data', pd.to_datetime(df_soudview['Horario'], format='%H:%M:%S', errors='coerce').dt.time],
            right_on=[col_veiculo_principal, 'Data', 'Horario_Principal'],
            how='left',
            indicator=True
        )
        relatorio_final['Status'] = np.where(relatorio_final['_merge'] == 'both', '✅ Encontrado na Principal', '❌ Não Encontrado')
        return relatorio_final[['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario', 'Veiculo_Principal_Mapeado', 'Status']]

    # --- Interface da aba Soudview ---
    st.info("""
        **Como usar:**
        1.  **Carregue a planilha da Soudview** no primeiro campo.
        2.  **Carregue sua planilha Principal** de checking (a mesma que você usa na outra aba) no segundo campo.
    """)

    col1, col2 = st.columns(2)
    with col1:
        soudview_file = st.file_uploader("1. Planilha Soudview", type=["xlsx", "xls"], key="soudview")
    with col2:
        principal_file = st.file_uploader("2. Planilha Principal (Checking)", type=["xlsx", "xls"], key="principal_soud")

    if st.button("🚀 Iniciar Validação Soudview", use_container_width=True):
        if soudview_file and principal_file:
            with st.spinner("Processando e analisando os dados... Por favor, aguarde."):
                st.subheader("Etapa 1: Planilha Soudview Reestruturada")
                df_soudview_estruturada = processar_planilha_soudview(soudview_file)
                if not df_soudview_estruturada.empty:
                    st.dataframe(df_soudview_estruturada)
                    st.subheader("Etapa 2: Relatório Final de Conferência")
                    df_principal = pd.read_excel(principal_file)
                    relatorio = comparar_dados(df_soudview_estruturada, df_principal)
                    if not relatorio.empty:
                        st.dataframe(relatorio)
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            relatorio.to_excel(writer, index=False, sheet_name='Relatorio_Soudview')
                        st.download_button(
                            label="📥 Baixar Relatório Completo",
                            data=output.getvalue(),
                            file_name="relatorio_conferencia_soudview.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
        else:
            st.warning("Por favor, carregue ambos os arquivos para iniciar a validação.")

# ==============================================================================
# 4. CONTROLE DE NAVEGAÇÃO - A função principal que roda o app
# ==============================================================================
def main():
    st.sidebar.title("Menu de Navegação")
    paginas = ["Validação de Checking", "Validação Soudview"]
    selecao = st.sidebar.selectbox("Escolha a funcionalidade", paginas)

    if selecao == "Validação de Checking":
        pagina_validacao_checking()
    elif selecao == "Validação Soudview":
        pagina_validacao_soudview()

if __name__ == "__main__":
    main()


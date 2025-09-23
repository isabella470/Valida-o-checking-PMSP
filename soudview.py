# Conteúdo para o arquivo: soudview.py

import pandas as pd

def parse_soudview(df_bruto):
    """
    Função personalizada para extrair dados da planilha Soudview, baseada no
    arquivo de exemplo 'Soundview_PRESTACAO-DE-SERVICOS-....csv'.
    """
    try:
        # 1. Extrai o nome do comercial. No seu arquivo, ele está na célula C4.
        #    Pandas lê isso como linha 3, coluna 2.
        nome_comercial = df_bruto.iloc[3, 2]

        # 2. Define que a tabela de dados começa na linha 7 (índice 6).
        df_dados = df_bruto.iloc[6:].copy()

        # 3. Renomeia as colunas da tabela para facilitar o acesso.
        #    O seu arquivo tem 9 colunas de dados a partir deste ponto.
        df_dados.columns = [
            'veiculo_soudview', 'programa', 'formato', 'titulo', 'duracao', 
            'versao', 'genero', 'data', 'horario'
        ]

        # 4. Adiciona a coluna com o nome do comercial a todas as linhas.
        df_dados['comercial_soudview'] = nome_comercial
        
        # 5. Remove linhas que possam estar completamente vazias, garantindo dados limpos.
        df_dados.dropna(subset=['veiculo_soudview', 'data', 'horario'], how='all', inplace=True)
        
        # 6. Seleciona e retorna apenas as colunas que o app principal precisa.
        colunas_necessarias = ['comercial_soudview', 'veiculo_soudview', 'data', 'horario']
        
        return df_dados[colunas_necessarias]

    except Exception as e:
        # Se ocorrer qualquer erro durante a extração, ele será mostrado no terminal.
        print(f"!!! ERRO ao processar a planilha Soudview em 'soudview.py': {e}")
        # E retorna uma tabela vazia para não quebrar o aplicativo principal.
        return pd.DataFrame()

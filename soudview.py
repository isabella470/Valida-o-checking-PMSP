import pandas as pd

def parse_soudview(df_bruto):
    """
    Função personalizada para extrair dados da planilha Soudview enviada.
    """
    try:
        # 1. Extrai o nome do comercial/campanha. No seu arquivo, ele está na célula C4 (linha 3, coluna 2).
        nome_comercial = df_bruto.iloc[3, 2]

        # 2. Define que os dados da tabela começam na linha 7 (índice 6).
        df_dados = df_bruto.iloc[6:].copy()

        # 3. Define os nomes corretos para as colunas da tabela, conforme o layout.
        df_dados.columns = [
            'veiculo_soudview', 'programa', 'formato', 'titulo', 'duracao', 
            'versao', 'genero', 'data', 'horario'
        ]

        # 4. Adiciona a coluna com o nome do comercial.
        df_dados['comercial_soudview'] = nome_comercial
        
        # 5. Remove linhas que possam estar completamente vazias.
        df_dados.dropna(subset=['veiculo_soudview', 'data', 'horario'], how='all', inplace=True)
        
        # 6. Seleciona e retorna apenas as colunas que o app principal precisa.
        colunas_necessarias = ['comercial_soudview', 'veiculo_soudview', 'data', 'horario']
        
        return df_dados[colunas_necessarias]

    except Exception as e:
        print(f"!!! ERRO em soudview.py: {e}")
        # Retorna um DataFrame vazio em caso de erro.
        return pd.DataFrame({
            'comercial_soudview': [], 'veiculo_soudview': [], 'data': [], 'horario': []
        })

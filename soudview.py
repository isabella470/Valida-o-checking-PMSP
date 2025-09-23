import pandas as pd

def parse_soudview(df_bruto):
    """
    Esta função recebe o DataFrame bruto e o transforma em um formato organizado.
    Siga os comentários para adaptar esta lógica ao seu arquivo.
    """
    
    # --- DEBUG: Imprime as 10 primeiras linhas do arquivo bruto no terminal ---
    # Isso ajuda você a ver os números das linhas e colunas.
    print("--- Amostra do Arquivo Bruto (soudview.py) ---")
    print(df_bruto.head(10))
    print("-------------------------------------------------")
    
    try:
        # ======================================================================
        # ADAPTE AS VARIÁVEIS ABAIXO
        # ======================================================================

        # 1. Em qual LINHA os seus dados (a lista de veiculações) começam?
        #    Lembre-se que a contagem começa em 0 (Linha 1 = 0, Linha 2 = 1, etc.)
        #    Exemplo: Se seus dados começam na sexta linha do Excel, use 5.
        LINHA_INICIAL_DADOS = 5 

        # 2. Em qual COLUNA está cada informação?
        #    (Coluna A = 0, Coluna B = 1, Coluna C = 2, etc.)
        COLUNA_VEICULO = 0  # Exemplo: Veículo na Coluna A
        COLUNA_DATA = 2     # Exemplo: Data na Coluna C
        COLUNA_HORARIO = 3  # Exemplo: Horário na Coluna D
        
        # 3. (Opcional) Onde está o nome do COMERCIAL/CAMPANHA?
        #    Muitas vezes fica em uma única célula no topo do arquivo.
        #    Exemplo: Linha 2 (índice 1), Coluna B (índice 1)
        LINHA_COMERCIAL = 1
        COLUNA_COMERCIAL = 1
        nome_comercial = df_bruto.iloc[LINHA_COMERCIAL, COLUNA_COMERCIAL]

        # ======================================================================
        # A LÓGICA ABAIXO USA AS VARIÁVEIS QUE VOCÊ DEFINIU
        # ======================================================================
        
        # Pula as linhas de cabeçalho
        df_dados = df_bruto.iloc[LINHA_INICIAL_DADOS:].copy()

        # Cria o DataFrame final com base nos números das colunas
        df_final = pd.DataFrame({
            'comercial_soudview': nome_comercial,
            'veiculo_soudview': df_dados.iloc[:, COLUNA_VEICULO],
            'data': df_dados.iloc[:, COLUNA_DATA],
            'horario': df_dados.iloc[:, COLUNA_HORARIO]
        })

        # Limpa linhas que ficaram totalmente vazias
        df_final.dropna(how='all', subset=['veiculo_soudview', 'data', 'horario'], inplace=True)
        
        # --- DEBUG: Imprime o resultado final no terminal ---
        print(f"--- Resultado do Parse (soudview.py): {len(df_final)} linhas extraídas ---")
        print(df_final.head())
        print("-------------------------------------------------")

        return df_final

    except (IndexError, KeyError) as e:
        # Se os números de linha/coluna estiverem errados, um erro acontecerá.
        # Esta mensagem ajudará a identificar o problema.
        print(f"!!! ERRO em soudview.py: Não foi possível encontrar a linha/coluna especificada. Verifique suas variáveis. Erro: {e}")
        # Retorna um DataFrame vazio em caso de erro para não quebrar o app principal.
        return pd.DataFrame({
            'comercial_soudview': [], 'veiculo_soudview': [], 'data': [], 'horario': []
        })

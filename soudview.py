import pandas as pd

def parse_soudview(df_bruto):
    """
    Esta função recebe um DataFrame 'bruto' (lido diretamente do Excel sem cabeçalho)
    e o transforma em um DataFrame organizado com colunas padronizadas.
    
    VOCÊ PRECISA ADAPTAR ESTA FUNÇÃO PARA O SEU ARQUIVO ESPECÍFICO.
    """
    
    # --------------------------------------------------------------------------
    # PASSO 1: EXTRAIR O NOME DA CAMPANHA (SE NECESSÁRIO)
    # --------------------------------------------------------------------------
    # Muitas vezes, o nome da campanha/comercial fica numa célula específica,
    # por exemplo, na primeira linha (índice 0) e primeira coluna (índice 0).
    # Adapte os números de [linha, coluna] conforme sua planilha.
    try:
        # Exemplo: Pega o valor da célula A1
        nome_comercial = df_bruto.iloc[0, 0] 
    except IndexError:
        nome_comercial = "Campanha Padrão"

    # --------------------------------------------------------------------------
    # PASSO 2: ENCONTRAR ONDE OS DADOS REALMENTE COMEÇAM
    # --------------------------------------------------------------------------
    # Pule as linhas de cabeçalho ou em branco até encontrar a primeira linha de dados.
    # Exemplo: Supondo que os dados comecem na linha 5 (índice 4).
    df_dados = df_bruto.iloc[4:].copy()

    # --------------------------------------------------------------------------
    # PASSO 3: CRIAR O DATAFRAME ORGANIZADO
    # --------------------------------------------------------------------------
    # Crie um novo DataFrame pegando as colunas corretas do df_dados.
    # **ESTA É A PARTE MAIS IMPORTANTE PARA ADAPTAR.**
    
    # Suponha que no seu Excel:
    # - Coluna A (índice 0) tem o nome do veículo.
    # - Coluna C (índice 2) tem a data da veiculação.
    # - Coluna D (índice 3) tem a hora da veiculação.
    
    df_final = pd.DataFrame({
        # Adiciona o nome do comercial que extraímos em todas as linhas
        'comercial_soudview': nome_comercial,
        
        # Pega a primeira coluna do Excel (df_dados.iloc[:, 0]) e a nomeia como 'veiculo_soudview'
        'veiculo_soudview': df_dados.iloc[:, 0],
        
        # Pega a terceira coluna (df_dados.iloc[:, 2]) e a nomeia como 'data'
        'data': df_dados.iloc[:, 2],
        
        # Pega a quarta coluna (df_dados.iloc[:, 3]) e a nomeia como 'horario'
        'horario': df_dados.iloc[:, 3]
    })

    # --------------------------------------------------------------------------
    # PASSO 4: LIMPEZA FINAL
    # --------------------------------------------------------------------------
    # Remove linhas que possam estar completamente vazias
    df_final.dropna(how='all', subset=['veiculo_soudview', 'data', 'horario'], inplace=True)

    return df_final

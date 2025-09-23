import pandas as pd

def parse_soudview(df_bruto):
    """
    Função de teste MÍNIMA.
    Ela não faz nada complexo, apenas retorna um DataFrame vazio
    com as colunas que o aplicativo principal espera.
    """
    print("--- A FUNÇÃO parse_soudview FOI CHAMADA COM SUCESSO! ---") # Isso aparecerá no seu terminal
    
    # Retorna uma estrutura de dados válida e vazia
    return pd.DataFrame({
        'comercial_soudview': [],
        'veiculo_soudview': [],
        'data': [],
        'horario': []
    })

# Conteúdo para o arquivo: soudview.py (Versão de Diagnóstico)

import pandas as pd

def parse_soudview(df_bruto):
    """
    Função de diagnóstico para extrair dados da planilha Soudview.
    Ela imprimirá informações úteis no terminal.
    """
    
    # --- INÍCIO DO DIAGNÓSTICO ---
    print("\n--- DIAGNÓSTICO DENTRO DE soudview.py ---")
    print(f"Formato do DataFrame bruto recebido: {df_bruto.shape[0]} linhas, {df_bruto.shape[1]} colunas")
    print("Amostra do DataFrame bruto (primeiras 10 linhas):")
    print(df_bruto.head(10))
    print("-------------------------------------------\n")
    # --- FIM DO DIAGNÓSTICO ---

    try:
        # --- LÓGICA DE EXTRAÇÃO (BASEADA NO ARQUIVO QUE VOCÊ ENVIOU) ---
        
        # 1. Extrai o nome do comercial da célula C4 (linha 3, coluna 2)
        nome_comercial = df_bruto.iloc[3, 2]
        print(f"Nome do comercial extraído: '{nome_comercial}'")

        # 2. Define que os dados da tabela começam na linha 7 (índice 6)
        df_dados = df_bruto.iloc[6:].copy()
        print(f"DataFrame de dados criado a partir da linha 7. Formato: {df_dados.shape}")

        # 3. Define os nomes das colunas. Esperamos 9 colunas aqui.
        nomes_colunas = [
            'veiculo_soudview', 'programa', 'formato', 'titulo', 'duracao', 
            'versao', 'genero', 'data', 'horario'
        ]
        
        # Validação importante: O número de colunas bate com o esperado?
        if len(df_dados.columns) != len(nomes_colunas):
            print(f"!!! ERRO: Incompatibilidade de colunas!")
            print(f"    - O script esperava {len(nomes_colunas)} colunas.")
            print(f"    - Mas os dados a partir da linha 7 têm {len(df_dados.columns)} colunas.")
            print(f"    - Causa provável: O separador (vírgula ou ponto-e-vírgula) pode estar errado na leitura do CSV.")
            return pd.DataFrame() # Retorna vazio

        df_dados.columns = nomes_colunas
        print("Nomes das colunas definidos com sucesso.")
        
        # 4. Adiciona a coluna com o nome do comercial
        df_dados['comercial_soudview'] = nome_comercial
        
        # 5. Remove linhas que possam estar totalmente vazias
        df_dados.dropna(subset=['veiculo_soudview', 'data', 'horario'], how='all', inplace=True)
        
        # 6. Seleciona e retorna apenas as colunas que o app principal precisa
        colunas_necessarias = ['comercial_soudview', 'veiculo_soudview', 'data', 'horario']
        df_final = df_dados[colunas_necessarias]
        
        print(f"Processamento concluído. {len(df_final)} linhas extraídas.")
        return df_final

    except Exception as e:
        # Se qualquer erro ocorrer, ele será impresso no terminal
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! OCORREU UM ERRO DENTRO DO 'soudview.py' !!!")
        print(f"!!! ERRO: {e}")
        print("!!! Causa provável: Os números de linha/coluna (ex: iloc[3, 2]) estão fora dos limites do arquivo.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        
        # Retorna um DataFrame vazio em caso de erro
        return pd.DataFrame()

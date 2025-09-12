import pandas as pd
import re
import datetime

def parse_soudview(df_raw):
    """
    Versão final e robusta que usa 'forward fill' e agora captura
    corretamente TODOS os horários de uma mesma linha de data.
    """
    
    # 1. Cria colunas temporárias extraindo o valor de Veículo e Comercial
    df_raw['VEICULO_TEMP'] = df_raw.iloc[:, 0].astype(str).str.extract(r'Veículo\s*:\s*(.*)', flags=re.IGNORECASE)
    df_raw['COMERCIAL_TEMP'] = df_raw.iloc[:, 0].astype(str).str.extract(r'Comercial\s*:\s*(.*)', flags=re.IGNORECASE)

    # 2. Preenche os valores para baixo (forward fill)
    df_raw['VEICULO_CONTEXTO'] = df_raw['VEICULO_TEMP'].ffill()
    df_raw['COMERCIAL_CONTEXTO'] = df_raw['COMERCIAL_TEMP'].ffill()

    # 3. Filtra apenas as linhas que são de dados (cujo primeiro valor é uma data)
    def eh_data(valor):
        if not isinstance(valor, str): return False
        try:
            pd.to_datetime(valor, dayfirst=True)
            return True
        except (ValueError, TypeError):
            return False
            
    df_data_rows = df_raw[df_raw.iloc[:, 0].apply(eh_data)].copy()
    
    if df_data_rows.empty:
        return pd.DataFrame()

    # 4. Processa as linhas de dados para extrair CADA horário
    dados_finais = []
    for index, row in df_data_rows.iterrows():
        veiculo = row['VEICULO_CONTEXTO']
        comercial = row['COMERCIAL_CONTEXTO']
        
        try:
            data = pd.to_datetime(row.iloc[0], dayfirst=True).date()
        except (ValueError, TypeError):
            continue

        # --- LÓGICA CORRIGIDA AQUI ---
        # Itera por cada célula da segunda coluna em diante
        for horario_bruto in row.iloc[1:]:
            # Verifica se a célula não está vazia
            if pd.notna(horario_bruto):
                try:
                    # Tenta converter o valor da célula para um objeto de tempo
                    horario_obj = pd.to_datetime(str(horario_bruto), errors='coerce').time()
                    if horario_obj:
                        # Se conseguir, adiciona a linha completa aos nossos dados
                        dados_finais.append({
                            'Veiculo_Soudview': veiculo,
                            'Comercial_Soudview': comercial,
                            'Data': data,
                            'Horario': horario_obj
                        })
                except (ValueError, TypeError):
                    # Se não for um formato de hora válido, simplesmente ignora e continua para a próxima célula
                    continue
                    
    return pd.DataFrame(dados_finais)

import pandas as pd
import datetime
import re

def parse_soudview(df_raw):
    """
    Versão mais robusta que ignora maiúsculas/minúsculas e espaços extras
    ao procurar por 'Veículo:' e 'Comercial:'.
    """
    dados_estruturados = []
    veiculo_atual = None

    for index, row in df_raw.iterrows():
        if pd.isna(row.iloc[0]):
            continue
        
        valor_celula = str(row.iloc[0]).strip()

        # 1. Identificar o veículo (de forma robusta)
        match_veiculo = re.search(r'Veículo\s*:\s*(.*)', valor_celula, re.IGNORECASE)
        if match_veiculo:
            veiculo_atual = match_veiculo.group(1).strip()
            continue

        # 2. Identificar o comercial (de forma robusta)
        match_comercial = re.search(r'Comercial\s*:\s*(.*)', valor_celula, re.IGNORECASE)
        if match_comercial:
            nome_comercial = match_comercial.group(1).strip()

            if index + 1 < len(df_raw):
                linha_de_dados = df_raw.iloc[index + 1]
                
                try:
                    data_obj = pd.to_datetime(linha_de_dados.iloc[0], dayfirst=True)
                except (ValueError, TypeError):
                    continue

                for horario in linha_de_dados.iloc[1:].dropna():
                    try:
                        horario_obj = pd.to_datetime(str(horario), format='%H:%M:%S', errors='coerce').time()
                        if horario_obj and veiculo_atual:
                            dados_estruturados.append({
                                'Veiculo_Soudview': veiculo_atual,
                                'Comercial_Soudview': nome_comercial,
                                'Data': data_obj.date(),
                                'Horario': horario_obj
                            })
                    except (ValueError, TypeError):
                        continue
    
    if not dados_estruturados:
        return pd.DataFrame()
        
    return pd.DataFrame(dados_estruturados)

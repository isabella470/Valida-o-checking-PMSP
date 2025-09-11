import pandas as pd
import datetime
import re

def eh_data(texto):
    """Verifica se um texto pode ser interpretado como uma data."""
    try:
        pd.to_datetime(texto, dayfirst=True)
        return True
    except (ValueError, TypeError):
        return False

def parse_soudview(df_raw):
    """
    Versão final que entende a estrutura de múltiplas linhas de data para um único comercial.
    """
    dados_estruturados = []
    veiculo_atual = None
    comercial_atual = None

    for index, row in df_raw.iterrows():
        # Pega o valor da primeira coluna, que é a mais importante
        primeira_celula = str(row.iloc[0]).strip()

        if pd.isna(row.iloc[0]) or primeira_celula == 'nan':
            continue

        # Procura por "Veículo:" para atualizar o veículo atual
        match_veiculo = re.search(r'Veículo\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_veiculo:
            veiculo_atual = match_veiculo.group(1).strip()
            comercial_atual = None # Reseta o comercial ao encontrar um novo veículo
            continue

        # Procura por "Comercial:" para atualizar o comercial atual
        match_comercial = re.search(r'Comercial\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_comercial:
            comercial_atual = match_comercial.group(1).strip()
            continue

        # >>> A MÁGICA ACONTECE AQUI <<<
        # Se a primeira célula for uma data, e já tivermos um comercial na memória...
        if eh_data(primeira_celula) and comercial_atual and veiculo_atual:
            data_obj = pd.to_datetime(primeira_celula, dayfirst=True).date()

            # Itera por TODAS as outras células da mesma linha para pegar os horários
            for horario in row.iloc[1:].dropna():
                try:
                    # Tenta converter para um objeto de tempo
                    horario_obj = pd.to_datetime(str(horario), errors='coerce').time()
                    if horario_obj:
                        dados_estruturados.append({
                            'Veiculo_Soudview': veiculo_atual,
                            'Comercial_Soudview': comercial_atual,
                            'Data': data_obj,
                            'Horario': horario_obj
                        })
                except (ValueError, TypeError):
                    # Ignora se o valor não for um horário válido
                    continue
    
    if not dados_estruturados:
        return pd.DataFrame()
        
    return pd.DataFrame(dados_estruturados)

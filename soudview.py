import pandas as pd
import datetime
import re

def eh_data(texto):
    """Verifica se um texto pode ser interpretado como uma data."""
    try:
        # Tenta converter, se falhar, não é uma data válida
        pd.to_datetime(texto, dayfirst=True)
        return True
    except (ValueError, TypeError):
        return False

def parse_horario_flexivel(horario_bruto):
    """
    Tenta converter um valor de horário em vários formatos possíveis.
    Esta é a função chave para resolver o problema.
    """
    if isinstance(horario_bruto, datetime.time):
        return horario_bruto
    
    horario_str = str(horario_bruto)
    
    # Tenta o formato completo primeiro
    try:
        return pd.to_datetime(horario_str, format='%H:%M:%S').time()
    except ValueError:
        pass
    
    # Tenta o formato com um dígito no segundo
    try:
        return pd.to_datetime(horario_str, format='%H:%M:%S.%f').time() # Formato que o pandas usa para ler do excel
    except ValueError:
        pass

    # Tenta o formato HH:MM
    try:
        return pd.to_datetime(horario_str, format='%H:%M').time()
    except ValueError:
        pass

    # Se nada funcionar, retorna None
    return None


def parse_soudview(df_raw):
    """
    Versão final que entende a estrutura de múltiplas linhas e horários em formatos flexíveis.
    """
    dados_estruturados = []
    veiculo_atual = None
    comercial_atual = None

    for index, row in df_raw.iterrows():
        primeira_celula = str(row.iloc[0]).strip()
        if pd.isna(row.iloc[0]) or primeira_celula == 'nan':
            continue

        match_veiculo = re.search(r'Veículo\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_veiculo:
            veiculo_atual = match_veiculo.group(1).strip()
            comercial_atual = None
            continue

        match_comercial = re.search(r'Comercial\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_comercial:
            comercial_atual = match_comercial.group(1).strip()
            continue

        if eh_data(primeira_celula) and comercial_atual and veiculo_atual:
            data_obj = pd.to_datetime(primeira_celula, dayfirst=True).date()

            # Itera por TODAS as outras células da mesma linha para pegar os horários
            for horario in row.iloc[1:].dropna():
                
                # USA A NOVA FUNÇÃO FLEXÍVEL AQUI
                horario_obj = parse_horario_flexivel(horario)
                
                if horario_obj:
                    dados_estruturados.append({
                        'Veiculo_Soudview': veiculo_atual,
                        'Comercial_Soudview': comercial_atual,
                        'Data': data_obj,
                        'Horario': horario_obj
                    })
    
    if not dados_estruturados:
        return pd.DataFrame()
        
    return pd.DataFrame(dados_estruturados)

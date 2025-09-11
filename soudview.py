# Arquivo: soudview.py
import pandas as pd
import datetime
import re

def eh_data(texto):
    try:
        pd.to_datetime(texto, dayfirst=True)
        return True
    except (ValueError, TypeError):
        return False

def parse_soudview(df_raw):
    # ... (código completo da função, sem alterações da última versão)
    dados_estruturados = []
    veiculo_atual = None
    comercial_atual = None
    for index, row in df_raw.iterrows():
        primeira_celula = str(row.iloc[0]).strip()
        if pd.isna(row.iloc[0]) or primeira_celula == 'nan': continue
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
            for horario in row.iloc[1:].dropna():
                try:
                    horario_obj = pd.to_datetime(str(horario), errors='coerce').time()
                    if horario_obj:
                        dados_estruturados.append({'Veiculo_Soudview': veiculo_atual, 'Comercial_Soudview': comercial_atual, 'Data': data_obj, 'Horario': horario_obj})
                except (ValueError, TypeError): continue
    return pd.DataFrame(dados_estruturados)

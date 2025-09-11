# Exemplo mínimo do módulo Soudview
import pandas as pd
from rapidfuzz import fuzz, process

def parse_soudview(df_raw):
    # Aqui você coloca sua lógica de parsing da Soudview
    # Exemplo genérico:
    df = df_raw.copy()
    df.columns = ["veiculo", "data", "hora", "titulo"]
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    return df

def normalizar_hora(hora):
    # Converte para datetime.time, ignora segundos
    if pd.isnull(hora):
        return None
    try:
        return pd.to_datetime(hora, format="%H:%M").time()
    except:
        return None

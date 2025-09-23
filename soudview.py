import pandas as pd

def parse_soudview(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza a planilha da Soudview para ter sempre as colunas:
    veiculo_soudview | comercial_soudview | data | horario
    """
    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()
    
    # tenta achar as colunas mais prováveis
    mapping = {
        'veiculo_soudview': ['veiculo', 'emissora', 'veículo', 'station'],
        'comercial_soudview': ['comercial', 'programa', 'spot'],
        'data': ['data', 'date'],
        'horario': ['hora', 'horario', 'time']
    }
    
    final_cols = {}
    for padrao, candidatos in mapping.items():
        for c in candidatos:
            if c in df.columns:
                final_cols[padrao] = c
                break
    
    # renomeia só o que achou
    df = df.rename(columns={v: k for k, v in final_cols.items() if v in df.columns})
    
    # garante que todas existam
    for col in ['veiculo_soudview', 'comercial_soudview', 'data', 'horario']:
        if col not in df.columns:
            df[col] = None
    
    return df[['veiculo_soudview', 'comercial_soudview', 'data', 'horario']]

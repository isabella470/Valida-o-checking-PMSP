import pandas as pd
import re

def parse_soudview(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Parser flexível para planilha da Soudview.
    Retorna: veiculo_soudview | comercial_soudview | data | horario
    """

    # Remove linhas/colunas completamente vazias
    df = df_bruto.dropna(how="all").copy()
    df = df.reset_index(drop=True)

    # Normaliza cabeçalhos em string minúscula
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Tentativa de detectar colunas por regex
    colunas = {
        "veiculo_soudview": None,
        "comercial_soudview": None,
        "data": None,
        "horario": None,
    }

    for col in df.columns:
        if re.search(r"ve[ií]culo|emissora|station", col):
            colunas["veiculo_soudview"] = col
        elif re.search(r"comercial|programa|spot|anúncio|anuncio", col):
            colunas["comercial_soudview"] = col
        elif re.search(r"data", col):
            colunas["data"] = col
        elif re.search(r"hora|horário|time", col):
            colunas["horario"] = col

    # Cria dataframe só com colunas válidas
    df_out = pd.DataFrame()
    for novo, original in colunas.items():
        if original in df.columns:
            df_out[novo] = df[original]
        else:
            df_out[novo] = None  # coluna ausente → preenche vazio

    # Normaliza data
    if "data" in df_out.columns:
        df_out["data"] = pd.to_datetime(df_out["data"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Normaliza horário
    if "horario" in df_out.columns:
        df_out["horario"] = pd.to_datetime(df_out["horario"], errors="coerce").dt.strftime("%H:%M")

    return df_out

import pandas as pd

def parse_soudview(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Converte o dataframe bruto da planilha Soudview em um dataframe padronizado.
    Esperado: colunas -> veiculo_soudview, comercial_soudview, data, horario
    """

    # Tenta detectar cabeçalhos automaticamente
    df = df_bruto.copy()
    df = df.dropna(how="all")  # remove linhas totalmente vazias
    df = df.reset_index(drop=True)

    # Ajuste: supondo que as colunas da Soudview venham assim (mude se for diferente):
    # [0] Veículo | [1] Programa/Comercial | [2] Data | [3] Hora
    col_map = {
        0: "veiculo_soudview",
        1: "comercial_soudview",
        2: "data",
        3: "horario"
    }

    # Renomeia apenas as primeiras 4 colunas
    df = df.rename(columns=col_map)

    # Pega só as colunas de interesse
    colunas_finais = ["veiculo_soudview", "comercial_soudview", "data", "horario"]
    df = df[[c for c in colunas_finais if c in df.columns]]

    # Normaliza data e hora
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    if "horario" in df.columns:
        df["horario"] = pd.to_datetime(df["horario"], errors="coerce").dt.strftime("%H:%M")

    return df

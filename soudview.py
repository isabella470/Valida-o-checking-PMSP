import pandas as pd

def parse_soudview(df_raw):
    """
    Parser da planilha Soudview exportada como CSV ou Excel.

    Regras:
    - O nome do veículo aparece em uma das colunas da direita (coluna 9, se existir).
      Mantém o último valor até que mude.
    - O comercial aparece em linhas com "Comercial:".
    - Datas ficam na primeira coluna (coluna 0).
    - Horários ficam normalmente na coluna 2 (podendo haver vários horários na mesma célula).
    """

    dados_finais = []
    veiculo_atual = None
    comercial_atual = None

    for _, row in df_raw.iterrows():
        # Primeira coluna: data ou "Comercial:"
        primeira_col = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        veiculo_col = str(row.iloc[9]) if row.shape[0] > 9 and pd.notna(row.iloc[9]) else None

        # Atualiza veículo se mudar
        if veiculo_col and "Veículo" in veiculo_col:
            veiculo_atual = veiculo_col.replace("Veículo:", "").strip()

        # Atualiza comercial se mudar
        if "Comercial:" in primeira_col:
            comercial_atual = primeira_col.replace("Comercial:", "").strip()
            continue

        # Tenta ler data (primeira coluna)
        try:
            data = pd.to_datetime(primeira_col, dayfirst=True, errors="raise").date()
        except Exception:
            continue

        # Extrai horários da coluna 2 (pode haver vários)
        if row.shape[0] > 2 and pd.notna(row.iloc[2]):
            horarios_brutos = str(row.iloc[2]).split()
            for h in horarios_brutos:
                try:
                    horario = pd.to_datetime(h, errors="coerce").time()
                    if horario:
                        dados_finais.append({
                            "Veiculo_Soudview": veiculo_atual,
                            "Comercial_Soudview": comercial_atual,
                            "Data": data,
                            "Horario": horario
                        })
                except Exception:
                    continue

    return pd.DataFrame(dados_finais)

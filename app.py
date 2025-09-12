import streamlit as st
import pandas as pd
from fuzzywuzzy import process, fuzz

# -----------------------------
# Função parse_soudview
# -----------------------------
def parse_soudview(df_raw):
    """
    Parser da planilha Soudview exportada como CSV ou Excel.
    """
    dados_finais = []
    veiculo_atual = None
    comercial_atual = None

    for _, row in df_raw.iterrows():
        primeira_col = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        veiculo_col = str(row.iloc[9]) if row.shape[0] > 9 and pd.notna(row.iloc[9]) else None

        # Atualiza veículo se mudar
        if veiculo_col and "Veículo" in veiculo_col:
            veiculo_atual = veiculo_col.replace("Veículo:", "").strip()

        # Atualiza comercial se houver
        if "Comercial:" in primeira_col:
            comercial_atual = primeira_col.replace("Comercial:", "").strip()
            continue

        # Lê data
        try:
            data = pd.to_datetime(primeira_col, dayfirst=True, errors="raise").date()
        except Exception:
            continue

        # Extrai horários (coluna 2), podendo ter vários
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

# -----------------------------
# Streamlit
# -----------------------------
st.title("Soudview x Checking Merge")

# Upload dos arquivos
soudview_file = st.file_uploader("Upload CSV/Excel Soudview", type=["csv", "xlsx"])
checking_file = st.file_uploader("Upload CSV/Excel Checking", type=["csv", "xlsx"])

if soudview_file and checking_file:
    # Lê arquivos
    if soudview_file.name.endswith(".csv"):
        df_soud_raw = pd.read_csv(soudview_file, header=None)
    else:
        df_soud_raw = pd.read_excel(soudview_file, header=None)

    if checking_file.name.endswith(".csv"):
        df_checking = pd.read_csv(checking_file)
    else:
        df_checking = pd.read_excel(checking_file)

    # Parser Soudview
    df_soud = parse_soudview(df_soud_raw)

    # Padroniza tipos de data/hora
    df_soud['Data'] = pd.to_datetime(df_soud['Data']).dt.date
    df_soud['Horario'] = pd.to_datetime(df_soud['Horario'], errors='coerce').dt.time

    df_checking['DATA_NORM'] = pd.to_datetime(df_checking['DATA_NORM']).dt.date
    df_checking['HORARIO_NORM'] = pd.to_datetime(df_checking['HORARIO_NORM'], errors='coerce').dt.time

    # Fuzzy match de veículos
    veiculos_soud = df_soud['Veiculo_Soudview'].dropna().unique()
    veiculos_checking = df_checking['VEICULO'].dropna().unique()

    mapa_veiculos = {}
    mapa_scores = {}
    for v in veiculos_soud:
        match = process.extractOne(v, veiculos_checking, scorer=fuzz.token_set_ratio)
        if match and match[1] >= 80:
            mapa_veiculos[v] = match[0]
            mapa_scores[v] = match[1]
        else:
            mapa_veiculos[v] = "NÃO MAPEADO"
            mapa_scores[v] = 0

    df_soud['Veiculo_Mapeado'] = df_soud['Veiculo_Soudview'].map(mapa_veiculos)
    df_soud['Score_Mapeamento'] = df_soud['Veiculo_Soudview'].map(mapa_scores)

    st.subheader("Soudview Processado")
    st.dataframe(df_soud)

    # Merge seguro
    df_final = pd.merge(
        df_soud,
        df_checking,
        left_on=['Veiculo_Mapeado', 'Data', 'Horario'],
        right_on=['VEICULO', 'DATA_NORM', 'HORARIO_NORM'],
        how='left'
    )

    st.subheader("Merge Final com Checking")
    st.dataframe(df_final)

    # Download do resultado
    csv = df_final.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar CSV Final", csv, "merge_final.csv", "text/csv")

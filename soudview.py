import pandas as pd
import datetime
import re

def eh_data(texto):
    """Verifica se um texto pode ser interpretado como uma data."""
    if not isinstance(texto, str) or len(texto) < 8:
        return False
    try:
        pd.to_datetime(texto, dayfirst=True)
        return True
    except (ValueError, TypeError):
        return False

def parse_soudview(df_raw):
    """
    Versão final customizada que lê o veículo da última coluna e os dados da primeira.
    Feita sob medida para o arquivo Soundview_PRESTACAO-DE-SERVICOS.
    """
    dados_estruturados = []
    veiculo_atual = None
    comercial_atual = None

    # Tenta extrair o veículo da primeira linha, última coluna (célula mesclada)
    # O iloc[0, -1] pega a primeira linha, última coluna.
    primeira_linha = df_raw.iloc[0]
    ultima_coluna_da_primeira_linha = primeira_linha.dropna().iloc[-1]
    
    if isinstance(ultima_coluna_da_primeira_linha, str):
        veiculo_atual = ultima_coluna_da_primeira_linha.strip()

    # Se não encontrou um veículo no cabeçalho, o arquivo é inválido
    if not veiculo_atual:
        st.error("Não foi possível identificar o nome do veículo no cabeçalho do arquivo Soudview.")
        return pd.DataFrame()

    # Agora, itera pelas linhas para encontrar os comerciais e os dados
    for index, row in df_raw.iterrows():
        if pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        
        if not primeira_celula:
            continue

        # Procura por "Comercial:" para definir o comercial atual
        match_comercial = re.search(r'Comercial\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_comercial:
            comercial_atual = match_comercial.group(1).strip()
            continue

        # Se a linha começa com uma data e já temos um comercial
        if eh_data(primeira_celula) and comercial_atual:
            data_obj = pd.to_datetime(primeira_celula, dayfirst=True).date()
            for horario in row.iloc[1:].dropna():
                try:
                    horario_obj = pd.to_datetime(str(horario), errors='coerce').time()
                    if horario_obj:
                        dados_estruturados.append({
                            'Veiculo_Soudview': veiculo_atual,
                            'Comercial_Soudview': comercial_atual,
                            'Data': data_obj,
                            'Horario': horario_obj
                        })
                except (ValueError, TypeError):
                    continue
    
    return pd.DataFrame(dados_estruturados)

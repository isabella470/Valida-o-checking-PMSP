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
    Versão com lógica de identificação de veículo mais precisa, para não confundir com outros cabeçalhos.
    """
    dados_estruturados = []
    veiculo_atual = None
    comercial_atual = None
    
    # Lista de palavras-chave que identificam linhas a serem IGNORADAS
    palavras_chave_ignorar = ['soundview', 'campanha:', 'cliente:', 'comercial:', 'agência:', 'período:']

    for index, row in df_raw.iterrows():
        # Pula a linha se a primeira célula for vazia
        if pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        
        # Pula a linha se, depois de limpa, estiver vazia
        if not primeira_celula:
            continue

        # Verifica se é uma linha de dados (começa com data)
        if eh_data(primeira_celula) and comercial_atual and veiculo_atual:
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
            continue

        # Procura por "Comercial:" para definir o comercial atual
        match_comercial = re.search(r'Comercial\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_comercial:
            comercial_atual = match_comercial.group(1).strip()
            continue

        # Se não for uma linha de data nem um comercial, verifica se é um cabeçalho a ser ignorado
        eh_para_ignorar = any(keyword in primeira_celula.lower() for keyword in palavras_chave_ignorar)
        
        # Se a linha sobreviveu a todos os filtros (não é data, não é comercial, não é para ignorar),
        # então ela DEVE ser o nome do veículo.
        if not eh_para_ignorar:
            veiculo_atual = primeira_celula
            comercial_atual = None # Reseta o comercial, pois é um novo bloco de veículo

    return pd.DataFrame(dados_estruturados)

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
    Analisador Universal: Lida com múltiplos formatos de arquivo Soudview.
    1. Tenta pegar o veículo do cabeçalho (canto direito).
    2. Procura por veículos no corpo do relatório e os prioriza.
    """
    dados_estruturados = []
    veiculo_do_cabecalho = None
    veiculo_do_corpo = None
    comercial_atual = None
    
    # Estratégia 1: Tenta extrair um veículo global do cabeçalho (Formato A)
    try:
        primeira_linha = df_raw.iloc[0]
        ultima_coluna_valida = primeira_linha.dropna()
        if not ultima_coluna_valida.empty:
            valor_canto_direito = ultima_coluna_valida.iloc[-1]
            if isinstance(valor_canto_direito, str) and len(valor_canto_direito) > 3:
                veiculo_do_cabecalho = valor_canto_direito.strip()
    except (IndexError, AttributeError):
        pass # Ignora se o arquivo for malformado

    # Estratégia 2: Itera pelas linhas para encontrar dados e veículos no corpo (Formato B)
    cabecalhos_ignorados = ['soundview', 'campanha:', 'cliente:', 'agência:', 'período:']
    
    for index, row in df_raw.iterrows():
        if pd.isna(row.iloc[0]): continue
        primeira_celula = str(row.iloc[0]).strip()
        if not primeira_celula: continue

        # Identifica a linha "Comercial:"
        match_comercial = re.search(r'Comercial\s*:\s*(.*)', primeira_celula, re.IGNORECASE)
        if match_comercial:
            comercial_atual = match_comercial.group(1).strip()
            continue

        # Prioridade máxima: Se a linha é de dados, processa-a
        veiculo_ativo = veiculo_do_corpo if veiculo_do_corpo else veiculo_do_cabecalho
        if eh_data(primeira_celula) and comercial_atual and veiculo_ativo:
            data_obj = pd.to_datetime(primeira_celula, dayfirst=True).date()
            for horario in row.iloc[1:].dropna():
                try:
                    horario_obj = pd.to_datetime(str(horario), errors='coerce').time()
                    if horario_obj:
                        dados_estruturados.append({
                            'Veiculo_Soudview': veiculo_ativo,
                            'Comercial_Soudview': comercial_atual,
                            'Data': data_obj,
                            'Horario': horario_obj
                        })
                except (ValueError, TypeError): continue
            continue

        # Se não for uma linha de dados nem um comercial, verifica se é um veículo
        eh_para_ignorar = any(keyword in primeira_celula.lower() for keyword in cabecalhos_ignorados)
        if not eh_para_ignorar:
            # Se a linha não é para ser ignorada, assume-se que é um nome de veículo no corpo
            veiculo_do_corpo = primeira_celula
            comercial_atual = None # Reseta o comercial para o novo bloco de veículo

    return pd.DataFrame(dados_estruturados)

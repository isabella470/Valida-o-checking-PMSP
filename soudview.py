import pandas as pd
import datetime

def normalizar_hora(hora_str):
    """Normaliza uma string de hora para o formato time."""
    try:
        # Tenta converter diretamente se for um objeto time
        if isinstance(hora_str, datetime.time):
            return hora_str
        # Tenta converter de string
        return pd.to_datetime(hora_str, format='%H:%M:%S', errors='coerce').time()
    except (ValueError, TypeError):
        return None

def parse_soudview(df_raw):
    """
    Lê um DataFrame bruto da Soudview e o transforma em uma tabela estruturada.
    Esta função cria uma nova estrutura de dados do zero para evitar erros de 'length mismatch'.
    """
    dados_estruturados = []
    veiculo_atual = None

    # Itera pelas linhas do DataFrame bruto lido da planilha
    for index, row in df_raw.iterrows():
        # A primeira coluna geralmente contém os dados que importam
        valor_celula = str(row.iloc[0]).strip()

        if pd.isna(row.iloc[0]) or valor_celula == 'nan':
            continue

        # Se a linha contém "Comercial:", é um bloco de campanha
        if 'Comercial:' in valor_celula:
            nome_comercial = valor_celula.split('Comercial:')[1].strip()
            
            # A data está na linha seguinte
            if index + 1 < len(df_raw):
                data_str = str(df_raw.iloc[index + 1, 0])
                try:
                    data_obj = pd.to_datetime(data_str, dayfirst=True).date()
                except (ValueError, TypeError):
                    continue  # Pula este bloco se a data for inválida
            else:
                continue

            # Os horários estão duas linhas abaixo e podem ocupar várias colunas
            if index + 2 < len(df_raw):
                horarios_row = df_raw.iloc[index + 2]
                
                for horario in horarios_row.dropna():
                    horario_limpo = normalizar_hora(str(horario))
                    if horario_limpo and veiculo_atual:
                        dados_estruturados.append({
                            'veiculo': veiculo_atual,
                            'comercial': nome_comercial,
                            'data': pd.to_datetime(data_obj), # Converte para timestamp para consistência
                            'hora': horario_limpo
                        })
        # Se não for um comercial, pode ser o nome de um veículo
        # Uma heurística simples é verificar se a célula não contém ":" ou "/" (como em datas)
        elif ':' not in valor_celula and '/' not in valor_celula and len(valor_celula) > 3:
             if index == 0 or 'Comercial:' not in str(df_raw.iloc[index - 1, 0]):
                veiculo_atual = valor_celula.strip()

    # Cria um DataFrame novinho em folha a partir da lista de dados limpos
    if not dados_estruturados:
        return pd.DataFrame(columns=['veiculo', 'comercial', 'data', 'hora'])

    return pd.DataFrame(dados_estruturados)

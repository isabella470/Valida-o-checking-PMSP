import pandas as pd
import datetime

def parse_soudview(df_raw):
    """
    Lê um DataFrame bruto da Soudview e o transforma em uma tabela estruturada,
    seguindo a regra de data e horários na mesma linha.
    """
    dados_estruturados = []
    veiculo_atual = None

    for index, row in df_raw.iterrows():
        # Pega a primeira célula da linha, que geralmente contém a informação
        valor_celula = str(row.iloc[0]).strip()

        if pd.isna(row.iloc[0]) or valor_celula == 'nan':
            continue

        # 1. Identificar o veículo
        if 'Veículo:' in valor_celula:
            veiculo_atual = valor_celula.split('Veículo:')[1].strip()
            continue

        # 2. Identificar o comercial
        if 'Comercial:' in valor_celula:
            nome_comercial = valor_celula.split('Comercial:')[1].strip()

            # 3. A próxima linha contém DATA e HORÁRIOS
            if index + 1 < len(df_raw):
                linha_de_dados = df_raw.iloc[index + 1]
                
                # O primeiro item é a data
                try:
                    data_obj = pd.to_datetime(linha_de_dados.iloc[0], dayfirst=True)
                except (ValueError, TypeError):
                    continue # Se a data for inválida, pula para o próximo comercial

                # Os itens seguintes na mesma linha são os horários
                for horario in linha_de_dados.iloc[1:].dropna():
                    try:
                        # Converte para objeto de tempo para padronização
                        horario_obj = pd.to_datetime(str(horario), format='%H:%M:%S', errors='coerce').time()
                        if horario_obj and veiculo_atual:
                            dados_estruturados.append({
                                'Veiculo_Soudview': veiculo_atual,
                                'Comercial_Soudview': nome_comercial,
                                'Data': data_obj.date(), # Armazena apenas a data
                                'Horario': horario_obj    # Armazena o objeto de tempo
                            })
                    except (ValueError, TypeError):
                        continue # Ignora horários em formato inválido
    
    if not dados_estruturados:
        return pd.DataFrame(columns=['Veiculo_Soudview', 'Comercial_Soudview', 'Data', 'Horario'])
        
    return pd.DataFrame(dados_estruturados)

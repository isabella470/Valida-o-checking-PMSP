# soudview.py
import pandas as pd
import re

def parse_soudview(df_bruto: pd.DataFrame):
    """
    Parser inteligente com log de diagnóstico para entender o processo de extração.
    Retorna um DataFrame de resultados e uma lista de mensagens de log.
    """
    log = []
    log.append("--- Iniciando o parser da Soudview ---")
    
    # Remove linhas e colunas completamente vazias para limpar o input
    df = df_bruto.dropna(how="all").dropna(how="all", axis=1).reset_index(drop=True)
    log.append(f"DataFrame limpo. Formato inicial: {df.shape[0]} linhas, {df.shape[1]} colunas.")

    veiculo_atual = "Veículo não identificado"
    comercial_atual = "Comercial não identificado"
    resultados = []

    for i, row in df.iterrows():
        # Se a linha for vazia ou a primeira célula for nula, pula para a próxima
        if row.empty or pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        log.append(f"Linha {i}: Analisando célula 'A' -> '{primeira_celula}'")

        # Tenta detectar se a linha é um cabeçalho de veículo
        if any(re.search(r"\b(FM|AM|TV|RÁDIO|RADIO|REDE)\b", str(cell).upper()) for cell in row if pd.notna(cell)):
            if len(re.findall(r'[a-zA-Z]', primeira_celula)) > 3: # Garante que não é só um "TV" perdido
                veiculo_atual = primeira_celula
                log.append(f"  -> DETECTADO como VEÍCULO. Novo contexto: '{veiculo_atual}'")
                continue

        # Tenta detectar se a linha é um cabeçalho de comercial
        if any(re.search(r"(SPOT|COMERCIAL|ANÚNCIO|ANUNCIO)", str(cell), re.I) for cell in row if pd.notna(cell)):
            comercial_atual = primeira_celula
            log.append(f"  -> DETECTADO como COMERCIAL. Novo contexto: '{comercial_atual}'")
            continue

        # Tenta detectar se a primeira célula da linha é uma data
        if re.match(r"^\d{1,2}/\d{1,2}(/\d{2,4})?$", primeira_celula):
            log.append(f"  -> DETECTADO como linha de DADOS. Processando horários...")
            data_str = primeira_celula
            horarios_encontrados = 0
            
            # Converte a data uma vez
            data_dt = pd.to_datetime(data_str, dayfirst=True, errors='coerce')
            if pd.isna(data_dt):
                log.append(f"    -> AVISO: A data '{data_str}' é inválida. Pulando linha.")
                continue

            # Itera por todas as outras células da linha para encontrar os horários
            for horario in row[1:]:
                if pd.isna(horario) or str(horario).strip() == '':
                    continue
                
                hora_obj = None # Reseta para cada célula
                try:
                    if isinstance(horario, (float, int)): # Formato de hora do Excel (ex: 0.41667)
                        total_seconds = int(horario * 24 * 60 * 60)
                        minutes, seconds = divmod(total_seconds, 60)
                        hours, minutes = divmod(minutes, 60)
                        # Garante que não ultrapasse 24h
                        if 0 <= hours < 24:
                            hora_obj = pd.to_datetime(f"{hours}:{minutes}:{seconds}", format='%H:%M:%S').time()
                    else: # Formato de texto ou datetime
                        # Tenta converter para datetime e pegar apenas a hora
                        horario_parseado = pd.to_datetime(str(horario), errors='coerce')
                        if pd.notna(horario_parseado):
                            hora_obj = horario_parseado.time()
                    
                    if hora_obj:
                        resultados.append({
                            "veiculo_soudview": veiculo_atual,
                            "comercial_soudview": comercial_atual,
                            "data": data_dt.date(), # Salva como objeto date
                            "horario": hora_obj     # Salva como objeto time
                        })
                        horarios_encontrados += 1
                except (ValueError, TypeError, AttributeError):
                    # Ignora células que não podem ser convertidas para hora
                    continue
            log.append(f"    -> {horarios_encontrados} horários válidos encontrados e adicionados.")
            continue
        
        log.append("  -> Linha não correspondeu a nenhum padrão (veículo, comercial ou data). Ignorando.")

    log.append(f"\n--- Fim do parser. Total de {len(resultados)} registros encontrados. ---")
    return pd.DataFrame(resultados), log

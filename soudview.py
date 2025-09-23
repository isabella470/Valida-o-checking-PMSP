# Conteúdo para o arquivo: soudview.py (Versão com Log Detalhado)

import pandas as pd
import re

def parse_soudview(df_bruto: pd.DataFrame):
    """
    Parser inteligente com log de diagnóstico para entender o processo de extração.
    Retorna um DataFrame de resultados e uma lista de mensagens de log.
    """
    log = []
    log.append("--- Iniciando o parser da Soudview ---\n")
    
    # Remove linhas e colunas completamente vazias para limpar o input
    df = df_bruto.dropna(how="all").dropna(how="all", axis=1).reset_index(drop=True)
    log.append(f"DataFrame limpo. Formato inicial: {df.shape[0]} linhas, {df.shape[1]} colunas.\n")

    veiculo_atual = "Veículo não identificado"
    comercial_atual = "Comercial não identificado"
    resultados = []

    for i, row in df.iterrows():
        # Pega a primeira célula da linha, que geralmente contém a informação principal
        # Se a linha for vazia ou a primeira célula for nula, pula para a próxima
        if row.empty or pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        log.append(f"Linha {i}: Analisando célula 'A' -> '{primeira_celula}'\n")

        # Tenta detectar se a linha é um cabeçalho de veículo
        if any(re.search(r"\b(FM|AM|TV|RÁDIO|RADIO|REDE)\b", str(cell).upper()) for cell in row):
            if len(re.findall(r'[a-zA-Z]', primeira_celula)) > 3: # Garante que não é só um "TV" perdido
                veiculo_atual = primeira_celula
                log.append(f"  -> DETECTADO como VEÍCULO. Novo contexto de veículo: '{veiculo_atual}'\n")
                continue

        # Tenta detectar se a linha é um cabeçalho de comercial
        if any(re.search(r"(SPOT|COMERCIAL|ANÚNCIO|ANUNCIO)", str(cell), re.I) for cell in row):
            comercial_atual = primeira_celula
            log.append(f"  -> DETECTADO como COMERCIAL. Novo contexto de comercial: '{comercial_atual}'\n")
            continue

        # Tenta detectar se a primeira célula da linha é uma data
        if re.match(r"^\d{1,2}/\d{1,2}(/\d{2,4})?$", primeira_celula):
            log.append(f"  -> DETECTADO como linha de DADOS. Processando horários...\n")
            data_str = primeira_celula
            horarios_encontrados = 0
            # Itera por todas as outras células da linha para encontrar os horários
            for horario in row[1:]:
                if pd.notna(horario) and str(horario).strip() != '':
                    try:
                        data_dt = pd.to_datetime(data_str, dayfirst=True, errors='coerce')
                        if isinstance(horario, (float, int)):
                            total_seconds = int(horario * 24 * 60 * 60)
                            minutes, seconds = divmod(total_seconds, 60)
                            hours, minutes = divmod(minutes, 60)
                            hora_obj = pd.to_datetime(f"{hours}:{minutes}:{seconds}", format='%H:%M:%S').time()
                        else:
                            hora_obj = pd.to_datetime(str(horario), errors='coerce').time()

                        if pd.notna(data_dt) and pd.notna(hora_obj):
                            resultados.append({
                                "veiculo_soudview": veiculo_atual,
                                "comercial_soudview": comercial_atual,
                                "data": data_dt.strftime("%Y-%m-%d"),
                                "horario": hora_obj.strftime("%H:%M:%S")
                            })
                            horarios_encontrados += 1
                    except (ValueError, TypeError):
                        continue
            log.append(f"    -> {horarios_encontrados} horários válidos encontrados e adicionados.\n")
            continue # Pula para a próxima linha após processar os horários
        
        # Se a linha não se encaixou em nenhuma regra, registra isso
        log.append("  -> Linha não correspondeu a nenhum padrão (veículo, comercial ou data). Ignorando.\n")

    log.append(f"\n--- Fim do parser. Total de {len(resultados)} registros encontrados. ---\n")
    return pd.DataFrame(resultados), log

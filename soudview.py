import pandas as pd
import re
from datetime import time

def parse_soudview(df_bruto: pd.DataFrame):
    """
    Parser da Soudview com lógica de detecção de cabeçalho aprimorada.
    Esta versão prioriza a detecção de linhas de dados e usa regras de cabeçalho mais flexíveis.
    Retorna um DataFrame de resultados e uma lista de mensagens de log.
    """
    log = []
    log.append("--- Iniciando o parser da Soudview (v3 - Lógica Corrigida) ---")
    
    # Limpeza inicial do DataFrame, removendo linhas e colunas completamente vazias
    df = df_bruto.dropna(how="all").dropna(how="all", axis=1).reset_index(drop=True)
    log.append(f"DataFrame limpo. Formato inicial: {df.shape[0]} linhas, {df.shape[1]} colunas.")

    veiculo_atual = "Veículo não identificado"
    comercial_atual = "Comercial não identificado"
    resultados = []

    for i, row in df.iterrows():
        # Pula a linha se ela estiver vazia ou se a primeira célula for nula
        if row.empty or pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        log.append(f"Linha {i}: Analisando célula 'A' -> '{primeira_celula}'")

        # 1. DETECÇÃO DE DADOS (MAIS IMPORTANTE)
        # Procura por múltiplas células que parecem ser horários, um forte indicador de linha de dados.
        horarios_encontrados_texto = []
        # Itera a partir da segunda célula, pois a primeira é geralmente a data
        for cell in row[1:]:
            if pd.notna(cell):
                cell_str = str(cell).strip()
                # Usa regex para encontrar padrões de horário (ex: 12:34:56)
                if re.match(r'^\d{1,2}:\d{2}:\d{2}', cell_str):
                    horarios_encontrados_texto.append(cell_str)

        # Se horários foram encontrados, processa a linha como uma linha de dados
        if len(horarios_encontrados_texto) > 0:
            log.append(f"  -> DETECTADO como linha de DADOS (encontrou {len(horarios_encontrados_texto)} horário(s) na linha).")
            
            data_str = primeira_celula
            # Tenta converter a primeira célula para data
            data_dt = pd.to_datetime(data_str, dayfirst=True, errors='coerce')

            # Se a conversão da data falhar, registra um aviso e pula a linha
            if pd.isna(data_dt):
                log.append(f"    -> AVISO: A data na primeira célula ('{data_str}') é inválida. Pulando linha de dados.")
                continue
            
            horarios_processados = 0
            for horario_str in horarios_encontrados_texto:
                try:
                    # Converte a string de horário para um objeto time
                    hora_obj = pd.to_datetime(horario_str, errors='coerce').time()
                    if hora_obj:
                        # Adiciona o registro válido à lista de resultados
                        resultados.append({
                            "veiculo_soudview": veiculo_atual,
                            "comercial_soudview": comercial_atual,
                            "data": data_dt.date(),
                            "horario": hora_obj
                        })
                        horarios_processados += 1
                except (ValueError, TypeError, AttributeError):
                    # Ignora horários que não puderem ser convertidos
                    continue
            
            log.append(f"    -> {horarios_processados} horários válidos foram processados e adicionados.")
            continue # Pula para a próxima linha, pois esta já foi processada

        # 2. DETECÇÃO DE CABEÇALHO (REGRAS MAIS FLEXÍVEIS)
        # Só executa se a linha não for de dados.

        # --- LÓGICA CORRIGIDA PARA DETECÇÃO DE VEÍCULO ---
        # Verifica se alguma célula na linha contém palavras-chave de veículo
        is_veiculo_candidate = any(re.search(r"\b(FM|AM|TV|RÁDIO|RADIO|REDE)\b", str(cell).upper()) for cell in row if pd.notna(cell))
        if is_veiculo_candidate:
            # CORREÇÃO: Junta todas as células de texto da linha para formar o nome do veículo.
            # Isso é mais robusto caso o nome não esteja na primeira coluna.
            header_parts = [str(cell).strip() for cell in row if pd.notna(cell)]
            plausible_header = " ".join(header_parts)
            
            # Evita que cabeçalhos de relatório (ex: "PI DE...") sejam capturados como veículo
            if not re.match(r'^(PI|CS)\s+DE', plausible_header.upper()):
                veiculo_atual = plausible_header
                log.append(f"  -> DETECTADO como VEÍCULO. Novo contexto de veículo: '{veiculo_atual}'")
                continue

        # --- LÓGICA CORRIGIDA PARA DETECÇÃO DE COMERCIAL ---
        # Verifica se alguma célula na linha contém palavras-chave de comercial
        is_comercial_candidate = any(re.search(r"(SPOT|COMERCIAL|ANÚNCIO|ANUNCIO)", str(cell), re.I) for cell in row if pd.notna(cell))
        if is_comercial_candidate:
            # CORREÇÃO: Junta todas as células de texto, similar à lógica do veículo.
            header_parts = [str(cell).strip() for cell in row if pd.notna(cell)]
            plausible_header = " ".join(header_parts)
            
            # Evita que cabeçalhos de relatório sejam capturados como comercial
            if not re.match(r'^(PI|CS)\s+DE', plausible_header.upper()):
                comercial_atual = plausible_header
                log.append(f"  -> DETECTADO como COMERCIAL. Novo contexto de comercial: '{comercial_atual}'")
                continue
        
        log.append("  -> Linha não correspondeu a nenhum padrão (dados, veículo ou comercial). Ignorando.")

    log.append(f"\n--- Fim do parser. Total de {len(resultados)} registros encontrados. ---")
    
    # Se houver resultados, cria um DataFrame e exibe um resumo no log
    if len(resultados) > 0:
        df_result = pd.DataFrame(resultados)
        veiculos_unicos = df_result['veiculo_soudview'].unique()
        comerciais_unicos = df_result['comercial_soudview'].unique()
        
        log.append(f"\n📊 RESUMO:")
        log.append(f"Veículos únicos encontrados ({len(veiculos_unicos)}):")
        for v in veiculos_unicos:
            log.append(f"  - {v}")
        
        log.append(f"\nComerciais únicos encontrados ({len(comerciais_unicos)}):")
        for c in comerciais_unicos:
            log.append(f"  - {c}")
    else:
        df_result = pd.DataFrame(resultados)

    return df_result, log

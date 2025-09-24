# soudview.py (VERSÃO CORRIGIDA E APRIMORADA)
import pandas as pd
import re
from datetime import time

def parse_soudview(df_bruto: pd.DataFrame):
    """
    Parser inteligente com log de diagnóstico para entender o processo de extração.
    Esta versão prioriza a detecção de linhas de dados e possui regras de cabeçalho mais rígidas.
    Retorna um DataFrame de resultados e uma lista de mensagens de log.
    """
    log = []
    log.append("--- Iniciando o parser da Soudview (v2 - Lógica Aprimorada) ---")
    
    df = df_bruto.dropna(how="all").dropna(how="all", axis=1).reset_index(drop=True)
    log.append(f"DataFrame limpo. Formato inicial: {df.shape[0]} linhas, {df.shape[1]} colunas.")

    veiculo_atual = "Veículo não identificado"
    comercial_atual = "Comercial não identificado"
    resultados = []

    for i, row in df.iterrows():
        if row.empty or pd.isna(row.iloc[0]):
            continue
            
        primeira_celula = str(row.iloc[0]).strip()
        log.append(f"Linha {i}: Analisando célula 'A' -> '{primeira_celula}'")

        # 1. DETECÇÃO DE DADOS (MAIS IMPORTANTE):
        # Procura por múltiplas células que parecem ser horários. É um indicador forte de uma linha de dados.
        horarios_encontrados_texto = []
        for cell in row[1:]: # Ignora a primeira célula que deve ser a data
            if pd.notna(cell):
                cell_str = str(cell).strip()
                if re.match(r'^\d{1,2}:\d{2}:\d{2}', cell_str):
                    horarios_encontrados_texto.append(cell_str)

        if len(horarios_encontrados_texto) > 0:
            log.append(f"  -> DETECTADO como linha de DADOS (encontrou {len(horarios_encontrados_texto)} horário(s) na linha).")
            
            data_str = primeira_celula
            data_dt = pd.to_datetime(data_str, dayfirst=True, errors='coerce')

            if pd.isna(data_dt):
                log.append(f"    -> AVISO: A data na primeira célula ('{data_str}') é inválida. Pulando linha de dados.")
                continue
            
            horarios_processados = 0
            for horario_str in horarios_encontrados_texto:
                try:
                    hora_obj = pd.to_datetime(horario_str, errors='coerce').time()
                    if hora_obj:
                        resultados.append({
                            "veiculo_soudview": veiculo_atual,
                            "comercial_soudview": comercial_atual,
                            "data": data_dt.date(),
                            "horario": hora_obj
                        })
                        horarios_processados += 1
                except (ValueError, TypeError, AttributeError):
                    continue # Ignora se a conversão do horário falhar
            
            log.append(f"    -> {horarios_processados} horários válidos foram processados e adicionados.")
            continue # Pula para a próxima linha

        # 2. DETECÇÃO DE CABEÇALHO (REGRAS MAIS RÍGIDAS)
        # Só executa se não for uma linha de dados.
        is_veiculo_candidate = any(re.search(r"\b(FM|AM|TV|RÁDIO|RADIO|REDE)\b", str(cell).upper()) for cell in row if pd.notna(cell))
        if is_veiculo_candidate:
            # Regra adicional: não deve parecer um cabeçalho de relatório como 'PI DE...'
            if len(re.findall(r'[a-zA-Z]', primeira_celula)) > 3 and not re.match(r'^(PI|CS)\s+DE', primeira_celula.upper()):
                veiculo_atual = primeira_celula
                log.append(f"  -> DETECTADO como VEÍCULO. Novo contexto de veículo: '{veiculo_atual}'")
                continue

        is_comercial_candidate = any(re.search(r"(SPOT|COMERCIAL|ANÚNCIO|ANUNCIO)", str(cell), re.I) for cell in row if pd.notna(cell))
        if is_comercial_candidate:
            # Regra adicional: não deve parecer um cabeçalho de relatório
            if not re.match(r'^(PI|CS)\s+DE', primeira_celula.upper()):
                comercial_atual = primeira_celula
                log.append(f"  -> DETECTADO como COMERCIAL. Novo contexto de comercial: '{comercial_atual}'")
                continue
        
        log.append("  -> Linha não correspondeu a nenhum padrão (dados, veículo ou comercial). Ignorando.")

    log.append(f"\n--- Fim do parser. Total de {len(resultados)} registros encontrados. ---")
    return pd.DataFrame(resultados), log

import pandas as pd
import re
from datetime import time

def parse_soudview(df_bruto: pd.DataFrame):
    """
    Parser robusto para extrair dados da planilha Soudview.
    Prioriza detecção correta de Veículo (com palavras-chave de rádio/TV)
    vs Campanha/Comercial (texto genérico).
    Retorna: (DataFrame de resultados, lista de logs)
    """
    log = []
    log.append("=== INICIANDO PARSER SOUDVIEW v4 ===")
    log.append(f"Formato inicial: {df_bruto.shape[0]} linhas × {df_bruto.shape[1]} colunas\n")
    
    # Limpa o DataFrame
    df = df_bruto.dropna(how="all").dropna(how="all", axis=1).reset_index(drop=True)
    log.append(f"Após limpeza: {df.shape[0]} linhas × {df.shape[1]} colunas")
    
    # Mostra primeiras linhas para diagnóstico
    log.append("\n--- PRIMEIRAS 10 LINHAS (para diagnóstico) ---")
    for i in range(min(10, len(df))):
        if i < len(df) and len(df.iloc[i]) > 0:
            primeira_celula = str(df.iloc[i, 0]) if not pd.isna(df.iloc[i, 0]) else "VAZIO"
            log.append(f"Linha {i}: '{primeira_celula[:80]}'")
    log.append("--- FIM DO PREVIEW ---\n")

    # Contexto atual
    veiculo_atual = "Veículo não identificado"
    comercial_atual = "Comercial não identificado"
    resultados = []

    # Padrões para detecção
    PATTERN_HORARIO = re.compile(r'^\d{1,2}:\d{2}(?::\d{2})?$')
    PATTERN_DATA = re.compile(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$')
    
    # Palavras-chave FORTES para identificar veículos (rádios/TVs)
    KEYWORDS_VEICULO_FORTE = [
        'RÁDIO', 'RADIO', 'FM', 'AM', 
        'REDE', 'TV', 'EMISSORA', 'BANDEIRANTES',
        'GLOBO', 'RECORD', 'SBT', 'BAND', 'JOVEM PAN'
    ]
    
    # Palavras que indicam que NÃO é um veículo
    KEYWORDS_NAO_VEICULO = [
        'CAMPANHA', 'SPOT', 'COMERCIAL', 'ANÚNCIO', 'ANUNCIO',
        'PRESTAÇÃO', 'PRESTACAO', 'SERVIÇOS', 'SERVICOS',
        'PRODUTO', 'MARCA'
    ]

    for i, row in df.iterrows():
        if row.empty or pd.isna(row.iloc[0]):
            continue
        
        primeira_celula = str(row.iloc[0]).strip()
        primeira_celula_upper = primeira_celula.upper()
        
        # Ignora linhas de cabeçalho de relatório
        if re.match(r'^(PI|CS)\s+DE\s+', primeira_celula_upper):
            log.append(f"Linha {i}: Ignorando cabeçalho de relatório")
            continue
        
        # PRIORIDADE 1: DETECTAR LINHAS DE DADOS
        # Procura por horários na linha (exceto primeira coluna que deve ser data)
        horarios_na_linha = []
        for idx, cell in enumerate(row[1:], start=1):
            if pd.notna(cell):
                cell_str = str(cell).strip()
                if PATTERN_HORARIO.match(cell_str):
                    horarios_na_linha.append((idx, cell_str))
        
        # Se encontrou horários, é uma linha de dados
        if len(horarios_na_linha) > 0:
            # Valida se primeira célula é uma data
            if not PATTERN_DATA.match(primeira_celula):
                log.append(f"Linha {i}: ⚠️ Horários encontrados mas primeira célula não parece data: '{primeira_celula}'")
                continue
            
            data_dt = pd.to_datetime(primeira_celula, dayfirst=True, errors='coerce')
            if pd.isna(data_dt):
                log.append(f"Linha {i}: ❌ Data inválida: '{primeira_celula}'")
                continue
            
            log.append(f"Linha {i}: ✅ DADOS - Data: {primeira_celula} | {len(horarios_na_linha)} horário(s)")
            
            # Processa cada horário
            for col_idx, horario_str in horarios_na_linha:
                try:
                    # Normaliza horário (adiciona segundos se necessário)
                    if horario_str.count(':') == 1:
                        horario_str += ':00'
                    
                    hora_obj = pd.to_datetime(horario_str, format='%H:%M:%S', errors='coerce').time()
                    
                    if hora_obj and hora_obj != time(0, 0):
                        resultados.append({
                            "veiculo_soudview": veiculo_atual,
                            "comercial_soudview": comercial_atual,
                            "data": data_dt.date(),
                            "horario": hora_obj
                        })
                        log.append(f"    → Adicionado: V:[{veiculo_atual[:30]}] C:[{comercial_atual[:30]}] {horario_str}")
                    else:
                        log.append(f"    → ⚠️ Horário inválido ignorado: {horario_str}")
                        
                except Exception as e:
                    log.append(f"    → ❌ Erro ao processar horário '{horario_str}': {e}")
            
            continue  # Próxima linha
        
        # PRIORIDADE 2: DETECTAR VEÍCULO (com regras estritas)
        # Deve conter palavras-chave FORTES de veículo E NÃO conter palavras de campanha
        tem_palavra_veiculo = any(keyword in primeira_celula_upper for keyword in KEYWORDS_VEICULO_FORTE)
        tem_palavra_nao_veiculo = any(keyword in primeira_celula_upper for keyword in KEYWORDS_NAO_VEICULO)
        
        if tem_palavra_veiculo and not tem_palavra_nao_veiculo:
            # Validação extra: deve ter mais de 5 caracteres
            if len(primeira_celula) > 5:
                veiculo_atual = primeira_celula
                log.append(f"Linha {i}: 📻 VEÍCULO: '{veiculo_atual}'")
                continue
        
        # PRIORIDADE 3: DETECTAR COMERCIAL/CAMPANHA
        # Se não é veículo e não é data/horário, provavelmente é comercial
        if not PATTERN_DATA.match(primeira_celula) and not PATTERN_HORARIO.match(primeira_celula):
            # Se tem palavras de campanha OU se é um texto longo sem palavras de veículo
            if tem_palavra_nao_veiculo or (len(primeira_celula) > 10 and not tem_palavra_veiculo):
                comercial_atual = primeira_celula
                log.append(f"Linha {i}: 📢 COMERCIAL/CAMPANHA: '{comercial_atual}'")
                continue
        
        # Se chegou aqui, linha não foi identificada
        if len(primeira_celula) > 50:
            log.append(f"Linha {i}: ⊘ Não identificada - '{primeira_celula[:50]}...'")
        else:
            log.append(f"Linha {i}: ⊘ Não identificada - '{primeira_celula}'")

    log.append(f"\n=== FIM DO PARSER ===")
    log.append(f"✅ Total de registros extraídos: {len(resultados)}")
    
    if len(resultados) == 0:
        log.append("\n⚠️ ATENÇÃO: Nenhum registro foi extraído!")
        log.append("Possíveis causas:")
        log.append("  - Formato da planilha não corresponde ao esperado")
        log.append("  - Datas não estão no formato reconhecido (DD/MM/YYYY ou DD-MM-YYYY)")
        log.append("  - Horários não estão no formato HH:MM ou HH:MM:SS")
        log.append("  - Faltam linhas de cabeçalho com palavras-chave de rádio/TV")
    else:
        # Mostra resumo dos veículos e comerciais encontrados
        veiculos_unicos = pd.DataFrame(resultados)['veiculo_soudview'].unique()
        comerciais_unicos = pd.DataFrame(resultados)['comercial_soudview'].unique()
        
        log.append(f"\n📊 RESUMO:")
        log.append(f"Veículos encontrados ({len(veiculos_unicos)}):")
        for v in veiculos_unicos:
            log.append(f"  - {v}")
        
        log.append(f"\nComerciais/Campanhas encontrados ({len(comerciais_unicos)}):")
        for c in comerciais_unicos:
            log.append(f"  - {c}")
    
    return pd.DataFrame(resultados), log

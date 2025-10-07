import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
from typing import Tuple, Dict
import logging

class ComparadorPlanilhas:
    """Classe para comparação otimizada entre planilhas Soudview e Checking"""
    
    def __init__(self, threshold_match: int = 80):
        """
        Inicializa o comparador
        
        Args:
            threshold_match: Score mínimo para considerar um match válido (0-100)
        """
        self.threshold_match = threshold_match
        self.logger = logging.getLogger(__name__)
    
    def normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto removendo caracteres especiais e padronizando formato
        
        Args:
            texto: Texto a ser normalizado
            
        Returns:
            Texto normalizado
        """
        if pd.isna(texto):
            return ""
        
        import re
        texto = str(texto).strip().upper()
        # Remove acentos
        texto = texto.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        texto = texto.replace('Ó', 'O').replace('Ú', 'U').replace('Ã', 'A')
        texto = texto.replace('Õ', 'O').replace('Ç', 'C').replace('Â', 'A')
        texto = texto.replace('Ê', 'E').replace('Ô', 'O')
        
        # Remove múltiplos espaços
        texto = re.sub(r'\s+', ' ', texto)
        # Remove caracteres especiais mas mantém letras, números e espaços
        texto = re.sub(r'[^\w\s]', '', texto)
        
        return texto.strip()
    
    def preparar_soudview(self, df_soud: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara e normaliza dados da Soudview
        
        Args:
            df_soud: DataFrame com dados da Soudview
            
        Returns:
            DataFrame preparado
        """
        df = df_soud.copy()
        
        # Normaliza campos principais
        df['veiculo_norm'] = df['veiculo_soudview'].apply(self.normalizar_texto)
        df['comercial_norm'] = df['comercial_soudview'].apply(self.normalizar_texto)
        
        # Converte data para formato padrão
        df['data_norm'] = pd.to_datetime(df['data'], errors='coerce').dt.date
        
        # Normaliza horário para minuto (HH:MM)
        df['horario_minuto'] = df['horario'].apply(
            lambda x: x.strftime('%H:%M') if pd.notna(x) else None
        )
        
        # Remove registros com dados essenciais faltando
        df = df.dropna(subset=['veiculo_norm', 'data_norm', 'horario_minuto'])
        df = df[df['veiculo_norm'] != '']
        
        return df
    
    def preparar_checking(self, df_checking: pd.DataFrame, 
                          filtro_local: str = "SÃO PAULO") -> pd.DataFrame:
        """
        Prepara e normaliza dados do Checking
        
        Args:
            df_checking: DataFrame com dados do Checking
            filtro_local: Texto para filtrar registros por localização
            
        Returns:
            DataFrame preparado e filtrado
        """
        # Mapeamento de colunas esperadas
        col_map = {
            'veiculo': 'VEÍCULO BOXNET',
            'data': 'DATA VEICULAÇÃO',
            'horario': 'HORA VEICULAÇÃO',
            'campanha': 'CAMPANHA'
        }
        
        # Verifica se todas as colunas necessárias existem
        colunas_faltantes = [v for v in col_map.values() if v not in df_checking.columns]
        if colunas_faltantes:
            raise ValueError(f"Colunas faltando no Checking: {colunas_faltantes}")
        
        df = df_checking.copy()
        
        # Filtra por localização se especificado
        if filtro_local:
            df = df[df[col_map['veiculo']].str.contains(
                filtro_local, case=False, na=False
            )]
        
        if df.empty:
            raise ValueError(f"Nenhum registro encontrado com filtro: {filtro_local}")
        
        # Normaliza campos
        df['veiculo_norm'] = df[col_map['veiculo']].apply(self.normalizar_texto)
        df['campanha_norm'] = df[col_map['campanha']].apply(self.normalizar_texto)
        
        # Normaliza data
        df['data_norm'] = pd.to_datetime(
            df[col_map['data']], dayfirst=True, errors='coerce'
        ).dt.date
        
        # Normaliza horário
        df['horario_norm'] = pd.to_datetime(
            df[col_map['horario']], errors='coerce', format='%H:%M:%S'
        ).dt.time
        
        df['horario_minuto'] = df['horario_norm'].apply(
            lambda x: x.strftime('%H:%M') if pd.notna(x) else None
        )
        
        # Remove registros inválidos
        df = df.dropna(subset=['veiculo_norm', 'data_norm', 'horario_minuto'])
        
        return df
    
    def mapear_veiculos(self, veiculos_origem: list, 
                        veiculos_destino: list) -> Tuple[Dict, Dict]:
        """
        Cria mapeamento entre veículos usando fuzzy matching
        
        Args:
            veiculos_origem: Lista de veículos de origem
            veiculos_destino: Lista de veículos de destino
            
        Returns:
            Tupla com (mapa_veiculos, mapa_scores)
        """
        mapa_veiculos = {}
        mapa_scores = {}
        
        for veiculo in veiculos_origem:
            if not veiculo or veiculo == "VEICULO NAO IDENTIFICADO":
                mapa_veiculos[veiculo] = "NÃO MAPEADO"
                mapa_scores[veiculo] = 0
                continue
            
            resultado = process.extractOne(
                veiculo, 
                veiculos_destino, 
                scorer=fuzz.token_set_ratio
            )
            
            if resultado:
                match, score, _ = resultado
                if score >= self.threshold_match:
                    mapa_veiculos[veiculo] = match
                    mapa_scores[veiculo] = score
                else:
                    mapa_veiculos[veiculo] = "NÃO MAPEADO"
                    mapa_scores[veiculo] = score
            else:
                mapa_veiculos[veiculo] = "NÃO MAPEADO"
                mapa_scores[veiculo] = 0
        
        return mapa_veiculos, mapa_scores
    
    def comparar(self, df_soudview: pd.DataFrame, 
                 df_checking: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza a comparação completa entre as planilhas
        
        Args:
            df_soudview: DataFrame da Soudview processado
            df_checking: DataFrame do Checking
            
        Returns:
            DataFrame com relatório de comparação
        """
        # Prepara os dados
        df_soud = self.preparar_soudview(df_soudview)
        df_check = self.preparar_checking(df_checking)
        
        self.logger.info(f"Soudview: {len(df_soud)} registros preparados")
        self.logger.info(f"Checking: {len(df_check)} registros preparados")
        
        # Mapeia veículos
        veiculos_soud = df_soud['veiculo_norm'].unique()
        veiculos_check = df_check['veiculo_norm'].unique()
        
        mapa_veiculos, mapa_scores = self.mapear_veiculos(
            veiculos_soud, veiculos_check
        )
        
        # Aplica mapeamento
        df_soud['veiculo_mapeado'] = df_soud['veiculo_norm'].map(mapa_veiculos)
        df_soud['score_match'] = df_soud['veiculo_norm'].map(mapa_scores)
        
        # Realiza merge
        resultado = pd.merge(
            df_soud,
            df_check,
            left_on=['veiculo_mapeado', 'data_norm', 'horario_minuto', 'comercial_norm'],
            right_on=['veiculo_norm', 'data_norm', 'horario_minuto', 'campanha_norm'],
            how='left',
            indicator=True,
            suffixes=('_soud', '_check')
        )
        
        # Define status
        resultado['status'] = np.where(
            resultado['_merge'] == 'both',
            'ENCONTRADO',
            'NAO_ENCONTRADO'
        )
        
        # Adiciona informações adicionais
        resultado['motivo_nao_encontrado'] = resultado.apply(
            lambda row: self._diagnosticar_nao_encontrado(row) 
            if row['status'] == 'NAO_ENCONTRADO' else '', 
            axis=1
        )
        
        # Seleciona e renomeia colunas finais
        colunas_saida = {
            'veiculo_soudview': 'Veiculo_Original',
            'veiculo_mapeado': 'Veiculo_Mapeado',
            'score_match': 'Score_Match',
            'comercial_soudview': 'Comercial',
            'data': 'Data',
            'horario': 'Horario',
            'status': 'Status',
            'motivo_nao_encontrado': 'Motivo'
        }
        
        resultado = resultado.rename(columns=colunas_saida)
        
        return resultado[[col for col in colunas_saida.values() if col in resultado.columns]]
    
    def _diagnosticar_nao_encontrado(self, row: pd.Series) -> str:
        """Diagnostica possível motivo de não ter encontrado match"""
        if row['veiculo_mapeado'] == 'NÃO MAPEADO':
            return 'Veículo não mapeado'
        return 'Não encontrado no checking'
    
    def gerar_estatisticas(self, df_resultado: pd.DataFrame) -> Dict:
        """
        Gera estatísticas do resultado da comparação
        
        Args:
            df_resultado: DataFrame com resultado da comparação
            
        Returns:
            Dicionário com estatísticas
        """
        total = len(df_resultado)
        encontrados = (df_resultado['Status'] == 'ENCONTRADO').sum()
        nao_encontrados = total - encontrados
        
        # Estatísticas por veículo
        stats_veiculo = df_resultado.groupby('Veiculo_Original').agg({
            'Status': lambda x: (x == 'ENCONTRADO').sum(),
        }).rename(columns={'Status': 'Encontrados'})
        
        stats_veiculo['Total'] = df_resultado.groupby('Veiculo_Original').size()
        stats_veiculo['Taxa_Match'] = (
            stats_veiculo['Encontrados'] / stats_veiculo['Total'] * 100
        ).round(2)
        
        return {
            'total': total,
            'encontrados': encontrados,
            'nao_encontrados': nao_encontrados,
            'taxa_match': round(encontrados / total * 100, 2) if total > 0 else 0,
            'por_veiculo': stats_veiculo.to_dict('index')
        }


# Exemplo de uso
if __name__ == "__main__":
    # Configuração de logging
    logging.basicConfig(level=logging.INFO)
    
    # Inicializa comparador
    comparador = ComparadorPlanilhas(threshold_match=85)
    
    # Exemplo de comparação
    # df_resultado = comparador.comparar(df_soudview, df_checking)
    # stats = comparador.gerar_estatisticas(df_resultado)
    # print(f"Taxa de match: {stats['taxa_match']}%")

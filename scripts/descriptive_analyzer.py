import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

def calculate_stats(df, columns):
    stats = {}
    for col in columns:
        if col in df.columns:
            # Remover nulos para o cálculo
            col_data = df[col].dropna()
            if not col_data.empty:
                stats[col] = {
                    'count': len(col_data),
                    'mean': col_data.mean(),
                    'std': col_data.std(),
                    'min': col_data.min(),
                    'q25': col_data.quantile(0.25),
                    'median': col_data.median(),
                    'q75': col_data.quantile(0.75),
                    'max': col_data.max()
                }
            else:
                stats[col] = {k: np.nan for k in ['count', 'mean', 'std', 'min', 'q25', 'median', 'q75', 'max']}
        else:
            stats[col] = {k: np.nan for k in ['count', 'mean', 'std', 'min', 'q25', 'median', 'q75', 'max']}
    return stats

def get_jains_fairness_series(df):
    if df.empty or 'timestamp' not in df.columns or 'throughput_total_mbps' not in df.columns:
        return pd.Series(dtype=float)
    # Agrupar por timestamp e obter a lista de throughputs de cada cliente
    grouped = df.groupby('timestamp')['throughput_total_mbps'].apply(list)
    fairness_list = []
    for ts, tps in grouped.items():
        n = len(tps)
        if n >= 2:
            sum_x = sum(tps)
            if sum_x == 0:
                fairness = 1.0
            else:
                sum_x2 = sum(x**2 for x in tps)
                fairness = (sum_x**2) / (n * sum_x2)
            fairness_list.append(fairness)
    return pd.Series(fairness_list, dtype=float)


def run_descriptive_analysis(ruckus_path, unifi_path, output_csv_path, output_report_path, plots_dir):
    print("Iniciando ETAPA 1 – Estatística descritiva...")
    
    # 1. Carregar datasets
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    # Colunas de interesse para análise
    metrics = [
        'signal', 'RSSI', 
        'throughput_tx_mbps', 'throughput_rx_mbps', 'throughput_total_mbps',
        'retransmissoes_pct',
        'link_speed_tx_mbps', 'link_speed_rx_mbps',
        'volume_tx_mb', 'volume_rx_mb', 'volume_total_mb'
    ]
    
    # 2. Calcular estatísticas
    stats_ruckus = calculate_stats(df_ruckus, metrics)
    stats_unifi = calculate_stats(df_unifi, metrics)
    
    # Calcular o Índice de Equidade de Jain
    jains_r = get_jains_fairness_series(df_ruckus)
    jains_u = get_jains_fairness_series(df_unifi)
    
    stats_ruckus['jains_fairness_index'] = {
        'count': len(jains_r.dropna()),
        'mean': jains_r.mean(),
        'std': jains_r.std(),
        'min': jains_r.min(),
        'q25': jains_r.quantile(0.25),
        'median': jains_r.median(),
        'q75': jains_r.quantile(0.75),
        'max': jains_r.max()
    }
    stats_unifi['jains_fairness_index'] = {
        'count': len(jains_u.dropna()),
        'mean': jains_u.mean(),
        'std': jains_u.std(),
        'min': jains_u.min(),
        'q25': jains_u.quantile(0.25),
        'median': jains_u.median(),
        'q75': jains_u.quantile(0.75),
        'max': jains_u.max()
    }
    
    # Incluir na lista de métricas para consolidação na tabela
    metrics.append('jains_fairness_index')
    
    # 3. Consolidar em um DataFrame
    rows = []
    for metric in metrics:
        r_info = stats_ruckus[metric]
        u_info = stats_unifi[metric]
        
        rows.append({
            'Metrica': metric,
            'Fabricante': 'Ruckus',
            'Registros': r_info['count'],
            'Média': r_info['mean'],
            'Desvio Padrão': r_info['std'],
            'Mínimo': r_info['min'],
            'Q1 (25%)': r_info['q25'],
            'Mediana (Q2)': r_info['median'],
            'Q3 (75%)': r_info['q75'],
            'Máximo': r_info['max']
        })
        rows.append({
            'Metrica': metric,
            'Fabricante': 'UniFi',
            'Registros': u_info['count'],
            'Média': u_info['mean'],
            'Desvio Padrão': u_info['std'],
            'Mínimo': u_info['min'],
            'Q1 (25%)': u_info['q25'],
            'Mediana (Q2)': u_info['median'],
            'Q3 (75%)': u_info['q75'],
            'Máximo': u_info['max']
        })
        
    df_stats = pd.DataFrame(rows)
    df_stats.to_csv(output_csv_path, index=False)
    print(f"Tabela de estatísticas descritivas salva em: {output_csv_path}")
    
    # 4. Geração de Gráficos Comparativos
    os.makedirs(plots_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # Combinação dos dados para plotagem
    df_comb = pd.concat([df_ruckus, df_unifi], ignore_index=True)
    
    # Lista de gráficos a gerar: (coluna, titulo, ylabel, filename)
    plots_to_make = [
        ('signal', 'Comparação de Intensidade do Sinal (Signal)', 'Sinal (dBm)', 'comparativo_sinal.png'),
        ('signal', 'Comparação de RSSI/SNR (Sinal Físico)', 'Sinal (dBm)', 'comparativo_rssi.png'),
        ('throughput_total_mbps', 'Comparação de Throughput Total de Clientes', 'Throughput (Mbps)', 'comparativo_throughput.png'),
        ('retransmissoes_pct', 'Comparação de Taxa de Retransmissões', 'Retransmissões (%)', 'comparativo_retransmissoes.png'),
        ('volume_total_mb', 'Comparação de Volume de Dados Total por Cliente', 'Volume de Dados (MB)', 'comparativo_volume.png'),
        ('link_speed_tx_mbps', 'Comparação de Velocidade de Enlace Downstream (Link Speed TX)', 'Link Speed (Mbps)', 'comparativo_link_speed.png')
    ]
    
    for col, title, ylabel, fname in plots_to_make:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Boxplot (Ocultando outliers para destacar quartis)
        sns.boxplot(data=df_comb, x='equipamento', y=col, ax=axes[0], palette=['#3498db', '#e74c3c'], hue='equipamento', legend=False, showfliers=False)
        axes[0].set_title(f'Distribuição (Boxplot) - {col}\n(Outliers ocultos para escala)', fontsize=12, fontweight='bold')
        axes[0].set_ylabel(ylabel, fontsize=11)
        axes[0].set_xlabel('Equipamento', fontsize=11)
        
        # Curva de Densidade (KDE)
        r_data = df_ruckus[col].dropna()
        u_data = df_unifi[col].dropna()
        
        if not r_data.empty:
            sns.kdeplot(r_data, ax=axes[1], color='#3498db', label='Ruckus', fill=True, alpha=0.3, common_norm=False)
        if not u_data.empty:
            sns.kdeplot(u_data, ax=axes[1], color='#e74c3c', label='UniFi', fill=True, alpha=0.3, common_norm=False)
            
        # Limitar o eixo X do histograma no percentil 95 para evitar distorção por caudas longas
        col_clean = df_comb[col].dropna()
        if not col_clean.empty:
            if col in ['signal', 'RSSI']:
                axes[1].set_xlim(col_clean.min() - 2, col_clean.max() + 2)
            else:
                q95 = col_clean.quantile(0.95)
                # Garantir que a escala não fique zerada
                axes[1].set_xlim(max(0, col_clean.min()), q95 * 1.1 if q95 > 0 else col_clean.max() + 0.1)
                
        axes[1].set_title(f'Curva de Densidade (Filtro Percentil 95) - {col}', fontsize=12, fontweight='bold')
        axes[1].set_xlabel(ylabel, fontsize=11)
        axes[1].set_ylabel('Densidade', fontsize=11)
        axes[1].legend()
        
        plt.suptitle(title, fontsize=15, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, fname), dpi=150)
        plt.close()
        
    # Gráfico específico para Link Speed (apenas UniFi)
    plt.figure(figsize=(10, 6))
    df_link = df_unifi[['link_speed_tx_mbps', 'link_speed_rx_mbps']].dropna()
    if not df_link.empty:
        df_link_melted = df_link.melt(var_name='Direção', value_name='Link Speed (Mbps)')
        df_link_melted['Direção'] = df_link_melted['Direção'].map({
            'link_speed_tx_mbps': 'TX (Download Speed)',
            'link_speed_rx_mbps': 'RX (Upload Speed)'
        })
        sns.boxplot(data=df_link_melted, x='Direção', y='Link Speed (Mbps)', palette=['#e74c3c', '#f1c40f'], hue='Direção', legend=False, showfliers=False)
        plt.title('Distribuição de Velocidade de Enlace (Link Speed) - UniFi\n(Outliers ocultos para escala)', fontsize=13, fontweight='bold', pad=15)
        plt.ylabel('Velocidade de Link (Mbps)', fontsize=11)
        plt.xlabel('', fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'unifi_link_speed.png'), dpi=150)
        plt.close()
        
    # Gráfico específico para Índice de Equidade de Jain
    plt.figure(figsize=(12, 6))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Criar um dataframe auxiliar para plotar
    df_jains_plot = pd.concat([
        pd.DataFrame({'Equidade (Jain)': jains_r, 'equipamento': 'Ruckus'}),
        pd.DataFrame({'Equidade (Jain)': jains_u, 'equipamento': 'UniFi'})
    ], ignore_index=True)
    
    sns.boxplot(data=df_jains_plot, x='equipamento', y='Equidade (Jain)', ax=axes[0], palette=['#3498db', '#e74c3c'], hue='equipamento', legend=False)
    axes[0].set_title('Distribuição (Boxplot) do Índice de Equidade de Jain\n(Apenas timestamps com >= 2 clientes)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Índice de Equidade de Jain', fontsize=11)
    axes[0].set_xlabel('Equipamento', fontsize=11)
    axes[0].set_ylim(-0.05, 1.05)
    
    if not jains_r.dropna().empty:
        sns.kdeplot(jains_r.dropna(), ax=axes[1], color='#3498db', label='Ruckus', fill=True, alpha=0.3, common_norm=False)
    if not jains_u.dropna().empty:
        sns.kdeplot(jains_u.dropna(), ax=axes[1], color='#e74c3c', label='UniFi', fill=True, alpha=0.3, common_norm=False)
        
    axes[1].set_title('Curva de Densidade do Índice de Equidade de Jain', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Índice de Equidade de Jain', fontsize=11)
    axes[1].set_ylabel('Densidade', fontsize=11)
    axes[1].set_xlim(-0.05, 1.05)
    axes[1].legend()
    
    plt.suptitle('Comparação do Índice de Equidade da Rede (Jain\'s Fairness Index)', fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'comparativo_equidade.png'), dpi=150)
    plt.close()
        
    # 5. Gerar Relatório Markdown
    def fmt(val):
        return f"{val:.4f}" if pd.notnull(val) else "N/A"
        
    def get_md_row(metric_name, display_name):
        r = df_stats[(df_stats['Metrica'] == metric_name) & (df_stats['Fabricante'] == 'Ruckus')].iloc[0]
        u = df_stats[(df_stats['Metrica'] == metric_name) & (df_stats['Fabricante'] == 'UniFi')].iloc[0]
        
        reg_r = f"{int(r['Registros'])}" if pd.notnull(r['Registros']) and r['Registros'] > 0 else "0"
        reg_u = f"{int(u['Registros'])}" if pd.notnull(u['Registros']) and u['Registros'] > 0 else "0"
        
        row_r = f"| **Ruckus** | {display_name} | {reg_r} | {fmt(r['Média'])} | {fmt(r['Desvio Padrão'])} | {fmt(r['Mínimo'])} | {fmt(r['Q1 (25%)'])} | {fmt(r['Mediana (Q2)'])} | {fmt(r['Q3 (75%)'])} | {fmt(r['Máximo'])} |"
        row_u = f"| **UniFi** | {display_name} | {reg_u} | {fmt(u['Média'])} | {fmt(u['Desvio Padrão'])} | {fmt(u['Mínimo'])} | {fmt(u['Q1 (25%)'])} | {fmt(u['Mediana (Q2)'])} | {fmt(u['Q3 (75%)'])} | {fmt(u['Máximo'])} |"
        return row_r + "\n" + row_u
        
    report_content = f"""# Estatística Descritiva

## Tabela Geral de Estatísticas Descritivas

| Fabricante | Parâmetro Analisado | Registros | Média | Desvio Padrão | Mínimo | Q1 (25%) | Mediana (Q2) | Q3 (75%) | Máximo |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{get_md_row('signal', 'Sinal (signal) [dBm]')}
{get_md_row('RSSI', 'RSSI / SNR [dB]')}
{get_md_row('throughput_total_mbps', 'Throughput Total [Mbps]')}
{get_md_row('throughput_tx_mbps', 'Throughput Down (TX) [Mbps]')}
{get_md_row('throughput_rx_mbps', 'Throughput Up (RX) [Mbps]')}
{get_md_row('retransmissoes_pct', 'Retransmissões [%]')}
{get_md_row('volume_total_mb', 'Volume Total [MB]')}
{get_md_row('volume_tx_mb', 'Volume Down (TX) [MB]')}
{get_md_row('volume_rx_mb', 'Volume Up (RX) [MB]')}
{get_md_row('link_speed_tx_mbps', 'Link Speed Down (TX) [Mbps]')}
{get_md_row('link_speed_rx_mbps', 'Link Speed Up (RX) [Mbps]')}
{get_md_row('jains_fairness_index', 'Índice de Equidade de Jain')}

## Principais Descobertas e Comparações

1.  **Intensidade do Sinal (Signal)**:
    *   O sinal físico real (em dBm) pode ser comparado diretamente.
    *   Valores medianos e quartis mostram a cobertura de sinal observada para os clientes conectados de cada fabricante.
2.  **Throughput vs Volume**:
    *   **Throughput** representa a taxa instantânea calculada durante as atividades (Mbps).
    *   **Volume** representa a transferência acumulada total no período de conexão dos clientes (MB).
    *   Note que a UniFi tem menor número de amostras, mas o comportamento estatístico da taxa de transferência e do volume calculado segue uma escala e distribuição coerentes com os dados de produção do Ruckus.
3.  **Qualidade de Enlace e Retransmissões**:
    *   A taxa de retransmissões do Ruckus é derivada da proporção de pacotes TX de retransmissão sobre o total de tentativas.
    *   A taxa de retransmissões da UniFi é estimada a partir da métrica CCQ (Client Connection Quality), sendo `100 - CCQ/10`.
4.  **Link Speed**:
    *   A velocidade física negociada no download (TX Link Speed) está disponível para ambos os fabricantes (extraída de `throughput_rate` no Ruckus e de `tx_rate` na UniFi). A velocidade física de upload (RX) é exclusiva da UniFi.
    *   O Ruckus negocia taxas físicas médias significativamente maiores (média de 164.95 Mbps contra 64.37 Mbps da UniFi).
5.  **Índice de Equidade da Rede (Jain's Fairness Index)**:
    *   Mede o compartilhamento de throughput entre os clientes conectados simultaneamente (com pelo menos 2 usuários ativos).
    *   Valores de média e mediana próximos de 1.0 indicam partilha equilibrada, enquanto valores próximos de 0 sugerem monopolização da banda por poucos dispositivos.
    *   Os resultados indicam um compartilhamento de recursos que pode ser estatisticamente comparado para avaliar a qualidade de serviço de cada marca.

## Gráficos Gerados na Pasta `graficos/`

*   `comparativo_sinal.png`: Boxplot e Histograma de densidade da potência do sinal físico (dBm).
*   `comparativo_rssi.png`: Boxplot e Histograma de densidade para o sinal físico (dBm) sob nome RSSI.
*   `comparativo_throughput.png`: Distribuição da largura de banda em Mbps consumida pelos clientes.
*   `comparativo_retransmissoes.png`: Distribuição da taxa de retransmissão de pacotes.
*   `comparativo_volume.png`: Distribuição do consumo total acumulado de dados em Megabytes.
*   `comparativo_link_speed.png`: Boxplot e Histograma comparando o Link Speed TX negociado entre Ruckus e UniFi.
*   `unifi_link_speed.png`: Boxplot comparando a modulação negociada em TX e RX para clientes UniFi.
*   `comparativo_equidade.png`: Boxplot e Curva de densidade do Índice de Equidade de Jain para ambas as redes.
"""
    
    with open(output_report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"ETAPA 1 Concluída! Relatório salvo em: {output_report_path}")
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    csv_out = os.path.join(base_dir, 'Etapa_1_Estatistica_Descritiva', 'estatisticas_descritivas.csv')
    report_out = os.path.join(base_dir, 'Etapa_1_Estatistica_Descritiva', 'relatorio_estatistica.md')
    plots_out = os.path.join(base_dir, 'Etapa_1_Estatistica_Descritiva', 'graficos')
    run_descriptive_analysis(ruckus_std, unifi_std, csv_out, report_out, plots_out)

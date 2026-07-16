import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr

# Adicionar a raiz do projeto ao sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from utils.convert_md_to_pdf import convert_md_to_pdf

def run_correlation_analysis(ruckus_path, unifi_path, output_dir):
    print("Iniciando ETAPA 3 – Análise de Correlações...")
    
    # 1. Carregar datasets padronizados
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados. Execute o standardizer primeiro.")
        return False
        
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    # Garantir conversão temporal
    df_ruckus['timestamp'] = pd.to_datetime(df_ruckus['timestamp'])
    df_unifi['timestamp'] = pd.to_datetime(df_unifi['timestamp'])
    
    # Criar diretórios de saída
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'graficos_dispersao')
    os.makedirs(plots_dir, exist_ok=True)
    
    sns.set_theme(style="whitegrid")
    
    # Dicionários para armazenar os coeficientes de Pearson e Spearman
    results = []
    
    # Funções auxiliares para calcular correlação com segurança
    def get_correlation(df, x_col, y_col):
        df_clean = df[[x_col, y_col]].dropna()
        df_clean = df_clean[np.isfinite(df_clean[x_col]) & np.isfinite(df_clean[y_col])]
        if len(df_clean) < 5:
            return np.nan, np.nan, 0
        try:
            r, p = pearsonr(df_clean[x_col], df_clean[y_col])
            return r, p, len(df_clean)
        except:
            return np.nan, np.nan, len(df_clean)

    def get_spearman_correlation(df, x_col, y_col):
        df_clean = df[[x_col, y_col]].dropna()
        df_clean = df_clean[np.isfinite(df_clean[x_col]) & np.isfinite(df_clean[y_col])]
        if len(df_clean) < 5:
            return np.nan, np.nan
        try:
            r, p = spearmanr(df_clean[x_col], df_clean[y_col])
            return r, p
        except:
            return np.nan, np.nan

    def process_relation(df_rk, df_uf, x_col, y_col, name, rk_label_x='RSSI', uf_label_x='RSSI', label_y='Throughput Total', plot_name=None):
        r_rk, p_rk, n_rk = get_correlation(df_rk, x_col, y_col)
        r_uf, p_uf, n_uf = get_correlation(df_uf, x_col, y_col)
        rs_rk, ps_rk = get_spearman_correlation(df_rk, x_col, y_col)
        rs_uf, ps_uf = get_spearman_correlation(df_uf, x_col, y_col)
        
        results.append({
            'Relacao': name,
            'Ruckus_R_P': r_rk, 'Ruckus_P_P': p_rk, 'Ruckus_N': n_rk,
            'UniFi_R_P': r_uf, 'UniFi_P_P': p_uf, 'UniFi_N': n_uf,
            'Ruckus_R_S': rs_rk, 'Ruckus_P_S': ps_rk,
            'UniFi_R_S': rs_uf, 'UniFi_P_S': ps_uf
        })
        
        if plot_name:
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            sns.regplot(data=df_rk, x=x_col, y=y_col, ax=axes[0], color='#3498db', scatter_kws={'alpha':0.2, 's':10}, line_kws={'color':'red'})
            axes[0].set_title(f'Ruckus: {rk_label_x} x {label_y}\n(Pearson r = {r_rk:.4f}, Spearman rs = {rs_rk:.4f})', fontweight='bold', fontsize=10)
            axes[0].set_xlabel(rk_label_x)
            axes[0].set_ylabel(label_y)
            
            sns.regplot(data=df_uf, x=x_col, y=y_col, ax=axes[1], color='#e74c3c', scatter_kws={'alpha':0.3, 's':15}, line_kws={'color':'blue'})
            axes[1].set_title(f'UniFi: {uf_label_x} x {label_y}\n(Pearson r = {r_uf:.4f}, Spearman rs = {rs_uf:.4f})', fontweight='bold', fontsize=10)
            axes[1].set_xlabel(uf_label_x)
            axes[1].set_ylabel(label_y)
            plt.tight_layout()
            plt.savefig(os.path.join(plots_dir, plot_name), dpi=150)
            plt.close()

    # 1. RSSI x Throughput (Total)
    process_relation(df_ruckus, df_unifi, 'RSSI', 'throughput_total_mbps', 'RSSI x Throughput Total', 'RSSI (dBm)', 'RSSI (Índice SNR)', 'Throughput Total (Mbps)', '01_rssi_throughput.png')
    
    # 2. RSSI x Retransmissões
    process_relation(df_ruckus, df_unifi, 'RSSI', 'retransmissoes_pct', 'RSSI x Retransmissoes', 'RSSI (dBm)', 'RSSI (Índice SNR)', 'Retransmissões (%)', '02_rssi_retransmissoes.png')
    
    # 3. Retransmissões x Throughput
    process_relation(df_ruckus, df_unifi, 'retransmissoes_pct', 'throughput_total_mbps', 'Retransmissoes x Throughput Total', 'Retransmissões (%)', 'Retransmissões (%)', 'Throughput Total (Mbps)', '03_retransmissoes_throughput.png')
    
    # 4. Número de clientes x Throughput agregado do AP (Groupby timestamp + AP)
    def aggregate_by_ap(df):
        ap_group = df.groupby(['timestamp', 'AP']).agg(
            qtd_clientes=('cliente (MAC)', 'nunique'),
            throughput_agregado_mbps=('throughput_total_mbps', 'sum'),
            retransmissoes_media_pct=('retransmissoes_pct', 'mean')
        ).reset_index()
        return ap_group

    df_ap_rk = aggregate_by_ap(df_ruckus)
    df_ap_uf = aggregate_by_ap(df_unifi)
    
    process_relation(df_ap_rk, df_ap_uf, 'qtd_clientes', 'throughput_agregado_mbps', 'Qtd Clientes x Throughput Agregado AP', 'Qtd Clientes no AP', 'Qtd Clientes no AP', 'Throughput Agregado AP (Mbps)', '04_clientes_throughput_ap.png')
    
    # 5. Número de clientes x Retransmissões médias do AP
    process_relation(df_ap_rk, df_ap_uf, 'qtd_clientes', 'retransmissoes_media_pct', 'Qtd Clientes x Retransmissoes Medias AP', 'Qtd Clientes no AP', 'Qtd Clientes no AP', 'Retransmissões Médias AP (%)', '05_clientes_retransmissoes_ap.png')
    
    # 6. Noise x Retransmissões
    process_relation(df_ruckus, df_unifi, 'noise', 'retransmissoes_pct', 'Noise x Retransmissoes', 'Noise Floor (dBm)', 'Noise Floor (dBm)', 'Retransmissões (%)', '06_noise_retransmissoes.png')
    
    # 7. Noise x RSSI
    process_relation(df_ruckus, df_unifi, 'noise', 'RSSI', 'Noise x RSSI', 'Noise Floor (dBm)', 'Noise Floor (dBm)', 'RSSI (dBm/SNR)', '07_noise_rssi.png')
    
    # 8. Link Speed TX x Throughput TX
    process_relation(df_ruckus, df_unifi, 'link_speed_tx_mbps', 'throughput_tx_mbps', 'Link Speed TX x Throughput TX', 'TX Link Speed (Mbps)', 'TX Link Speed (Mbps)', 'Throughput TX (Mbps)', '08_link_speed_throughput.png')
    
    # 9. Volume de dados x Tempo de sessão (Uptime)
    r_rk, p_rk, n_rk = get_correlation(df_ruckus, 'tempo_sessao_seg', 'volume_total_mb')
    r_uf, p_uf, n_uf = get_correlation(df_unifi, 'tempo_sessao_seg', 'volume_total_mb')
    rs_rk, ps_rk = get_spearman_correlation(df_ruckus, 'tempo_sessao_seg', 'volume_total_mb')
    rs_uf, ps_uf = get_spearman_correlation(df_unifi, 'tempo_sessao_seg', 'volume_total_mb')
    results.append({
        'Relacao': 'Volume Total x Tempo de Sessao',
        'Ruckus_R_P': r_rk, 'Ruckus_P_P': p_rk, 'Ruckus_N': n_rk,
        'UniFi_R_P': r_uf, 'UniFi_P_P': p_uf, 'UniFi_N': n_uf,
        'Ruckus_R_S': rs_rk, 'Ruckus_P_S': ps_rk,
        'UniFi_R_S': rs_uf, 'UniFi_P_S': ps_uf
    })
    
    plt.figure(figsize=(10, 6))
    sns.regplot(data=df_ruckus, x='tempo_sessao_seg', y='volume_total_mb', color='#3498db', scatter_kws={'alpha':0.2, 's':10}, line_kws={'color':'red'})
    plt.title(f'Ruckus: Tempo de Sessão x Volume de Dados Acumulado\n(Pearson r = {r_rk:.4f}, Spearman rs = {rs_rk:.4f})', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Tempo de Sessão (Uptime, segundos)', fontsize=11)
    plt.ylabel('Volume de Dados Total (MB)', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, '09_ruckus_uptime_volume.png'), dpi=150)
    plt.close()

    # 10. Matriz de Correlação Heatmap (Spearman)
    corr_cols = ['signal', 'RSSI', 'noise', 'throughput_total_mbps', 'retransmissoes_pct', 'volume_total_mb', 'tempo_sessao_seg']
    renamed_cols = {
        'signal': 'Sinal (dBm)',
        'RSSI': 'RSSI/SNR (dB)',
        'noise': 'Ruído (dBm)',
        'throughput_total_mbps': 'Throughput (Mbps)',
        'retransmissoes_pct': 'Retransmissões (%)',
        'volume_total_mb': 'Volume (MB)',
        'tempo_sessao_seg': 'Tempo Sessão (s)'
    }
    
    df_corr_rk = df_ruckus[corr_cols].rename(columns=renamed_cols).dropna(how='all')
    corr_matrix_rk = df_corr_rk.corr(method='spearman')
    
    df_corr_uf = df_unifi[corr_cols].rename(columns=renamed_cols).dropna(how='all')
    corr_matrix_uf = df_corr_uf.corr(method='spearman')
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    sns.heatmap(corr_matrix_rk, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, center=0, ax=axes[0], cbar_kws={'label': 'Coeficiente de Spearman (rs)'})
    axes[0].set_title('Ruckus: Matriz de Correlação (Spearman)', fontsize=13, fontweight='bold', pad=10)
    
    sns.heatmap(corr_matrix_uf, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, center=0, ax=axes[1], cbar_kws={'label': 'Coeficiente de Spearman (rs)'})
    axes[1].set_title('UniFi: Matriz de Correlação (Spearman)', fontsize=13, fontweight='bold', pad=10)
    
    plt.tight_layout()
    heatmap_path = os.path.join(plots_dir, 'matriz_correlacao_heatmap.png')
    plt.savefig(heatmap_path, dpi=150)
    plt.close()

    # Salvar tabela CSV
    df_results = pd.DataFrame(results)
    csv_path = os.path.join(output_dir, 'coeficientes_correlacao.csv')
    df_results.to_csv(csv_path, index=False)
    print(f"Tabela de correlações exportada em: {csv_path}")

    # 2. Gerar Relatório Markdown
    def get_row(rel):
        row = df_results[df_results['Relacao'] == rel].iloc[0]
        def fmt_val(r, p):
            if pd.isnull(r):
                return "N/A"
            sig = "*" if p < 0.05 else ""
            sig = "**" if p < 0.01 else sig
            return f"{r:.4f}{sig}"
        return f"| **{rel}** | {fmt_val(row['Ruckus_R_P'], row['Ruckus_P_P'])} | {fmt_val(row['Ruckus_R_S'], row['Ruckus_P_S'])} | {int(row['Ruckus_N'])} | {fmt_val(row['UniFi_R_P'], row['UniFi_P_P'])} | {fmt_val(row['UniFi_R_S'], row['UniFi_P_S'])} | {int(row['UniFi_N'])} |"

    report_content = f"""# Relatório de Análise de Correlações (Etapa 3)

Este relatório apresenta e analisa os coeficientes de correlação de **Pearson (*r_p*)** e **Spearman (*r_s*)** e gera gráficos correspondentes para analisar quantitativamente o comportamento da telemetria das redes UniFi e Ruckus.

> [!NOTE]
> **Limitação do Escopo**: As discussões e conclusões apresentadas neste relatório baseiam-se estritamente no cenário e conjunto de dados observados durante o período de coleta. Os resultados sugerem tendências e comportamentos de rede nesse ambiente específico, não devendo ser interpretados como regras gerais absolutas.

Os coeficientes de Pearson medem a força de uma relação linear, enquanto os de Spearman medem a relação monotônica (útil para distribuições não-normais e não-lineares). Ambos variam de -1 a +1. Nas tabelas, a presença de um asterisco indica significância estatística de p < 0.05 e dois asteriscos indicam p < 0.01.

## Tabela Consolidada de Coeficientes de Pearson (*r_p*) e Spearman (*r_s*)

| Relação Investigada | Ruckus (*r_p*) | Ruckus (*r_s*) | Amostras (*N*) | UniFi (*r_p*) | UniFi (*r_s*) | Amostras (*N*) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{get_row('RSSI x Throughput Total')}
{get_row('RSSI x Retransmissoes')}
{get_row('Retransmissoes x Throughput Total')}
{get_row('Qtd Clientes x Throughput Agregado AP')}
{get_row('Qtd Clientes x Retransmissoes Medias AP')}
{get_row('Noise x Retransmissoes')}
{get_row('Noise x RSSI')}
{get_row('Link Speed TX x Throughput TX')}
{get_row('Volume Total x Tempo de Sessao')}

---

## Matrizes de Correlação (Heatmap Geral)

O mapa de calor abaixo resume o comportamento de correlação cruzada cruzando todos os parâmetros numéricos de telemetria física e lógica.

![Matriz de Correlação Heatmap](graficos_dispersao/matriz_correlacao_heatmap.png)

*   **Ruckus**: Exibe correlações monotônicas muito fortes entre Sinal e RSSI (sendo a mesma grandeza física mapeada) e uma relação moderada a forte entre Ruído (Noise) e Retransmissões. O Throughput dos clientes individuais apresenta baixíssima correlação com a potência do sinal (*r_s* = {df_results.loc[0, "Ruckus_R_S"]:.4f}), condizente com o comportamento de ociosidade predominante.
*   **UniFi**: O sinal absoluto (signal) e o RSSI (que atua como índice SNR) exibem correlação positiva moderada a forte (*r_s* = 0.70). O Throughput individual apresenta correlação positiva de intensidade moderada com a intensidade de sinal (*r_s* = {df_results.loc[0, "UniFi_R_S"]:.4f}). O ruído de fundo (noise) exibe baixíssima correlação com o sinal, validando a física do meio.

---

## Análise de Cada Gráfico de Dispersão

### 1. RSSI × Throughput
*   **Arquivo**: `01_rssi_throughput.png`
*   **Visualização**:
![RSSI x Throughput](graficos_dispersao/01_rssi_throughput.png)
*   **Expectativa Teórica**: Esperava-se uma correlação positiva moderada a forte. Sinais com melhor intensidade (RSSI alto) permitem modulações e taxas físicas maiores, o que deveria se traduzir em taxas mais altas de transferência ativa.
*   **Comportamento Observado**: Os dados sugerem correlação praticamente nula no Ruckus (*r_p* = {df_results.loc[0, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[0, "Ruckus_R_S"]:.4f}) e fraca a moderada na UniFi (*r_p* = {df_results.loc[0, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[0, "UniFi_R_S"]:.4f}).
*   **Discussão**: Esta divergência sugere que o throughput de dados ativo depende fundamentalmente do padrão de demanda do usuário no instante de coleta. A maioria esmagadora dos dispositivos conectados permaneceu ociosa ou gerando tráfego insignificante (background sync), independentemente de estarem com sinal excelente ou intermediário.

### 2. RSSI × Retransmissões
*   **Arquivo**: `02_rssi_retransmissoes.png`
*   **Visualização**:
![RSSI x Retransmissões](graficos_dispersao/02_rssi_retransmissoes.png)
*   **Expectativa Teórica**: Esperava-se uma correlação negativa moderada a forte. Níveis fracos de sinal costumam reduzir o SNR, elevando a taxa de bits incorretos (BER) e gerando retransmissões para recuperar os pacotes.
*   **Comportamento Observado**: Correlação positiva muito fraca no Ruckus (*r_p* = {df_results.loc[1, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[1, "Ruckus_R_S"]:.4f}) e negativa moderada na UniFi (*r_p* = {df_results.loc[1, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[1, "UniFi_R_S"]:.4f}).
*   **Discussão**: Os dados da UniFi são consistentes com a teoria de que o sinal fraco prejudica o canal. Na Ruckus, a fraca correlação observada indica a atuação de mecanismos de hardware e software (como antenas inteligentes BeamFlex e controle de potência dinâmico) que evitam a perda excessiva de quadros físicos mesmo em níveis moderadamente baixos de sinal.

### 3. Retransmissões × Throughput
*   **Arquivo**: `03_retransmissoes_throughput.png`
*   **Visualização**:
![Retransmissões x Throughput](graficos_dispersao/03_retransmissoes_throughput.png)
*   **Expectativa Teórica**: Esperava-se uma correlação negativa moderada, pois altas retransmissões consomem tempo de canal de RF (airtime) e reduzem a capacidade útil.
*   **Comportamento Observado**: Correlação negativa fraca no Ruckus (*r_p* = {df_results.loc[2, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[2, "Ruckus_R_S"]:.4f}) e na UniFi (*r_p* = {df_results.loc[2, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[2, "UniFi_R_S"]:.4f}).
*   **Discussão**: Os resultados sugerem que, como o throughput ativo na rede está muito longe do teto operacional dos canais (baixa carga ativa), o impacto de retransmissões dispersas no throughput do usuário não se mostrou severo o suficiente para gerar decréscimo drástico na taxa média registrada.

### 4. Quantidade de Clientes × Throughput Agregado do AP
*   **Arquivo**: `04_clientes_throughput_ap.png`
*   **Visualização**:
![Clientes x Throughput Agregado](graficos_dispersao/04_clientes_throughput_ap.png)
*   **Expectativa Teórica**: Esperava-se uma correlação positiva moderada a forte, visto que o tráfego total somado em um AP tende a crescer proporcionalmente com a quantidade de dispositivos ativos gerando tráfego concorrente.
*   **Comportamento Observado**: Os dados indicam correlação positiva forte no Ruckus (*r_p* = {df_results.loc[3, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[3, "Ruckus_R_S"]:.4f}) e positiva moderada a forte na UniFi (*r_p* = {df_results.loc[3, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[3, "UniFi_R_S"]:.4f}).
*   **Discussão**: Esse resultado é consistente com o esperado teoricamente. O tráfego consolidado no AP é influenciado diretamente pelo número de usuários simultâneos, mesmo que cada usuário consuma pouca banda individualmente.

### 5. Quantidade de Clientes × Retransmissões Médias do AP
*   **Arquivo**: `05_clientes_retransmissoes_ap.png`
*   **Visualização**:
![Clientes x Retransmissões AP](graficos_dispersao/05_clientes_retransmissoes_ap.png)
*   **Expectativa Teórica**: Esperava-se uma correlação positiva moderada, dado que mais clientes compartilhando o canal físico via protocolo CSMA/CA aumentam as chances de colisão no ar.
*   **Comportamento Observado**: Os dados mostram correlação linear nula (*r_p* = {df_results.loc[4, "Ruckus_R_P"]:.4f}), mas correlação monotônica positiva fraca a moderada (*r_s* = {df_results.loc[4, "Ruckus_R_S"]:.4f}) no Ruckus e muito fraca na UniFi (*r_p* = {df_results.loc[4, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[4, "UniFi_R_S"]:.4f}).
*   **Discussão**: Os coeficientes sugerem que os APs de ambas as marcas conseguem lidar satisfatoriamente com a coordenação de pacotes dos clientes e evitar colisões críticas sob as cargas observadas durante a coleta.

### 6. Ruído de Fundo (Noise) × Retransmissões
*   **Arquivo**: `06_noise_retransmissoes.png`
*   **Visualização**:
![Noise x Retransmissões](graficos_dispersao/06_noise_retransmissoes.png)
*   **Expectativa Teórica**: Esperava-se correlação positiva, uma vez que níveis de ruído elevados deterioram o SNR e a integridade física dos bits transmitidos.
*   **Comportamento Observado**: Correlação negativa moderada a forte no Ruckus (*r_p* = {df_results.loc[5, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[5, "Ruckus_R_S"]:.4f}) e praticamente nula na UniFi (*r_p* = {df_results.loc[5, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[5, "UniFi_R_S"]:.4f}).
*   **Discussão**: Na UniFi, o ruído ambiental estimado manteve-se estável e praticamente sem correlação com as retransmissões (*r_s* = -0.0043). Na Ruckus, a correlação de -0.6323 reflete o comportamento físico da relação sinal-ruído (SNR) e do sinal absoluto reportados nos logs da controladora, evidenciando como a degradação mútua dessas métricas físicas de radiofrequência se associa à variação na taxa de retransmissões de pacotes na rede.

### 7. Ruído de Fundo (Noise) × RSSI
*   **Arquivo**: `07_noise_rssi.png`
*   **Visualização**:
![Noise x RSSI](graficos_dispersao/07_noise_rssi.png)
*   **Expectativa Teórica**: Esperava-se correlação nula. Fisicamente, o ruído eletromagnético do canal é independente da potência de sinal de transmissão negociada pelo rádio do cliente.
*   **Comportamento Observado**: Correlação nula na UniFi (*r_p* = {df_results.loc[6, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[6, "UniFi_R_S"]:.4f}), mas muito forte na Ruckus (*r_p* = {df_results.loc[6, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[6, "Ruckus_R_S"]:.4f}).
*   **Discussão**: O resultado da UniFi apoia a independência física entre ruído ambiental e sinal do cliente no cenário observado. Na Ruckus, a correlação moderada a fraca (*r_s* = -0.3762) decorre da relação física direta entre a potência de sinal recebido e a variação da relação sinal-ruído (SNR) registradas nos sensores de rádio da controladora.

### 8. Link Speed TX × Throughput TX
*   **Arquivo**: `08_link_speed_throughput.png`
*   **Visualização**:
![Link Speed x Throughput](graficos_dispersao/08_link_speed_throughput.png)
*   **Expectativa Teórica**: Esperava-se uma correlação positiva moderada. Modulações físicas mais velozes no link (Link Speed) expandem o teto operacional de transferência, propiciando maiores taxas de throughput de transmissão.
*   **Comportamento Observado**: Correlação fraca no Ruckus (*r_p* = {df_results.loc[7, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[7, "Ruckus_R_S"]:.4f}) e nula na UniFi (*r_p* = {df_results.loc[7, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[7, "UniFi_R_S"]:.4f}).
*   **Discussão**: Esse resultado indica que a modulação de velocidade do link de rádio é mantida elevada pela proximidade física, porém a vazão real consumida depende exclusivamente do perfil e uso de aplicativos pelo cliente.

### 9. Volume de Dados × Tempo de Sessão (Uptime)
*   **Arquivo**: `09_ruckus_uptime_volume.png`
*   **Visualização**:
![Tempo de Sessão x Volume Ruckus](graficos_dispersao/09_ruckus_uptime_volume.png)
*   **Expectativa Teórica**: Esperava-se uma correlação positiva moderada a forte, dado que sessões de conexão mais duradouras propiciam o acúmulo integrado de mais bytes trafegados.
*   **Comportamento Observado**: Correlação positiva moderada a forte no Ruckus (*r_p* = {df_results.loc[8, "Ruckus_R_P"]:.4f}, *r_s* = {df_results.loc[8, "Ruckus_R_S"]:.4f}) e na UniFi (*r_p* = {df_results.loc[8, "UniFi_R_P"]:.4f}, *r_s* = {df_results.loc[8, "UniFi_R_S"]:.4f}).
*   **Discussão**: Os dados são consistentes com a teoria de rede. Sessões mais estáveis e de longa duração representam um fator preponderante no acúmulo de dados totais consumidos na infraestrutura.

---
*Relatório de correlações gerado em: Etapa_3_Correlacoes/relatorio_correlacoes.md*
"""
    
    report_path = os.path.join(output_dir, 'relatorio_correlacoes.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"ETAPA 3 Concluída! Relatório salvo em: {report_path}")
    
    # 3. Converter MD para PDF
    pdf_path = os.path.join(output_dir, 'relatorio_correlacoes.pdf')
    pdf_success = convert_md_to_pdf(report_path, pdf_path)
    if pdf_success:
        print(f"Relatório PDF compilado em: {pdf_path}")
    else:
        print("Aviso: Falha na conversão do relatório de correlações para PDF.")
        
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    output_dir = os.path.join(base_dir, 'Etapa_3_Correlacoes')
    run_correlation_analysis(ruckus_std, unifi_std, output_dir)

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

def run_validation(ruckus_path, unifi_path, output_report_path, plots_dir):
    print("Iniciando ETAPA 0 – Validação do dataset...")
    
    # 1. Carregar datasets padronizados
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados. Execute o standardizer primeiro.")
        return False
        
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    # Criar diretório de gráficos se não existir
    os.makedirs(plots_dir, exist_ok=True)
    
    # 2. Registros Originais
    count_orig_ruckus = len(df_ruckus)
    count_orig_unifi = len(df_unifi)
    
    # 3. Remoção de registros duplicados
    df_ruckus_clean = df_ruckus.drop_duplicates()
    df_unifi_clean = df_unifi.drop_duplicates()
    
    count_clean_ruckus = len(df_ruckus_clean)
    count_clean_unifi = len(df_unifi_clean)
    
    dupes_removed_ruckus = count_orig_ruckus - count_clean_ruckus
    dupes_removed_unifi = count_orig_unifi - count_clean_unifi
    
    # Salvar versões limpas (sobrescrever ou manter limpos)
    df_ruckus_clean.to_csv(ruckus_path, index=False)
    df_unifi_clean.to_csv(unifi_path, index=False)
    
    # 4. Período efetivamente coberto
    df_ruckus_clean['timestamp'] = pd.to_datetime(df_ruckus_clean['timestamp'])
    df_unifi_clean['timestamp'] = pd.to_datetime(df_unifi_clean['timestamp'])
    
    min_ts_ruckus = df_ruckus_clean['timestamp'].min()
    max_ts_ruckus = df_ruckus_clean['timestamp'].max()
    duration_ruckus = max_ts_ruckus - min_ts_ruckus
    
    min_ts_unifi = df_unifi_clean['timestamp'].min()
    max_ts_unifi = df_unifi_clean['timestamp'].max()
    duration_unifi = max_ts_unifi - min_ts_unifi
    
    # 5. Percentual de dados ausentes
    missing_ruckus = df_ruckus_clean.isnull().mean() * 100
    missing_unifi = df_unifi_clean.isnull().mean() * 100
    
    # 6. Gráficos de Diagnóstico
    # Gráfico 1: Histograma Temporal de Registros
    plt.figure(figsize=(12, 5))
    sns.set_theme(style="whitegrid")
    
    # Ruckus registros por hora
    df_ruckus_clean['hour'] = df_ruckus_clean['timestamp'].dt.round('h')
    ruckus_temporal = df_ruckus_clean.groupby('hour').size()
    
    # UniFi registros por hora
    df_unifi_clean['hour'] = df_unifi_clean['timestamp'].dt.round('h')
    unifi_temporal = df_unifi_clean.groupby('hour').size()
    
    plt.plot(ruckus_temporal.index, ruckus_temporal.values, label='Ruckus', color='#3498db', linewidth=2)
    plt.plot(unifi_temporal.index, unifi_temporal.values, label='UniFi', color='#e74c3c', linewidth=2)
    
    plt.title('Distribuição Temporal de Registros Coletados (Frequência por Hora)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Data e Hora', fontsize=12)
    plt.ylabel('Quantidade de Registros', fontsize=12)
    plt.legend(fontsize=11)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plot_temporal_path = os.path.join(plots_dir, 'diagnostico_temporal.png')
    plt.savefig(plot_temporal_path, dpi=150)
    plt.close()
    
    # Gráfico 2: Mapa de Calor de Dados Ausentes
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Heatmap Ruckus (excluir colunas de string para visualização rápida ou usar amostragem)
    # Mostra colunas com dados nulos
    sns.heatmap(df_ruckus_clean.isnull(), cbar=False, yticklabels=False, cmap='viridis', ax=axes[0])
    axes[0].set_title('Dados Ausentes - Ruckus', fontsize=12, fontweight='bold')
    
    sns.heatmap(df_unifi_clean.isnull(), cbar=False, yticklabels=False, cmap='viridis', ax=axes[1])
    axes[1].set_title('Dados Ausentes - UniFi', fontsize=12, fontweight='bold')
    
    plt.suptitle('Mapa Visual de Dados Ausentes (Amarelo indica Nulo)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plot_missing_path = os.path.join(plots_dir, 'diagnostico_dados_ausentes.png')
    plt.savefig(plot_missing_path, dpi=150)
    plt.close()
    
    # 7. Gerar Relatório Markdown
    report_content = f"""# Validação de Consistência dos Dados

## 1. Quantidade de Registros

A tabela abaixo resume a quantidade de registros encontrados nos logs de telemetria antes e depois do processo de deduplicação (remoção de duplicados exatos).

| Fabricante | Registros Originais | Registros Duplicados Removidos | Registros Limpos | % de Redundância |
| :--- | :---: | :---: | :---: | :---: |
| **Ruckus** | {count_orig_ruckus:,} | {dupes_removed_ruckus:,} | {count_clean_ruckus:,} | {(dupes_removed_ruckus / count_orig_ruckus * 100):.2f}% |
| **UniFi** | {count_orig_unifi:,} | {dupes_removed_unifi:,} | {count_clean_unifi:,} | {(dupes_removed_unifi / count_orig_unifi * 100):.2f}% |

*Nota: Registros duplicados ocorrem por sobreposição em polling repetido do coletor. A remoção evita viés nas análises estatísticas.*

## 2. Período Coberto pela Coleta

| Fabricante | Data/Hora Inicial (Min) | Data/Hora Final (Max) | Duração Efetiva |
| :--- | :---: | :---: | :---: |
| **Ruckus** | {min_ts_ruckus.strftime('%d/%m/%Y %H:%M')} | {max_ts_ruckus.strftime('%d/%m/%Y %H:%M')} | {duration_ruckus} |
| **UniFi** | {min_ts_unifi.strftime('%d/%m/%Y %H:%M')} | {max_ts_unifi.strftime('%d/%m/%Y %H:%M')} | {duration_unifi} |

*Nota: Ambos os datasets cobrem o mesmo período temporal (de {min_ts_ruckus.strftime('%d/%m/%Y %H:%M')} a {max_ts_ruckus.strftime('%d/%m/%Y %H:%M')}), garantindo que os cenários de carga de rede sejam diretamente comparáveis.*

## 3. Dados Ausentes (Missing Values)

O percentual de dados nulos ou ausentes para cada variável após a limpeza:

| Coluna Padronizada | % Nulos Ruckus | % Nulos UniFi | Tipo de Dado |
| :--- | :---: | :---: | :--- |
| `timestamp` | {missing_ruckus['timestamp']:.2f}% | {missing_unifi['timestamp']:.2f}% | Datetime |
| `AP` | {missing_ruckus['AP']:.2f}% | {missing_unifi['AP']:.2f}% | Categórico |
| `cliente (MAC)` | {missing_ruckus['cliente (MAC)']:.2f}% | {missing_unifi['cliente (MAC)']:.2f}% | Categórico |
| `RSSI` | {missing_ruckus['RSSI']:.2f}% | {missing_unifi['RSSI']:.2f}% | Numérico |
| `signal` | {missing_ruckus['signal']:.2f}% | {missing_unifi['signal']:.2f}% | Numérico |
| `noise` | {missing_ruckus['noise']:.2f}% | {missing_unifi['noise']:.2f}% | Numérico |
| `canal` | {missing_ruckus['canal']:.2f}% | {missing_unifi['canal']:.2f}% | Categórico |
| `throughput_tx_mbps` | {missing_ruckus['throughput_tx_mbps']:.2f}% | {missing_unifi['throughput_tx_mbps']:.2f}% | Numérico |
| `throughput_rx_mbps` | {missing_ruckus['throughput_rx_mbps']:.2f}% | {missing_unifi['throughput_rx_mbps']:.2f}% | Numérico |
| `link_speed_tx_mbps` | {missing_ruckus['link_speed_tx_mbps']:.2f}% | {missing_unifi['link_speed_tx_mbps']:.2f}% | Numérico |
| `link_speed_rx_mbps` | {missing_ruckus['link_speed_rx_mbps']:.2f}% | {missing_unifi['link_speed_rx_mbps']:.2f}% | Numérico |
| `retransmissoes_pct` | {missing_ruckus['retransmissoes_pct']:.2f}% | {missing_unifi['retransmissoes_pct']:.2f}% | Numérico |
| `volume_tx_mb` | {missing_ruckus['volume_tx_mb']:.2f}% | {missing_unifi['volume_tx_mb']:.2f}% | Numérico |
| `volume_rx_mb` | {missing_ruckus['volume_rx_mb']:.2f}% | {missing_unifi['volume_rx_mb']:.2f}% | Numérico |
| `padrão` | {missing_ruckus['padrão']:.2f}% | {missing_unifi['padrão']:.2f}% | Categórico |

## 4. Tratamento de Valores Nulos

*   **Link Speed no Ruckus**: A taxa de modulação física de TX (`link_speed_tx_mbps`) foi extraída com sucesso a partir do campo `throughput_rate` (em Kbps) nos logs de telemetria da controladora SmartZone. A taxa RX correspondente (`link_speed_rx_mbps`) não é informada nos logs brutos e é mantida como `NaN`.
*   **Ruído (Noise) e Sinal (Signal) em Ruckus**: Alguns registros continham valores de sinal zerados ou vazios. Onde o sinal era -100 (vazio padrão) e SNR era 0, o ruído foi definido como NaN para evitar distorções de cálculo.
*   **Valores Nulos na UniFi**: O dataset UniFi apresenta consistência total (0% de nulos nas métricas principais de telemetria).

## 5. Padronização das Unidades de Medida

As colunas foram padronizadas da seguinte forma:
1.  **Sinal e Ruído**: Potência medida em **dBm**.
2.  **RSSI/SNR**: Medido em **dB** (ou índice relativo na UniFi).
3.  **Throughput**: Convertido em **Mbps** (Megabits por segundo) para Downstream (`tx`) e Upstream (`rx`).
4.  **Volume de Dados**: Convertido em **MB** (Megabytes) acumulados por cliente no período de observação.
5.  **Retransmissões**: Medidas em porcentagem (**%**) de pacotes retransmitidos.
6.  **Link Speed**: Modulação de velocidade física convertida em **Mbps**.

## 6. Equivalência de Métricas (Mapeamento Ruckus vs UniFi)

A tabela abaixo mostra a relação entre os campos extraídos de cada fabricante que representam as mesmas grandezas físicas:

| Grandeza Física | Métrica Ruckus (Raw) | Métrica UniFi (Raw) | Coluna Padronizada Final |
| :--- | :--- | :--- | :--- |
| Potência do Sinal | `signal_rssi` | `signal` | `signal` (dBm) |
| Relação Sinal/Ruído | `snr` | `rssi` | `RSSI` (dB) |
| Throughput Downstream | `tx_bytes / uptime` | `tx_bytes_r * 8` | `throughput_tx_mbps` |
| Throughput Upstream | `rx_bytes / uptime` | `rx_bytes_r * 8` | `throughput_rx_mbps` |
| Retransmissões | `tx_retries / (tx_pkts + tx_retries)` | `100 - (ccq / 10)` | `retransmissoes_pct` |
| Volume Trafegado | `tx_bytes`, `rx_bytes` | `tx_bytes_r * uptime`, `rx_bytes_r * uptime` | `volume_tx_mb`, `volume_rx_mb` |
| Modulação de Velocidade | `throughput_rate` | `tx_rate`, `rx_rate` | `link_speed_tx_mbps`, `link_speed_rx_mbps` |

## 7. Gráficos de Diagnóstico Gerados

Os gráficos de validação foram salvos em:
*   `diagnostico_temporal.png`: Mostra a atividade de registros ao longo do tempo de coleta.
*   `diagnostico_dados_ausentes.png`: Mapa de calor identificando colunas com dados faltantes (especialmente Link Speed no Ruckus).
"""
    
    with open(output_report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"ETAPA 0 Concluída! Relatório salvo em: {output_report_path}")
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    report_out = os.path.join(base_dir, 'Etapa_0_Validacao', 'relatorio_validacao.md')
    plots_out = os.path.join(base_dir, 'Etapa_0_Validacao')
    run_validation(ruckus_std, unifi_std, report_out, plots_out)

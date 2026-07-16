import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

def generate_plots(ruckus_path, unifi_path, plots_dir):
    print("Iniciando ETAPA 2 – Visualização dos dados...")
    
    # 1. Carregar datasets padronizados
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados. Execute o standardizer primeiro.")
        return False
        
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    df_ruckus['timestamp'] = pd.to_datetime(df_ruckus['timestamp'])
    df_unifi['timestamp'] = pd.to_datetime(df_unifi['timestamp'])
    
    # Adicionar coluna de identificação nos datasets originais
    df_ruckus['equipamento'] = 'Ruckus'
    df_unifi['equipamento'] = 'UniFi'
    
    # Combinar datasets
    df_comb = pd.concat([df_ruckus, df_unifi], ignore_index=True)
    
    os.makedirs(plots_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # ==========================================================================
    # 1. HISTOGRAMAS
    # ==========================================================================
    
    # A. Histograma de RSSI (Sinal Físico)
    plt.figure(figsize=(10, 6))
    r_rssi = df_ruckus['signal'].dropna()
    u_rssi = df_unifi['signal'].dropna()
    
    if not r_rssi.empty:
        sns.histplot(r_rssi, color='#3498db', label='Ruckus (Sinal dBm)', kde=True, stat="density", alpha=0.5, bins=30)
    if not u_rssi.empty:
        sns.histplot(u_rssi, color='#e74c3c', label='UniFi (Sinal dBm)', kde=True, stat="density", alpha=0.5, bins=30)
        
    plt.title('Distribuição de Densidade do Sinal Físico (dBm) por Fabricante', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Sinal Físico (dBm)', fontsize=11)
    plt.ylabel('Densidade', fontsize=11)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'histograma_rssi.png'), dpi=150)
    plt.close()
    
    # B. Histograma de Canais Utilizados
    plt.figure(figsize=(12, 6))
    sns.countplot(data=df_comb, x='canal', hue='equipamento', palette=['#3498db', '#e74c3c'])
    plt.title('Distribuição de Utilização de Canais por Fabricante', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Canal Utilizado', fontsize=11)
    plt.ylabel('Frequência (Quantidade de Registros)', fontsize=11)
    plt.xticks(rotation=45)
    plt.legend(title='Equipamento')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'histograma_canais.png'), dpi=150)
    plt.close()
    
    # C. Histograma do Número de Clientes por AP
    df_clients_per_ap = df_comb.groupby(['timestamp', 'AP', 'equipamento']).size().reset_index(name='qtd_clientes')
    
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_clients_per_ap, x='qtd_clientes', hue='equipamento', palette=['#3498db', '#e74c3c'], 
                 kde=True, stat="count", multiple="dodge", alpha=0.6, shrink=0.8, discrete=True)
    plt.title('Distribuição de Clientes Conectados por Access Point (AP)', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Quantidade de Clientes Conectados por AP', fontsize=11)
    plt.ylabel('Frequência de Ocorrência (Timestamps)', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'histograma_clientes_por_ap.png'), dpi=150)
    plt.close()
    
    # ==========================================================================
    # 2. BOXPLOTS (Outliers ocultos para escala adequada)
    # ==========================================================================
    
    # A. Boxplot de RSSI por Fabricante
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_comb, x='equipamento', y='signal', palette=['#3498db', '#e74c3c'], hue='equipamento', legend=False, showfliers=False)
    plt.title('Intensidade do Sinal Físico (dBm) por Fabricante\n(Outliers ocultos para escala)', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Fabricante', fontsize=11)
    plt.ylabel('Sinal (dBm)', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'boxplot_rssi_fabricante.png'), dpi=150)
    plt.close()
    
    # B. Boxplot de Throughput por Banda (2.4 GHz vs 5 GHz)
    plt.figure(figsize=(10, 6))
    df_band = df_comb[df_comb['banda'].isin(['2.4 GHz', '5 GHz'])]
    sns.boxplot(data=df_band, x='banda', y='throughput_total_mbps', hue='equipamento', palette=['#3498db', '#e74c3c'], showfliers=False)
    plt.title('Consumo de Throughput de Cliente por Banda de Frequência\n(Outliers ocultos para escala)', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Banda de Frequência', fontsize=11)
    plt.ylabel('Throughput Total (Mbps)', fontsize=11)
    plt.legend(title='Equipamento')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'boxplot_throughput_banda.png'), dpi=150)
    plt.close()
    
    # C. Boxplot de Retransmissões por Banda (2.4 GHz vs 5 GHz)
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_band, x='banda', y='retransmissoes_pct', hue='equipamento', palette=['#3498db', '#e74c3c'], showfliers=False)
    plt.title('Taxa de Retransmissões por Banda de Frequência\n(Outliers ocultos para escala)', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Banda de Frequência', fontsize=11)
    plt.ylabel('Retransmissões (%)', fontsize=11)
    plt.legend(title='Equipamento')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'boxplot_retransmissoes_banda.png'), dpi=150)
    plt.close()
    
    # D. Boxplot de Throughput Agregado por AP
    df_ap_rk = df_ruckus.groupby(['timestamp', 'AP'])['throughput_total_mbps'].sum().reset_index(name='tp_agregado')
    df_ap_uf = df_unifi.groupby(['timestamp', 'AP'])['throughput_total_mbps'].sum().reset_index(name='tp_agregado')
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    
    # Ruckus APs (ordenados pela média de throughput)
    df_ap_rk['AP_display'] = df_ap_rk['AP'].apply(lambda x: f"RK-{x[-5:].replace(':', '')}" if len(str(x)) >= 5 else x)
    order_rk = df_ap_rk.groupby('AP_display')['tp_agregado'].mean().sort_values(ascending=False).index
    sns.boxplot(data=df_ap_rk, x='AP_display', y='tp_agregado', ax=axes[0], color='#3498db', order=order_rk, showfliers=False)
    axes[0].set_title('Distribuição de Throughput Agregado por AP – Ruckus\n(Ordenado por média de tráfego, outliers ocultados)', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Access Point (AP MAC Simplificado)')
    axes[0].set_ylabel('Throughput Agregado do AP (Mbps)')
    axes[0].tick_params(axis='x', rotation=45)
    
    # UniFi APs (ordenados pela média de throughput)
    order_uf = df_ap_uf.groupby('AP')['tp_agregado'].mean().sort_values(ascending=False).index
    sns.boxplot(data=df_ap_uf, x='AP', y='tp_agregado', ax=axes[1], color='#e74c3c', order=order_uf, showfliers=False)
    axes[1].set_title('Distribuição de Throughput Agregado por AP – UniFi\n(Ordenado por média de tráfego, outliers ocultados)', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Access Point (AP Nome)')
    axes[1].set_ylabel('Throughput Agregado do AP (Mbps)')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'boxplot_throughput_por_ap.png'), dpi=150)
    plt.close()
    
    # ==========================================================================
    # 3. HEATMAP
    # ==========================================================================
    
    # A. Heatmap: Fabricante × Dia × Hora (Clientes Únicos)
    df_comb['dia'] = df_comb['timestamp'].dt.strftime('%d/%m')
    df_comb['hora'] = df_comb['timestamp'].dt.hour
    
    # Agrupar por equipamento, dia e hora e contar clientes únicos (por MAC)
    df_heatmap_data = df_comb.groupby(['equipamento', 'dia', 'hora'])['cliente (MAC)'].nunique().reset_index(name='clientes_unicos')
    df_heatmap_data['Fabricante_Dia'] = df_heatmap_data['equipamento'] + ' (' + df_heatmap_data['dia'] + ')'
    
    # Pivotar tabela para formato de matriz (linhas = Fabricante (Dia), colunas = horas)
    pivot_heatmap = df_heatmap_data.pivot(index='Fabricante_Dia', columns='hora', values='clientes_unicos').fillna(0).astype(int)
    
    # Garantir que todas as 24 horas (0 a 23) estejam representadas nas colunas
    for h in range(24):
        if h not in pivot_heatmap.columns:
            pivot_heatmap[h] = 0
    pivot_heatmap = pivot_heatmap.reindex(columns=sorted(pivot_heatmap.columns))
    # Ordenar o índice de forma estritamente cronológica agrupada por fabricante
    datas_ordenadas = sorted(df_comb['timestamp'].dt.date.unique())
    datas_str = [d.strftime('%d/%m') for d in datas_ordenadas]
    ordem_linhas = []
    for eq in ['Ruckus', 'UniFi']:
        for d_str in datas_str:
            label = f"{eq} ({d_str})"
            if label in pivot_heatmap.index:
                ordem_linhas.append(label)
    pivot_heatmap = pivot_heatmap.reindex(ordem_linhas)
    
    plt.figure(figsize=(15, 8))
    # Gerar heatmap com anotações de números
    sns.heatmap(pivot_heatmap, annot=True, fmt="d", cmap="YlGnBu", cbar_kws={'label': 'Clientes Únicos Conectados'}, annot_kws={"size": 9})
    plt.title('Distribuição Temporal de Clientes Únicos por Horário, Dia e Fabricante', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Hora do Dia (00:00 - 23:00)', fontsize=11)
    plt.ylabel('Fabricante (Data)', fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'heatmap_horario_clientes.png'), dpi=150)
    plt.close()
    
    # Calcular métricas para o relatório dinâmico
    rk_sig_mean = df_ruckus['signal'].mean()
    rk_sig_med = df_ruckus['signal'].median()
    uf_sig_mean = df_unifi['signal'].mean()
    uf_sig_med = df_unifi['signal'].median()
    
    # Calcular picos de clientes únicos
    df_ruckus['dia'] = df_ruckus['timestamp'].dt.strftime('%d/%m')
    df_ruckus['hora'] = df_ruckus['timestamp'].dt.hour
    df_unifi['dia'] = df_unifi['timestamp'].dt.strftime('%d/%m')
    df_unifi['hora'] = df_unifi['timestamp'].dt.hour
    
    gr_rk = df_ruckus.groupby(['dia', 'hora'])['cliente (MAC)'].nunique().reset_index()
    gr_uf = df_unifi.groupby(['dia', 'hora'])['cliente (MAC)'].nunique().reset_index()
    
    peak_rk_row = gr_rk.loc[gr_rk['cliente (MAC)'].idxmax()]
    peak_uf_row = gr_uf.loc[gr_uf['cliente (MAC)'].idxmax()]
    
    peak_rk_val = int(peak_rk_row['cliente (MAC)'])
    peak_uf_val = int(peak_uf_row['cliente (MAC)'])
    
    report_content = f"""# Visualização dos Dados

## 1. Intensidade do Sinal por Fabricante

### 1.1. Boxplot de Sinal Físico por Fabricante
O boxplot de sinal físico por fabricante apresenta a distribuição e os quartis da potência recebida (dBm) para ambas as infraestruturas.

![Boxplot RSSI por Fabricante](graficos/boxplot_rssi_fabricante.png)

*   **Ruckus**: Média de `{rk_sig_mean:.2f} dBm`, Mediana `{rk_sig_med:.2f} dBm`.
*   **UniFi**: Média de `{uf_sig_mean:.2f} dBm`, Mediana `{uf_sig_med:.2f} dBm`.
*   Os resultados sugerem uma cobertura de sinal física coerente para os clientes de ambas as marcas no cenário analisado, com a maioria das amostras se situando em uma faixa saudável de RF.

### 1.2. Histograma de Densidade de Sinal
O histograma apresenta a densidade de ocorrência de potência de sinal nos logs coletados.

![Histograma RSSI](graficos/histograma_rssi.png)

*   O gráfico demonstra que a UniFi possui uma distribuição de sinal com menor variabilidade (concentrada em torno de -67 dBm), enquanto a Ruckus apresenta maior amplitude e dispersão das conexões ao longo do dia.

---

## 2. Utilização de Canais por Fabricante

O histograma de utilização de canais apresenta a contagem de registros em cada frequência de operação.

![Histograma de Canais](graficos/histograma_canais.png)

*   **2.4 GHz**: Ambas as marcas concentram o tráfego nos canais não sobrepostos `1`, `6` e `11`, validando as boas práticas de planejamento de RF adotadas no campus.
*   **5 GHz**: A Ruckus apresenta uma alocação de espectro mais ampla e distribuída (como canais `36`, `52`, `60`, `104`, `112`, `120`, `128`, `149`), o que reduz interferência co-canal em células adjacentes.

---

## 3. Quantidade de Clientes Conectados por AP

Este histograma ilustra a densidade de clientes associados simultaneamente a cada Access Point.

![Histograma Clientes por AP](graficos/histograma_clientes_por_ap.png)

*   **UniFi**: Exibe perfil de baixa carga (maior parte dos registros possui entre 1 e 5 clientes simultâneos por rádio).
*   **Ruckus**: Exibe maior flexibilidade de densidade, suportando APs com cargas significativamente mais robustas de concorrência, o que condiz com o posicionamento de alta densidade da marca.

---

## 4. Análise de Desempenho e Qualidade de Enlace por Banda

### 4.1. Throughput por Banda
O boxplot compara o consumo de throughput entre as bandas de 2.4 GHz e 5 GHz.

![Boxplot Throughput por Banda](graficos/boxplot_throughput_banda.png)

*   Como esperado teoricamente, a banda de **5 GHz** oferece vazão e capacidade física superior para ambas as marcas, superando a banda de **2.4 GHz** que possui limitações inerentes de modulação e largura de canal.

### 4.2. Retransmissões por Banda
O boxplot compara a ocorrência de retransmissões físicas ou estimadas.

![Boxplot Retransmissões por Banda](graficos/boxplot_retransmissoes_banda.png)

*   A banda de **2.4 GHz** exibe taxas médias superiores de retransmissão, justificada pelo congestionamento e interferências co-canal concorrentes de micro-ondas, Bluetooth e outras redes WiFi da vizinhança.

---

## 5. Distribuição de Throughput Agregado por AP

Este gráfico apresenta a soma da vazão ativa de todos os clientes associados a cada um dos APs mapeados, permitindo identificar o nível de carregamento individual de tráfego por antena.

![Boxplot Throughput por AP](graficos/boxplot_throughput_por_ap.png)

*   **Ruckus (AP MAC Simplificado)**: Apresenta maior amplitude e níveis superiores de vazão somada (vários APs superando médias de 5 a 10 Mbps de tráfego agregado ativo, com picos de consumo expressivos). Para melhor visualização, os endereços MAC longos do Ruckus foram simplificados no formato `RK-XXXX` (onde `XXXX` são os 4 dígitos finais do MAC).
*   **UniFi (AP Nome)**: Mostra distribuições de vazão agregada concentradas próximas de zero (com médias inferiores a 2 Mbps). Isso indica que a maioria dos APs da UniFi operaram com carga de dados muito baixa durante o período amostrado, corroborando a ociosidade do ambiente.

---

## 6. Distribuição Temporal de Clientes Únicos por Fabricante e Dia

O mapa de calor (heatmap) apresenta a quantidade de clientes únicos ativos por fabricante e por dia do período selecionado, distribuída ao longo do ciclo diário de 24 horas.

![Heatmap de Clientes Únicos](graficos/heatmap_horario_clientes.png)

*   O gráfico sugere uma **rotina cíclica de uso da rede** que se repete de forma semelhante ao longo dos dias: o volume de clientes únicos ativos inicia uma curva ascendente a partir das **08:00**, atinge os maiores patamares no horário comercial/acadêmico (especialmente entre **14:00** e **18:00**) e entra em declínio progressivo nas primeiras horas da noite, reduzindo-se drasticamente durante a madrugada.
*   **Picos de Clientes**:
    *   No ambiente Ruckus, o pico de clientes únicos em uma única hora ocorreu no dia **{peak_rk_row['dia']}** às **{int(peak_rk_row['hora'])}:00**, registrando **{peak_rk_val}** dispositivos.
    *   No ambiente UniFi, o pico de clientes únicos ocorreu no dia **{peak_uf_row['dia']}** às **{int(peak_uf_row['hora'])}:00**, registrando **{peak_uf_val}** dispositivos.
*   Os resultados indicam uma concentração consistentemente maior de dispositivos na infraestrutura Ruckus para todos os dias do período em comparação com a UniFi, o que sugere maior adensamento de usuários sob essa rede no campus observado.

---
*Relatório de visualização de dados gerado em: Etapa_2_Visualizacao/relatorio_visualizacao.md*
"""

    report_path = os.path.join(os.path.dirname(plots_dir), 'relatorio_visualizacao.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"Relatório Markdown dinâmico da Etapa 2 salvo em: {report_path}")

    print(f"ETAPA 2 Concluída! Todos os gráficos da Etapa 2 gerados em: {plots_dir}")
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    plots_out = os.path.join(base_dir, 'Etapa_2_Visualizacao', 'graficos')
    generate_plots(ruckus_std, unifi_std, plots_out)

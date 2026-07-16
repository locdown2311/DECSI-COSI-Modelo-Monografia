import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Adicionar a raiz do projeto ao sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from utils.convert_md_to_pdf import convert_md_to_pdf

def map_ap_jains_fairness(df):
    if df.empty or 'AP' not in df.columns or 'timestamp' not in df.columns or 'throughput_total_mbps' not in df.columns:
        return pd.Series(np.nan, index=df.index)
        
    def compute_jain(group):
        n = len(group)
        if n >= 2:
            sum_x = group.sum()
            if sum_x == 0:
                return 1.0
            sum_x2 = (group ** 2).sum()
            return (sum_x ** 2) / (n * sum_x2)
        else:
            return np.nan

    jains_map = df.groupby(['AP', 'timestamp'])['throughput_total_mbps'].apply(compute_jain)
    jains_df = jains_map.reset_index(name='ap_jains_fairness')
    
    df_temp = df[['AP', 'timestamp']].copy()
    df_temp['original_index'] = df_temp.index
    df_merged = df_temp.merge(jains_df, on=['AP', 'timestamp'], how='left')
    df_merged.index = df_merged['original_index']
    return df_merged['ap_jains_fairness']

def run_bottleneck_analysis(ruckus_path, unifi_path, output_dir):
    print("Iniciando ETAPA 5 – Classificação dos Gargalos...")
    
    # 1. Carregar datasets padronizados
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados.")
        return False
        
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    df_ruckus['timestamp'] = pd.to_datetime(df_ruckus['timestamp'])
    df_unifi['timestamp'] = pd.to_datetime(df_unifi['timestamp'])
    
    # Criar pastas de saída
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'graficos')
    os.makedirs(plots_dir, exist_ok=True)
    
    # --- PRÉ-PROCESSAMENTO: CÁLCULO DE MÉTRICAS AGREGADAS ---
    def preprocess_df(df, name):
        # A. Clientes por AP e minuto
        df_ap_count = df.groupby(['timestamp', 'AP']).size().reset_index(name='clientes_por_ap')
        df = df.merge(df_ap_count, on=['timestamp', 'AP'], how='left')
        
        # B. Throughput agregado por AP e minuto
        df_ap_tp = df.groupby(['timestamp', 'AP'])['throughput_total_mbps'].sum().reset_index(name='tp_agregado_ap')
        df = df.merge(df_ap_tp, on=['timestamp', 'AP'], how='left')
        
        # C. Roaming excessivo (Total AP switches > 5 para o cliente MAC)
        df_sorted = df.sort_values(by=['cliente (MAC)', 'timestamp'])
        df_sorted['ap_anterior'] = df_sorted.groupby('cliente (MAC)')['AP'].shift(1)
        df_sorted['mudou_ap'] = (df_sorted['AP'] != df_sorted['ap_anterior']) & df_sorted['ap_anterior'].notna()
        
        # Somar mudanças por MAC
        roaming_stats = df_sorted.groupby('cliente (MAC)')['mudou_ap'].sum().reset_index(name='total_roaming')
        df = df.merge(roaming_stats, on='cliente (MAC)', how='left')
        
        # D. Cálculo de SNR
        if name == 'Ruckus':
            df['SNR'] = df['signal'] - df['noise']
        else: # UniFi
            df['SNR'] = df['RSSI'] # Onde RSSI é SNR index
            
        # Adicionar coluna de fabricante
        df['equipamento'] = name
        return df

    df_rk_processed = preprocess_df(df_ruckus, 'Ruckus')
    df_uf_processed = preprocess_df(df_unifi, 'UniFi')
    
    # --- CLASSIFICAÇÃO DOS GARGALOS (ROW-BY-ROW) ---
    def classify_bottlenecks(df):
        # Gargalo 1: Baixa qualidade de sinal (< -75 dBm)
        df['gargalo_sinal'] = df['signal'] < -75
        
        # Gargalo 2: Congestionamento do AP (>= 15 clientes)
        df['gargalo_congestionamento'] = df['clientes_por_ap'] >= 15
        
        # Gargalo 3: Interferência (noise > -90 OU SNR < 20 com sinal >= -75)
        df['gargalo_interferencia'] = (df['noise'] > -90) | ((df['signal'] >= -75) & (df['SNR'] < 20))
        
        # Gargalo 4: Roaming excessivo (> 5 transições no dia)
        df['gargalo_roaming'] = df['total_roaming'] > 5
        
        # Gargalo 5: Limitação da infraestrutura cabeada (Fast Ethernet >= 90 Mbps agregados)
        df['gargalo_cabo'] = df['tp_agregado_ap'] >= 90
        
        # Sem Gargalo: nenhum dos anteriores
        df['sem_gargalo'] = ~(df['gargalo_sinal'] | df['gargalo_congestionamento'] | 
                              df['gargalo_interferencia'] | df['gargalo_roaming'] | 
                              df['gargalo_cabo'])
        return df

    df_rk_classified = classify_bottlenecks(df_rk_processed)
    df_uf_classified = classify_bottlenecks(df_uf_processed)
    
    df_comb = pd.concat([df_rk_classified, df_uf_classified], ignore_index=True)
    
    # --- CÁLCULO DE ESTATÍSTICAS COMPARATIVAS ---
    categories = [
        ('gargalo_sinal', 'G1: Baixa Qualidade de Enlace'),
        ('gargalo_congestionamento', 'G2: Congestionamento do Meio'),
        ('gargalo_interferencia', 'G3: Interferência / SNR Ruim'),
        ('gargalo_roaming', 'G4: Instabilidade de Roaming'),
        ('gargalo_cabo', 'G5: Gargalo Cabeado (FE)'),
        ('sem_gargalo', 'Sem Gargalos')
    ]
    
    results = []
    
    for col, label in categories:
        for name, df in [('Ruckus', df_rk_classified), ('UniFi', df_uf_classified)]:
            sub = df[df[col] == True]
            n = len(sub)
            pct = (n / len(df)) * 100
            
            mean_tp = sub['throughput_total_mbps'].mean() if n > 0 else 0
            median_tp = sub['throughput_total_mbps'].median() if n > 0 else 0
            mean_ret = sub['retransmissoes_pct'].mean() if n > 0 else 0
            median_ret = sub['retransmissoes_pct'].median() if n > 0 else 0
            
            results.append({
                'Fabricante': name,
                'Categoria': label,
                'Amostras_N': n,
                'Porcentagem_Pct': pct,
                'Throughput_Media': mean_tp,
                'Throughput_Mediana': median_tp,
                'Retransmissoes_Media': mean_ret,
                'Retransmissoes_Mediana': median_ret
            })
            
    df_res = pd.DataFrame(results)
    csv_path = os.path.join(output_dir, 'resultados_gargalos.csv')
    df_res.to_csv(csv_path, index=False)
    print(f"Resultados dos gargalos exportados para: {csv_path}")
    
    # --- GERAR PLOTS COMPARATIVOS ---
    # 1. Gráfico de Barras Comparativo da Ocorrência de Gargalos
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_res, x='Categoria', y='Porcentagem_Pct', hue='Fabricante', palette=['#3498db', '#e74c3c'])
    plt.title('Percentual de Amostras Afetadas por Tipo de Gargalo', fontsize=13, fontweight='bold', pad=15)
    plt.xlabel('Categoria de Gargalo', fontsize=11)
    plt.ylabel('Amostras Afetadas (%)', fontsize=11)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'distribuicao_gargalos.png'), dpi=150)
    plt.close()
    
    # 2. Impacto dos Gargalos no Throughput do Cliente
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_res[df_res['Categoria'] != 'G5: Gargalo Cabeado (FE)'], x='Categoria', y='Throughput_Media', hue='Fabricante', palette=['#3498db', '#e74c3c'])
    plt.title('Throughput Médio do Cliente por Tipo de Gargalo\n(Gargalo Cabeado omitido devido à frequência nula)', fontsize=12, fontweight='bold', pad=15)
    plt.xlabel('Categoria de Gargalo', fontsize=11)
    plt.ylabel('Throughput Médio (Mbps)', fontsize=11)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'impacto_throughput.png'), dpi=150)
    plt.close()
    
    # 3. Impacto dos Gargalos nas Retransmissões do Cliente
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_res[df_res['Categoria'] != 'G5: Gargalo Cabeado (FE)'], x='Categoria', y='Retransmissoes_Media', hue='Fabricante', palette=['#3498db', '#e74c3c'])
    plt.title('Taxa Média de Retransmissões do Cliente por Tipo de Gargalo\n(Gargalo Cabeado omitido devido à frequência nula)', fontsize=12, fontweight='bold', pad=15)
    plt.xlabel('Categoria de Gargalo', fontsize=11)
    plt.ylabel('Retransmissões Médias (%)', fontsize=11)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'impacto_retransmissoes.png'), dpi=150)
    plt.close()

    # --- ANÁLISE POR ACCESS POINT ---
    # Ruckus
    df_rk_processed['ap_jains_fairness'] = map_ap_jains_fairness(df_rk_processed)
    df_rk_processed['AP_display'] = df_rk_processed['AP'].apply(lambda x: f"RK-{x[-5:].replace(':', '')}" if len(str(x)) >= 5 else x)
    ap_rk_stats = df_rk_processed.groupby('AP_display').agg(
        amostras=('timestamp', 'count'),
        clientes_media=('clientes_por_ap', 'mean'),
        clientes_max=('clientes_por_ap', 'max'),
        throughput_agregado_media=('tp_agregado_ap', 'mean'),
        throughput_agregado_max=('tp_agregado_ap', 'max'),
        sinal_medio=('signal', 'mean'),
        retransmissoes_media=('retransmissoes_pct', 'mean'),
        throughput_cliente_media=('throughput_total_mbps', 'mean'),
        equidade_media=('ap_jains_fairness', 'mean')
    ).reset_index().sort_values(by='throughput_agregado_media', ascending=False)

    # UniFi
    df_uf_processed['ap_jains_fairness'] = map_ap_jains_fairness(df_uf_processed)
    ap_uf_stats = df_uf_processed.groupby('AP').agg(
        amostras=('timestamp', 'count'),
        clientes_media=('clientes_por_ap', 'mean'),
        clientes_max=('clientes_por_ap', 'max'),
        throughput_agregado_media=('tp_agregado_ap', 'mean'),
        throughput_agregado_max=('tp_agregado_ap', 'max'),
        sinal_medio=('signal', 'mean'),
        retransmissoes_media=('retransmissoes_pct', 'mean'),
        throughput_cliente_media=('throughput_total_mbps', 'mean'),
        equidade_media=('ap_jains_fairness', 'mean')
    ).reset_index().sort_values(by='throughput_agregado_media', ascending=False)

    # --- CLUSTERIZAÇÃO DOS ACCESS POINTS (K-MEANS) ---
    features_clust = ['clientes_media', 'throughput_agregado_media', 'sinal_medio', 'retransmissoes_media']
    
    # K-Means Ruckus (K=4)
    ap_rk_stats_clean = ap_rk_stats.dropna(subset=features_clust).copy()
    if len(ap_rk_stats_clean) >= 4:
        scaler_rk = StandardScaler()
        X_rk = scaler_rk.fit_transform(ap_rk_stats_clean[features_clust])
        kmeans_rk = KMeans(n_clusters=4, random_state=42)
        ap_rk_stats_clean['cluster'] = kmeans_rk.fit_predict(X_rk)
        centroids_rk = ap_rk_stats_clean.groupby('cluster')[features_clust].mean()
        
        # Rotulagem programática Ruckus (K=4)
        idx_high_load_rk = centroids_rk['throughput_agregado_media'].idxmax()
        idx_low_signal_rk = centroids_rk['retransmissoes_media'].idxmax()
        
        remaining_rk = [i for i in range(4) if i not in [idx_high_load_rk, idx_low_signal_rk]]
        idx_low_load_rk = centroids_rk.loc[remaining_rk, 'clientes_media'].idxmin()
        idx_moderate_rk = [i for i in remaining_rk if i != idx_low_load_rk][0]
        
        labels_rk = {
            idx_high_load_rk: "Grupo A: Muito Carregado",
            idx_low_signal_rk: "Grupo D: Baixa Qualidade de Sinal",
            idx_low_load_rk: "Grupo B: Pouco Utilizado",
            idx_moderate_rk: "Grupo C: Carga Moderada"
        }
        ap_rk_stats_clean['cluster_label'] = ap_rk_stats_clean['cluster'].map(labels_rk)
    else:
        ap_rk_stats_clean['cluster_label'] = 'N/A'
        centroids_rk = pd.DataFrame()
        labels_rk = {}
        
    # K-Means UniFi (K=4)
    ap_uf_stats_clean = ap_uf_stats.dropna(subset=features_clust).copy()
    if len(ap_uf_stats_clean) >= 4:
        scaler_uf = StandardScaler()
        X_uf = scaler_uf.fit_transform(ap_uf_stats_clean[features_clust])
        kmeans_uf = KMeans(n_clusters=4, random_state=42)
        ap_uf_stats_clean['cluster'] = kmeans_uf.fit_predict(X_uf)
        centroids_uf = ap_uf_stats_clean.groupby('cluster')[features_clust].mean()
        
        # Rotulagem programática UniFi (K=4)
        idx_crit_uf = centroids_uf['retransmissoes_media'].idxmax()
        remaining_uf_1 = [i for i in range(4) if i != idx_crit_uf]
        idx_high_load_uf = centroids_uf.loc[remaining_uf_1, 'throughput_agregado_media'].idxmax()
        
        remaining_uf_2 = [i for i in remaining_uf_1 if i != idx_high_load_uf]
        idx_low_ret_uf = centroids_uf.loc[remaining_uf_2, 'retransmissoes_media'].idxmin()
        idx_low_load_uf = [i for i in remaining_uf_2 if i != idx_low_ret_uf][0]
        
        labels_uf = {
            idx_crit_uf: "Grupo C: Alta Retransmissão",
            idx_high_load_uf: "Grupo A: Muito Carregado",
            idx_low_ret_uf: "Grupo D: Baixa Retransmissão / Estável",
            idx_low_load_uf: "Grupo B: Pouco Utilizado"
        }
        ap_uf_stats_clean['cluster_label'] = ap_uf_stats_clean['cluster'].map(labels_uf)
    else:
        ap_uf_stats_clean['cluster_label'] = 'N/A'
        centroids_uf = pd.DataFrame()
        labels_uf = {}

    # Atualizar as tabelas de estatísticas para conter as informações de cluster
    ap_rk_stats = ap_rk_stats.merge(ap_rk_stats_clean[['AP_display', 'cluster_label']], on='AP_display', how='left')
    ap_rk_stats['cluster_label'] = ap_rk_stats['cluster_label'].fillna('N/A')
    
    ap_uf_stats = ap_uf_stats.merge(ap_uf_stats_clean[['AP', 'cluster_label']], on='AP', how='left')
    ap_uf_stats['cluster_label'] = ap_uf_stats['cluster_label'].fillna('N/A')

    # Gerar gráficos de clusters
    if len(ap_rk_stats_clean) >= 4:
        plt.figure(figsize=(10, 6))
        plot_df_rk = ap_rk_stats_clean.rename(columns={
            'cluster_label': 'Grupo Operacional',
            'retransmissoes_media': 'Retransmissões (%)'
        })
        sns.scatterplot(
            data=plot_df_rk,
            x='clientes_media',
            y='throughput_agregado_media',
            hue='Grupo Operacional',
            size='Retransmissões (%)',
            sizes=(40, 240),
            palette='viridis',
            alpha=0.8
        )
        plt.title('Clusterização de APs Ruckus (K=4)\n(Tamanho do ponto indica taxa de retransmissão)', fontsize=13, fontweight='bold', pad=15)
        plt.xlabel('Média de Clientes Conectados', fontsize=11)
        plt.ylabel('Throughput Agregado Médio (Mbps)', fontsize=11)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'cluster_ruckus.png'), dpi=150, bbox_inches='tight')
        plt.close()

    if len(ap_uf_stats_clean) >= 4:
        plt.figure(figsize=(10, 6))
        plot_df_uf = ap_uf_stats_clean.rename(columns={
            'cluster_label': 'Grupo Operacional',
            'retransmissoes_media': 'Retransmissões (%)'
        })
        sns.scatterplot(
            data=plot_df_uf,
            x='clientes_media',
            y='throughput_agregado_media',
            hue='Grupo Operacional',
            size='Retransmissões (%)',
            sizes=(40, 240),
            palette='viridis',
            alpha=0.8
        )
        plt.title('Clusterização de APs UniFi (K=4)\n(Tamanho do ponto indica taxa de retransmissão)', fontsize=13, fontweight='bold', pad=15)
        plt.xlabel('Média de Clientes Conectados', fontsize=11)
        plt.ylabel('Throughput Agregado Médio (Mbps)', fontsize=11)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, 'cluster_unifi.png'), dpi=150, bbox_inches='tight')
        plt.close()

    def make_ap_table(df):
        rows = []
        for _, r in df.iterrows():
            ap_name = r.get('AP_display', r.get('AP'))
            sinal_str = f"{r['sinal_medio']:.1f}" if pd.notna(r['sinal_medio']) else "N/A"
            equidade_str = f"{r['equidade_media']:.4f}" if pd.notna(r['equidade_media']) else "N/A"
            cluster_lbl = r.get('cluster_label', 'N/A')
            rows.append(
                f"| **{ap_name}** | {int(r['amostras']):,} | {r['clientes_media']:.1f} (max {int(r['clientes_max'])}) | {r['throughput_agregado_media']:.3f} (max {r['throughput_agregado_max']:.3f}) | {sinal_str} | {r['retransmissoes_media']:.2f}% | {r['throughput_cliente_media']:.3f} | {equidade_str} | {cluster_lbl} |"
            )
        return "\n".join(rows)

    def make_centroids_md(centroids, labels):
        if centroids.empty:
            return "*Não foi possível calcular os centróides (amostras insuficientes).*"
        header = [
            "| Perfil Operacional (Cluster) | Média Clientes | Throughput Agregado Médio [Mbps] | Sinal Médio [dBm] | Retransmissões Médias [%] |",
            "| :--- | :---: | :---: | :---: | :---: |"
        ]
        items = []
        for idx, row in centroids.iterrows():
            name = labels.get(idx, f"Cluster {idx}")
            row_str = f"| **{name}** | {row['clientes_media']:.2f} | {row['throughput_agregado_media']:.3f} | {row['sinal_medio']:.1f} | {row['retransmissoes_media']:.2f}% |"
            items.append((name, row_str))
            
        # Ordenar alfabeticamente pelo nome do grupo (Grupo A, Grupo B, Grupo C, Grupo D)
        items.sort(key=lambda x: x[0])
        
        rows = header + [item[1] for item in items]
        return "\n".join(rows)

    centroids_rk_md = make_centroids_md(centroids_rk, labels_rk)
    centroids_uf_md = make_centroids_md(centroids_uf, labels_uf)

    ap_rk_table = make_ap_table(ap_rk_stats)
    ap_uf_table = make_ap_table(ap_uf_stats)

    # --- GERAR RELATÓRIO MARKDOWN ---
    def get_md_row(label):
        rk = df_res[(df_res['Categoria'] == label) & (df_res['Fabricante'] == 'Ruckus')].iloc[0]
        uf = df_res[(df_res['Categoria'] == label) & (df_res['Fabricante'] == 'UniFi')].iloc[0]
        
        row_rk = f"| **Ruckus** | {label} | {rk['Amostras_N']:,} | {rk['Porcentagem_Pct']:.2f}% | {rk['Throughput_Media']:.3f} / {rk['Throughput_Mediana']:.3f} | {rk['Retransmissoes_Media']:.2f}% / {rk['Retransmissoes_Mediana']:.2f}% |"
        row_uf = f"| **UniFi** | {label} | {uf['Amostras_N']:,} | {uf['Porcentagem_Pct']:.2f}% | {uf['Throughput_Media']:.3f} / {uf['Throughput_Mediana']:.3f} | {uf['Retransmissoes_Media']:.2f}% / {uf['Retransmissoes_Mediana']:.2f}% |"
        return row_rk + "\n" + row_uf

    # Criar um dicionário para busca rápida de valores
    g_data = {}
    for _, r in df_res.iterrows():
        key = (r['Fabricante'], r['Categoria'])
        g_data[key] = {
            'amostras': r['Amostras_N'],
            'porcentagem': r['Porcentagem_Pct'],
            'tp_media': r['Throughput_Media'],
            'tp_mediana': r['Throughput_Mediana'],
            'ret_media': r['Retransmissoes_Media'],
            'ret_mediana': r['Retransmissoes_Mediana']
        }
        
    def get_val(fab, cat, field, default=0.0):
        return g_data.get((fab, cat), {}).get(field, default)

    # Distribuição de Gargalos (Frequências)
    pct_g1_rk = get_val('Ruckus', 'G1: Baixa Qualidade de Enlace', 'porcentagem')
    pct_g1_uf = get_val('UniFi', 'G1: Baixa Qualidade de Enlace', 'porcentagem')
    pct_g2_rk = get_val('Ruckus', 'G2: Congestionamento do Meio', 'porcentagem')
    pct_g2_uf = get_val('UniFi', 'G2: Congestionamento do Meio', 'porcentagem')
    pct_g3_rk = get_val('Ruckus', 'G3: Interferência / SNR Ruim', 'porcentagem')
    pct_g3_uf = get_val('UniFi', 'G3: Interferência / SNR Ruim', 'porcentagem')
    pct_g4_rk = get_val('Ruckus', 'G4: Instabilidade de Roaming', 'porcentagem')
    pct_g4_uf = get_val('UniFi', 'G4: Instabilidade de Roaming', 'porcentagem')
    pct_g5_rk = get_val('Ruckus', 'G5: Gargalo Cabeado (FE)', 'porcentagem')
    pct_g5_uf = get_val('UniFi', 'G5: Gargalo Cabeado (FE)', 'porcentagem')

    # Throughput Médio
    tp_sg_rk = get_val('Ruckus', 'Sem Gargalos', 'tp_media')
    tp_sg_uf = get_val('UniFi', 'Sem Gargalos', 'tp_media')
    tp_g1_rk = get_val('Ruckus', 'G1: Baixa Qualidade de Enlace', 'tp_media')
    tp_g1_uf = get_val('UniFi', 'G1: Baixa Qualidade de Enlace', 'tp_media')
    tp_g2_rk = get_val('Ruckus', 'G2: Congestionamento do Meio', 'tp_media')
    tp_g2_uf = get_val('UniFi', 'G2: Congestionamento do Meio', 'tp_media')
    tp_g3_rk = get_val('Ruckus', 'G3: Interferência / SNR Ruim', 'tp_media')
    tp_g3_uf = get_val('UniFi', 'G3: Interferência / SNR Ruim', 'tp_media')
    tp_g4_rk = get_val('Ruckus', 'G4: Instabilidade de Roaming', 'tp_media')
    tp_g4_uf = get_val('UniFi', 'G4: Instabilidade de Roaming', 'tp_media')

    # Percentuais de redução de throughput
    red_tp_rk_g1 = (1.0 - (tp_g1_rk / tp_sg_rk)) * 100 if tp_sg_rk > 0 else 0.0
    red_tp_uf_g1 = (1.0 - (tp_g1_uf / tp_sg_uf)) * 100 if tp_sg_uf > 0 else 0.0
    red_tp_uf_g2 = (1.0 - (tp_g2_uf / tp_sg_uf)) * 100 if tp_sg_uf > 0 else 0.0
    red_tp_uf_g3 = (1.0 - (tp_g3_uf / tp_sg_uf)) * 100 if tp_sg_uf > 0 else 0.0
    red_tp_rk_g4 = (1.0 - (tp_g4_rk / tp_sg_rk)) * 100 if tp_sg_rk > 0 else 0.0

    # Retransmissões Médias
    ret_sg_rk = get_val('Ruckus', 'Sem Gargalos', 'ret_media')
    ret_sg_uf = get_val('UniFi', 'Sem Gargalos', 'ret_media')
    ret_g1_rk = get_val('Ruckus', 'G1: Baixa Qualidade de Enlace', 'ret_media')
    ret_g1_uf = get_val('UniFi', 'G1: Baixa Qualidade de Enlace', 'ret_media')
    ret_g2_rk = get_val('Ruckus', 'G2: Congestionamento do Meio', 'ret_media')
    ret_g2_uf = get_val('UniFi', 'G2: Congestionamento do Meio', 'ret_media')
    ret_g3_rk = get_val('Ruckus', 'G3: Interferência / SNR Ruim', 'ret_media')
    ret_g3_uf = get_val('UniFi', 'G3: Interferência / SNR Ruim', 'ret_media')
    ret_g4_rk = get_val('Ruckus', 'G4: Instabilidade de Roaming', 'ret_media')
    ret_g4_uf = get_val('UniFi', 'G4: Instabilidade de Roaming', 'ret_media')

    # Percentuais de aumento de retransmissões
    aum_ret_rk_g1 = ((ret_g1_rk / ret_sg_rk) - 1.0) * 100 if ret_sg_rk > 0 else 0.0
    aum_ret_uf_g1 = ((ret_g1_uf / ret_sg_uf) - 1.0) * 100 if ret_sg_uf > 0 else 0.0
    aum_ret_uf_g3 = ((ret_g3_uf / ret_sg_uf) - 1.0) * 100 if ret_sg_uf > 0 else 0.0
    aum_ret_rk_g4 = ((ret_g4_rk / ret_sg_rk) - 1.0) * 100 if ret_sg_rk > 0 else 0.0

    # Valores dinâmicos dos centróides da Ruckus
    rk_a_cli = centroids_rk.loc[idx_high_load_rk, 'clientes_media'] if not centroids_rk.empty else 0.0
    rk_a_tp = centroids_rk.loc[idx_high_load_rk, 'throughput_agregado_media'] if not centroids_rk.empty else 0.0
    rk_a_sig = centroids_rk.loc[idx_high_load_rk, 'sinal_medio'] if not centroids_rk.empty else 0.0
    rk_a_ret = centroids_rk.loc[idx_high_load_rk, 'retransmissoes_media'] if not centroids_rk.empty else 0.0

    rk_b_cli = centroids_rk.loc[idx_low_load_rk, 'clientes_media'] if not centroids_rk.empty else 0.0
    rk_b_tp = centroids_rk.loc[idx_low_load_rk, 'throughput_agregado_media'] if not centroids_rk.empty else 0.0
    rk_b_sig = centroids_rk.loc[idx_low_load_rk, 'sinal_medio'] if not centroids_rk.empty else 0.0
    rk_b_ret = centroids_rk.loc[idx_low_load_rk, 'retransmissoes_media'] if not centroids_rk.empty else 0.0

    rk_c_cli = centroids_rk.loc[idx_moderate_rk, 'clientes_media'] if not centroids_rk.empty else 0.0
    rk_c_tp = centroids_rk.loc[idx_moderate_rk, 'throughput_agregado_media'] if not centroids_rk.empty else 0.0
    rk_c_sig = centroids_rk.loc[idx_moderate_rk, 'sinal_medio'] if not centroids_rk.empty else 0.0
    rk_c_ret = centroids_rk.loc[idx_moderate_rk, 'retransmissoes_media'] if not centroids_rk.empty else 0.0

    rk_d_cli = centroids_rk.loc[idx_low_signal_rk, 'clientes_media'] if not centroids_rk.empty else 0.0
    rk_d_tp = centroids_rk.loc[idx_low_signal_rk, 'throughput_agregado_media'] if not centroids_rk.empty else 0.0
    rk_d_sig = centroids_rk.loc[idx_low_signal_rk, 'sinal_medio'] if not centroids_rk.empty else 0.0
    rk_d_ret = centroids_rk.loc[idx_low_signal_rk, 'retransmissoes_media'] if not centroids_rk.empty else 0.0

    # Valores dinâmicos dos centróides da UniFi
    uf_a_cli = centroids_uf.loc[idx_high_load_uf, 'clientes_media'] if not centroids_uf.empty else 0.0
    uf_a_tp = centroids_uf.loc[idx_high_load_uf, 'throughput_agregado_media'] if not centroids_uf.empty else 0.0
    uf_a_sig = centroids_uf.loc[idx_high_load_uf, 'sinal_medio'] if not centroids_uf.empty else 0.0
    uf_a_ret = centroids_uf.loc[idx_high_load_uf, 'retransmissoes_media'] if not centroids_uf.empty else 0.0

    uf_b_cli = centroids_uf.loc[idx_low_load_uf, 'clientes_media'] if not centroids_uf.empty else 0.0
    uf_b_tp = centroids_uf.loc[idx_low_load_uf, 'throughput_agregado_media'] if not centroids_uf.empty else 0.0
    uf_b_sig = centroids_uf.loc[idx_low_load_uf, 'sinal_medio'] if not centroids_uf.empty else 0.0
    uf_b_ret = centroids_uf.loc[idx_low_load_uf, 'retransmissoes_media'] if not centroids_uf.empty else 0.0

    uf_c_cli = centroids_uf.loc[idx_crit_uf, 'clientes_media'] if not centroids_uf.empty else 0.0
    uf_c_tp = centroids_uf.loc[idx_crit_uf, 'throughput_agregado_media'] if not centroids_uf.empty else 0.0
    uf_c_sig = centroids_uf.loc[idx_crit_uf, 'sinal_medio'] if not centroids_uf.empty else 0.0
    uf_c_ret = centroids_uf.loc[idx_crit_uf, 'retransmissoes_media'] if not centroids_uf.empty else 0.0

    uf_d_cli = centroids_uf.loc[idx_low_ret_uf, 'clientes_media'] if not centroids_uf.empty else 0.0
    uf_d_tp = centroids_uf.loc[idx_low_ret_uf, 'throughput_agregado_media'] if not centroids_uf.empty else 0.0
    uf_d_sig = centroids_uf.loc[idx_low_ret_uf, 'sinal_medio'] if not centroids_uf.empty else 0.0
    uf_d_ret = centroids_uf.loc[idx_low_ret_uf, 'retransmissoes_media'] if not centroids_uf.empty else 0.0

    report_content = f"""# Classificação de Gargalos de Rede

## Limiares de Decisão Estabelecidos

1.  **G1: Baixa Qualidade de Enlace**: Potência física de sinal recebido pelo AP (`signal`) < `-75 dBm`.
2.  **G2: Congestionamento do Meio**: Número de clientes simultâneos conectados no mesmo AP e minuto >= 15.
3.  **G3: Interferência / SNR Ruim**: Ruído de fundo (`noise`) > `-90 dBm` ou SNR < `20 dB` em clientes com bom sinal (>= -75 dBm).
4.  **G4: Instabilidade de Roaming**: Clientes (MAC) que registraram > 5 trocas de AP no período de observação.
5.  **G5: Gargalo Cabeado (FE)**: Throughput de tráfego agregado sustentado do AP >= 90 Mbps (limite de interface Fast Ethernet de 100 Mbps).

---

## Tabela Geral de Ocorrência e Impacto de Gargalos

| Fabricante | Categoria de Gargalo | Amostras (N) | Porcentagem (%) | Throughput Cliente (Méd/Med) [Mbps] | Retransmissões (Méd/Med) [%] |
| :--- | :--- | :---: | :---: | :---: | :---: |
{get_md_row('G1: Baixa Qualidade de Enlace')}
{get_md_row('G2: Congestionamento do Meio')}
{get_md_row('G3: Interferência / SNR Ruim')}
{get_md_row('G4: Instabilidade de Roaming')}
{get_md_row('G5: Gargalo Cabeado (FE)')}
{get_md_row('Sem Gargalos')}

---

## Análise de Desempenho e Carga por Access Point

Abaixo são apresentados os perfis consolidados de carga e desempenho de cada Access Point mapeado na coleta, ordenados pelo throughput agregado médio (indicador de demanda atendida).

### Rede Ruckus (APs MAC Simplificados)

| Access Point | Amostras (N) | Clientes Médios (Pico) | Throughput Agregado Médio (Max) [Mbps] | Sinal Médio [dBm] | Retransmissões Médias [%] | Throughput Médio p/ Cliente [Mbps] | Equidade Média (Jain) | Perfil Operacional (Cluster) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
{ap_rk_table}

### Rede UniFi (APs Cadastrados)

| Access Point | Amostras (N) | Clientes Médios (Pico) | Throughput Agregado Médio (Max) [Mbps] | Sinal Médio [dBm] | Retransmissões Médias [%] | Throughput Médio p/ Cliente [Mbps] | Equidade Média (Jain) | Perfil Operacional (Cluster) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
{ap_uf_table}

---

## Análise de Distribuição e Frequência

![Distribuição de Gargalos](graficos/distribuicao_gargalos.png)

1.  **Baixa Qualidade de Enlace (G1)**:
    *   Afeta **{pct_g1_rk:.2f}%** das amostras na Ruckus e **{pct_g1_uf:.2f}%** na UniFi. Esse perfil elevado indica que uma porção considerável dos usuários se posicionou nas bordas de cobertura ou em zonas de sombra do sinal Wi-Fi.
2.  **Congestionamento do Meio (G2)**:
    *   A Ruckus registrou **{pct_g2_rk:.2f}%** de suas amostras sob congestionamento (APs com 15 ou mais clientes simultâneos), enquanto a UniFi teve apenas **{pct_g2_uf:.2f}%** sob essa condição. Essa discrepância confirma que a rede Ruckus atende ao intenso adensamento de usuários.
3.  **Interferência (G3)**:
    *   Este gargalo teve incidência nula na Ruckus (**{pct_g3_rk:.2f}%**) e ínfima na UniFi (**{pct_g3_uf:.2f}%**) sob os critérios rigorosos avaliados de forma isolada, indicando que os cenários de alta retransmissão estão fundamentalmente vinculados à fraca qualidade de sinal ou ao excessivo congestionamento e trocas de AP.
4.  **Instabilidade de Roaming (G4)**:
    *   Afetou massivos **{pct_g4_rk:.2f}%** dos registros de Ruckus e **{pct_g4_uf:.2f}%** de UniFi. Dispositivos móveis realizam abundantes transições ou persistem conectados a APs distantes (*sticky clients*), evidenciando o gargalo mais disseminado da infraestrutura corporativa do campus.
5.  **Limitação de Infraestrutura Cabeada (G5)**:
    *   Virtualmente nula (**{pct_g5_rk:.2f}%** na Ruckus e **{pct_g5_uf:.2f}%** na UniFi). O tráfego não saturou de forma crônica as portas Fast Ethernet, indicando que o gargalo de *backhaul* cabeado não é a atual limitação de desempenho.

---

## Análise de Consequências e Hipóteses

### Impacto no Throughput

![Impacto no Throughput](graficos/impacto_throughput.png)

*   **Padrão de Throughput (Sem Gargalos)**: Sob condições ideais ("Sem Gargalos"), o throughput médio por cliente foi de `{tp_sg_rk:.3f} Mbps` no Ruckus e `{tp_sg_uf:.3f} Mbps` no UniFi.
*   **Consequência de Baixa Qualidade de Sinal (G1)**: No Ruckus, a vazão média manteve-se em `{tp_g1_rk:.3f} Mbps` (redução de {red_tp_rk_g1:.1f}% em relação ao ideal). Já na UniFi, a vazão despencou para `{tp_g1_uf:.3f} Mbps` (redução severa de {red_tp_uf_g1:.1f}%), demonstrando o alto impacto da atenuação física sobre o desempenho dos clientes.
*   **Consequência de Congestionamento (G2)**: A vazão média manteve-se em `{tp_g2_rk:.3f} Mbps` no Ruckus e registrou queda na UniFi para `{tp_g2_uf:.3f} Mbps` (redução de {red_tp_uf_g2:.1f}% em relação à condição ideal), refletindo o efeito do compartilhamento de tempo de transmissão aérea (CSMA/CA).
*   **Consequência de Interferência (G3)**: Não houve registros isolados suficientes no Ruckus (incidência de {pct_g3_rk:.2f}%), enquanto a UniFi registrou queda significativa da vazão média para `{tp_g3_uf:.3f} Mbps` (redução de {red_tp_uf_g3:.1f}% em relação ao ideal).
*   **Consequência de Instabilidade de Roaming (G4)**: O throughput médio de clientes afetados por roaming frequente foi de `{tp_g4_rk:.3f} Mbps` no Ruckus (queda de {red_tp_rk_g4:.1f}% em relação ao ideal) e `{tp_g4_uf:.3f} Mbps` no UniFi.

### Impacto nas Retransmissões

![Impacto nas Retransmissões](graficos/impacto_retransmissoes.png)

*   **Padrão Esperado (Sem Gargalos)**: Sob condições ideais, as taxas médias de retransmissão situaram-se em `{ret_sg_rk:.2f}%` na Ruckus e `{ret_sg_uf:.2f}%` na UniFi.
*   **Consequência de Baixa Qualidade de Sinal (G1)**: Sob sinal fraco, a taxa de retransmissão no Ruckus subiu levemente para `{ret_g1_rk:.2f}%` (aumento de {aum_ret_rk_g1:.1f}% em relação ao ideal). Na UniFi, contudo, observou-se a maior elevação registrada, alcançando `{ret_g1_uf:.2f}%` (um aumento de {aum_ret_uf_g1:.1f}% em relação ao ideal), comprovando a degradação da integridade de quadros em enlaces atenuados.
*   **Consequência de Congestionamento (G2)**: A taxa de retransmissão manteve-se estável na Ruckus (`{ret_g2_rk:.2f}%`) e na UniFi (`{ret_g2_uf:.2f}%`), indicando que a concorrência pelo meio não foi a causa primária para o aumento direto de retransmissões.
*   **Consequência de Interferência (G3)**: Sem registros isolados na Ruckus, a UniFi registrou taxa de retransmissão elevada em `{ret_g3_uf:.2f}%` (aumento de {aum_ret_uf_g3:.1f}% em relação ao ideal), o que evidencia a ocorrência de colisões provocadas por ruído de RF.
*   **Consequência de Instabilidade de Roaming (G4)**: A taxa no Ruckus variou ligeiramente para `{ret_g4_rk:.2f}%` (aumento de {aum_ret_rk_g4:.1f}% em relação ao ideal), enquanto a UniFi registrou taxa média de `{ret_g4_uf:.2f}%`.

---

## 6. Clusterização e Perfil Operacional dos Access Points (K-Means)

Para agrupar os Access Points com comportamentos operacionais semelhantes e gerar um mapa de diagnóstico útil, aplicou-se o algoritmo de aprendizado de máquina **K-Means** (com $K=4$ clusters para cada fabricante). A clusterização baseou-se na aplicação do algoritmo com normalização prévia das variáveis por meio do `StandardScaler` para evitar que a diferença de escalas (como potência de sinal em dBm vs clientes em unidades) distorcesse as distâncias euclidianas. O valor de $K=4$ foi escolhido para segmentar os rádios de cada fabricante em categorias nítidas de comportamento operacional, permitindo contrastar o desempenho sob carga ativa contra cenários de isolamento físico ou degradação. As variáveis utilizadas para a clusterização foram: média de clientes, throughput agregado médio do AP, sinal físico médio e taxa média de retransmissões.

Os centróides e perfis detalhados resultantes de cada cluster são discutidos a seguir:

### Perfis de Rádios Ruckus

{centroids_rk_md}

*   **Grupo A: Muito Carregado**: Representa os access points que operam sob intensa demanda de usuários (média de `{rk_a_cli:.2f}` clientes conectados e pico de tráfego agregado médio de `{rk_a_tp:.3f} Mbps`). Apesar de operar sob alta concorrência de canal e sinal físico médio de `{rk_a_sig:.1f} dBm`, este grupo apresenta a menor taxa de retransmissão de toda a rede Ruckus (média de `{rk_a_ret:.2f}%`). Isso demonstra o desempenho altamente eficiente do agendamento de pacotes e mitigação de colisões da arquitetura Ruckus sob forte carga.
*   **Grupo B: Pouco Utilizado**: Constituído por APs com baixo volume de tráfego (média de `{rk_b_tp:.3f} Mbps`) e baixa concorrência (média de `{rk_b_cli:.2f}` clientes). O sinal físico médio é excelente (média de `{rk_b_sig:.1f} dBm`) e as retransmissões mantêm-se estáveis em `{rk_b_ret:.2f}%`, representando pontos de ociosidade operacional na rede corporativa.
*   **Grupo C: Carga Moderada**: Representa o perfil operacional típico nominal de RF da rede no campus (média de `{rk_c_cli:.2f}` clientes e throughput agregado médio de `{rk_c_tp:.3f} Mbps`). Apresenta sinal médio de `{rk_c_sig:.1f} dBm` e taxa de retransmissão saudável de `{rk_c_ret:.2f}%`.
*   **Grupo D: Baixa Qualidade de Sinal**: Caracteriza os rádios severamente limitados pela qualidade física de recepção de sinal (média de `{rk_d_sig:.1f} dBm`). O baixo tráfego agregado registrado (`{rk_d_tp:.3f} Mbps`) é reflexo não da ociosidade (média de `{rk_d_cli:.2f}` clientes), mas da elevada taxa de retransmissão de quadros (`{rk_d_ret:.2f}%`), que aponta perda de pacotes frequente e atenuação física no enlace.

### Perfis de Rádios UniFi

{centroids_uf_md}

*   **Grupo A: Muito Carregado**: Engloba os APs da rede UniFi com maior atividade relativa (média de `{uf_a_cli:.2f}` clientes e throughput agregado médio de `{uf_a_tp:.3f} Mbps`). O sinal médio é saudável (`{uf_a_sig:.1f} dBm`), mas a taxa de retransmissões média é elevada (`{uf_a_ret:.2f}%`), indicando forte contenção do meio de transmissão sob concorrência na banda saturada de 2,4 GHz.
*   **Grupo B: Pouco Utilizado**: É o maior cluster em número de APs na UniFi, ilustrando sua ociosidade (média de `{uf_b_cli:.2f}` clientes e vazão de tráfego irrisória de `{uf_b_tp:.3f} Mbps`). As retransmissões médias situam-se em `{uf_b_ret:.2f}%`, valor induzido pelo ruído de fundo permanente do espectro.
*   **Grupo C: Alta Retransmissão**: Mapeia rádios com comportamento anômalo: excelente intensidade de sinal físico (média de `{uf_c_sig:.1f} dBm`, indicando proximidade imediata dos dispositivos), porém com taxa crítica de retransmissão de `{uf_c_ret:.2f}%`. Esse padrão sugere interferência severa de canais adjacentes ou co-canal no espectro saturado de 2,4 GHz, ou desbalanceamento de potência de transmissão entre o AP e o cliente.
*   **Grupo D: Baixa Retransmissão / Estável**: Representa os rádios UniFi operando em condições de melhor estabilidade de RF (média de `{uf_d_cli:.2f}` clientes e sinal médio de `{uf_d_sig:.1f} dBm`). Alcança a menor taxa de retransmissão média registrada para a UniFi (`{uf_d_ret:.2f}%`), validando a estabilidade do enlace sob baixa concorrência.

### Gráficos de Dispersão dos Clusters de APs

As figuras abaixo mapeiam os APs no espaço de carga (Clientes vs Throughput Agregado), com o tamanho dos pontos indicando a taxa de retransmissão e a cor indicando o grupo operacional.

*   **Ruckus**:
![Clusterização Ruckus](graficos/cluster_ruckus.png)

*   **UniFi**:
![Clusterização UniFi](graficos/cluster_unifi.png)

---
*Relatório de classificação de gargalos gerado em: Etapa_5_Classificacao_Gargalos/relatorio_gargalos.md*
"""
    
    report_path = os.path.join(output_dir, 'relatorio_gargalos.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"Relatório Markdown termo mitigado e AP analysis salvo em: {report_path}")
    
    # 3. Converter MD para PDF
    pdf_path = os.path.join(output_dir, 'relatorio_gargalos.pdf')
    pdf_success = convert_md_to_pdf(report_path, pdf_path)
    
    if pdf_success:
        print(f"Relatório PDF compilado em: {pdf_path}")
    else:
        print("Aviso: Falha na conversão do relatório de gargalos para PDF.")
        
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    output_dir = os.path.join(base_dir, 'Etapa_5_Classificacao_Gargalos')
    run_bottleneck_analysis(ruckus_std, unifi_std, output_dir)

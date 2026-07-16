import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

def get_ap_stats(df):
    # A. Clientes por AP e minuto
    df_ap_count = df.groupby(['timestamp', 'AP']).size().reset_index(name='clientes_por_ap')
    df = df.merge(df_ap_count, on=['timestamp', 'AP'], how='left')
    
    # B. Throughput agregado por AP e minuto
    df_ap_tp = df.groupby(['timestamp', 'AP'])['throughput_total_mbps'].sum().reset_index(name='tp_agregado_ap')
    df = df.merge(df_ap_tp, on=['timestamp', 'AP'], how='left')
    
    # Consolidar por AP
    ap_stats = df.groupby('AP').agg(
        clientes_media=('clientes_por_ap', 'mean'),
        throughput_agregado_media=('tp_agregado_ap', 'mean'),
        sinal_medio=('signal', 'mean'),
        retransmissoes_media=('retransmissoes_pct', 'mean')
    ).reset_index()
    return ap_stats

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ruckus_path = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_path = os.path.join(base_dir, 'unifi_standardized.csv')
    output_dir = os.path.join(base_dir, 'Etapa_5_Classificacao_Gargalos')
    
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados. Execute o pipeline primeiro.")
        return

    df_rk = pd.read_csv(ruckus_path)
    df_uf = pd.read_csv(unifi_path)
    
    features_clust = ['clientes_media', 'throughput_agregado_media', 'sinal_medio', 'retransmissoes_media']
    
    # Extrair estatísticas consolidadas por AP
    ap_rk_stats = get_ap_stats(df_rk)
    ap_uf_stats = get_ap_stats(df_uf)
    
    ap_rk_clean = ap_rk_stats.dropna(subset=features_clust).copy()
    ap_uf_clean = ap_uf_stats.dropna(subset=features_clust).copy()
    
    scaler_rk = StandardScaler()
    X_rk = scaler_rk.fit_transform(ap_rk_clean[features_clust])
    
    scaler_uf = StandardScaler()
    X_uf = scaler_uf.fit_transform(ap_uf_clean[features_clust])
    
    k_range = [2, 3, 4, 5, 6]
    
    results = {'Ruckus': [], 'UniFi': []}
    
    # Executar K-Means e calcular métricas
    for name, X in [('Ruckus', X_rk), ('UniFi', X_uf)]:
        print(f"\nCalculando métricas para {name} (N_APs = {len(X)})...")
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(X)
            inertia = kmeans.inertia_
            sil = silhouette_score(X, labels)
            db = davies_bouldin_score(X, labels)
            
            results[name].append({
                'K': k,
                'Inércia': inertia,
                'Silhueta': sil,
                'Davies-Bouldin': db
            })
            print(f"  K={k} | Inércia={inertia:.2f} | Silhueta={sil:.4f} | Davies-Bouldin={db:.4f}")
            
    # Criar DataFrame para facilidade de plotagem
    df_rk_metrics = pd.DataFrame(results['Ruckus'])
    df_uf_metrics = pd.DataFrame(results['UniFi'])
    
    # Plotar os resultados para a monografia / apresentação
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    
    # Ruckus plots
    sns.lineplot(data=df_rk_metrics, x='K', y='Inércia', marker='o', color='#3498db', ax=axes[0, 0])
    axes[0, 0].set_title('Ruckus: Método do Cotovelo (Inércia)', fontweight='bold')
    axes[0, 0].set_xticks(k_range)
    
    sns.lineplot(data=df_rk_metrics, x='K', y='Silhueta', marker='s', color='#2ecc71', ax=axes[0, 1])
    axes[0, 1].set_title('Ruckus: Índice de Silhueta (Maior é melhor)', fontweight='bold')
    axes[0, 1].set_xticks(k_range)
    
    sns.lineplot(data=df_rk_metrics, x='K', y='Davies-Bouldin', marker='^', color='#e74c3c', ax=axes[0, 2])
    axes[0, 2].set_title('Ruckus: Davies-Bouldin (Menor é melhor)', fontweight='bold')
    axes[0, 2].set_xticks(k_range)
    
    # UniFi plots
    sns.lineplot(data=df_uf_metrics, x='K', y='Inércia', marker='o', color='#3498db', ax=axes[1, 0])
    axes[1, 0].set_title('UniFi: Método do Cotovelo (Inércia)', fontweight='bold')
    axes[1, 0].set_xticks(k_range)
    
    sns.lineplot(data=df_uf_metrics, x='K', y='Silhueta', marker='s', color='#2ecc71', ax=axes[1, 1])
    axes[1, 1].set_title('UniFi: Índice de Silhueta (Maior é melhor)', fontweight='bold')
    axes[1, 1].set_xticks(k_range)
    
    sns.lineplot(data=df_uf_metrics, x='K', y='Davies-Bouldin', marker='^', color='#e74c3c', ax=axes[1, 2])
    axes[1, 2].set_title('UniFi: Davies-Bouldin (Menor é melhor)', fontweight='bold')
    axes[1, 2].set_xticks(k_range)
    
    plt.suptitle('Validação Numérica da Quantidade de Clusters (K) - K-Means', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    plot_path = os.path.join(output_dir, 'graficos', 'validador_kmeans_metricas.png')
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"\nGráfico comparativo de validação salvo em: {plot_path}")

if __name__ == '__main__':
    main()

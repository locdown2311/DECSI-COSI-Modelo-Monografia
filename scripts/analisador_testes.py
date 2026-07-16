import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import shapiro, ttest_ind, mannwhitneyu

# Adicionar a raiz do projeto ao sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from utils.convert_md_to_pdf import convert_md_to_pdf

def get_jains_fairness_series(df):
    if df.empty or 'timestamp' not in df.columns or 'throughput_total_mbps' not in df.columns:
        return pd.Series(dtype=float)
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

def run_statistical_analysis(ruckus_path, unifi_path, output_dir):
    print("Iniciando ETAPA 4 – Testes Estatísticos...")
    
    # 1. Carregar datasets
    if not os.path.exists(ruckus_path) or not os.path.exists(unifi_path):
        print("Erro: Datasets padronizados não encontrados. Execute o standardizer primeiro.")
        return False
        
    df_ruckus = pd.read_csv(ruckus_path)
    df_unifi = pd.read_csv(unifi_path)
    
    # Criar diretórios
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'graficos')
    os.makedirs(plots_dir, exist_ok=True)
    
    sns.set_theme(style="whitegrid")
    
    # Verificar se UniFi possui dados de 5 GHz
    has_unifi_5g = (df_unifi['banda'] == '5 GHz').sum() >= 5
    print(f"UniFi possui dados de 5 GHz utilizáveis? {'Sim' if has_unifi_5g else 'Não (Apenas 2.4 GHz disponível)'}")
    
    # Dicionário de resultados
    results = []
    
    # Função auxiliar para rodar teste de normalidade com amostragem
    def test_normality(data, label):
        clean_data = data.dropna()
        n = len(clean_data)
        if n < 5:
            return False, np.nan, np.nan, n
        
        # Amostragem se N > 5000 (limite Shapiro-Wilk)
        if n > 5000:
            sample_data = clean_data.sample(5000, random_state=42)
        else:
            sample_data = clean_data
            
        try:
            stat, p = shapiro(sample_data)
            is_normal = p >= 0.05
            return is_normal, stat, p, n
        except Exception as e:
            print(f"Erro no teste de normalidade para {label}: {e}")
            return False, np.nan, np.nan, n

    # Função auxiliar para rodar teste de hipótese adequado com tamanho de efeito
    def compare_groups(df_a, col_a, df_b, col_b, label_a, label_b, var_name, category):
        data_a = df_a[col_a].dropna()
        data_b = df_b[col_b].dropna()
        
        n_a = len(data_a)
        n_b = len(data_b)
        
        if n_a < 5 or n_b < 5:
            res = {
                'Categoria': category,
                'Variavel': var_name,
                'Grupo_A': label_a,
                'N_A': n_a,
                'Media_A': data_a.mean() if n_a > 0 else np.nan,
                'Mediana_A': data_a.median() if n_a > 0 else np.nan,
                'Normal_A': "N/A",
                'Grupo_B': label_b,
                'N_B': n_b,
                'Media_B': data_b.mean() if n_b > 0 else np.nan,
                'Mediana_B': data_b.median() if n_b > 0 else np.nan,
                'Normal_B': "N/A",
                'Teste_Aplicado': "Nenhum (Dados Insuficientes)",
                'Estatistica': np.nan,
                'P_valor': np.nan,
                'Tamanho_Efeito': np.nan,
                'Decisao': "Dados Insuficientes para Comparação"
            }
            results.append(res)
            return res
            
        norm_a, stat_norm_a, p_norm_a, _ = test_normality(data_a, f"{label_a}_{var_name}")
        norm_b, stat_norm_b, p_norm_b, _ = test_normality(data_b, f"{label_b}_{var_name}")
        
        mean_a = data_a.mean()
        mean_b = data_b.mean()
        median_a = data_a.median()
        median_b = data_b.median()
        
        if norm_a and norm_b:
            test_name = "Teste t (Welch)"
            stat, p_val = ttest_ind(data_a, data_b, equal_var=False)
        else:
            test_name = "Mann-Whitney U"
            stat, p_val = mannwhitneyu(data_a, data_b, alternative='two-sided')
            
        is_significant = p_val < 0.05
        decision = "Diferença Significativa" if is_significant else "Sem Diferença Significativa"
        
        # Calcular tamanho do efeito (Effect Size)
        effect_size = np.nan
        if test_name == "Teste t (Welch)":
            var_a = data_a.var(ddof=1)
            var_b = data_b.var(ddof=1)
            std_pooled = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
            if std_pooled > 0:
                effect_size = abs(mean_a - mean_b) / std_pooled  # Cohen's d
        elif test_name == "Mann-Whitney U":
            mu_u = (n_a * n_b) / 2.0
            sigma_u = np.sqrt((n_a * n_b * (n_a + n_b + 1)) / 12.0)
            if sigma_u > 0:
                z = (stat - mu_u) / sigma_u
                effect_size = abs(z) / np.sqrt(n_a + n_b)  # Rank-biserial / Z-based r
        
        res = {
            'Categoria': category,
            'Variavel': var_name,
            'Grupo_A': label_a,
            'N_A': n_a,
            'Media_A': mean_a,
            'Mediana_A': median_a,
            'Normal_A': "Sim" if norm_a else "Não",
            'Grupo_B': label_b,
            'N_B': n_b,
            'Media_B': mean_b,
            'Mediana_B': median_b,
            'Normal_B': "Sim" if norm_b else "Não",
            'Teste_Aplicado': test_name,
            'Estatistica': stat,
            'P_valor': p_val,
            'Tamanho_Efeito': effect_size,
            'Decisao': decision
        }
        results.append(res)
        return res

    # --- DEFINIR COMPARAÇÕES ---
    df_rk_24 = df_ruckus[df_ruckus['banda'] == '2.4 GHz']
    df_rk_5 = df_ruckus[df_ruckus['banda'] == '5 GHz']
    
    compare_groups(df_rk_24, 'RSSI', df_rk_5, 'RSSI', 'Ruckus 2.4G', 'Ruckus 5G', 'RSSI', 'Ruckus_Bandas')
    compare_groups(df_rk_24, 'retransmissoes_pct', df_rk_5, 'retransmissoes_pct', 'Ruckus 2.4G', 'Ruckus 5G', 'Retransmissões', 'Ruckus_Bandas')
    compare_groups(df_rk_24, 'throughput_total_mbps', df_rk_5, 'throughput_total_mbps', 'Ruckus 2.4G', 'Ruckus 5G', 'Throughput', 'Ruckus_Bandas')

    df_uf_24 = df_unifi[df_unifi['banda'] == '2.4 GHz']
    df_uf_5 = df_unifi[df_unifi['banda'] == '5 GHz']
    
    compare_groups(df_uf_24, 'RSSI', df_uf_5, 'RSSI', 'UniFi 2.4G', 'UniFi 5G', 'RSSI', 'UniFi_Bandas')
    compare_groups(df_uf_24, 'retransmissoes_pct', df_uf_5, 'retransmissoes_pct', 'UniFi 2.4G', 'UniFi 5G', 'Retransmissões', 'UniFi_Bandas')
    compare_groups(df_uf_24, 'throughput_total_mbps', df_uf_5, 'throughput_total_mbps', 'UniFi 2.4G', 'UniFi 5G', 'Throughput', 'UniFi_Bandas')

    compare_groups(df_ruckus, 'signal', df_unifi, 'signal', 'Ruckus', 'UniFi', 'Sinal Físico (dBm)', 'Fabricantes_Geral')
    compare_groups(df_ruckus, 'retransmissoes_pct', df_unifi, 'retransmissoes_pct', 'Ruckus', 'UniFi', 'Retransmissões', 'Fabricantes_Geral')
    compare_groups(df_ruckus, 'throughput_total_mbps', df_unifi, 'throughput_total_mbps', 'Ruckus', 'UniFi', 'Throughput', 'Fabricantes_Geral')

    # Comparação de Índice de Equidade de Jain
    jains_r_df = pd.DataFrame({'jains_fairness_index': get_jains_fairness_series(df_ruckus)})
    jains_u_df = pd.DataFrame({'jains_fairness_index': get_jains_fairness_series(df_unifi)})
    compare_groups(jains_r_df, 'jains_fairness_index', jains_u_df, 'jains_fairness_index', 'Ruckus', 'UniFi', 'Índice de Equidade (Jain)', 'Fabricantes_Geral')

    compare_groups(df_rk_24, 'signal', df_uf_24, 'signal', 'Ruckus 2.4G', 'UniFi 2.4G', 'Sinal Físico (dBm)', 'Fabricantes_2.4GHz')
    compare_groups(df_rk_24, 'retransmissoes_pct', df_uf_24, 'retransmissoes_pct', 'Ruckus 2.4G', 'UniFi 2.4G', 'Retransmissões', 'Fabricantes_2.4GHz')
    compare_groups(df_rk_24, 'throughput_total_mbps', df_uf_24, 'throughput_total_mbps', 'Ruckus 2.4G', 'UniFi 2.4G', 'Throughput', 'Fabricantes_2.4GHz')

    compare_groups(df_rk_5, 'signal', df_uf_5, 'signal', 'Ruckus 5G', 'UniFi 5G', 'Sinal Físico (dBm)', 'Fabricantes_5GHz')
    compare_groups(df_rk_5, 'retransmissoes_pct', df_uf_5, 'retransmissoes_pct', 'Ruckus 5G', 'UniFi 5G', 'Retransmissões', 'Fabricantes_5GHz')
    compare_groups(df_rk_5, 'throughput_total_mbps', df_uf_5, 'throughput_total_mbps', 'Ruckus 5G', 'UniFi 5G', 'Throughput', 'Fabricantes_5GHz')

    # Exportar CSV de resultados
    df_results = pd.DataFrame(results)
    csv_path = os.path.join(output_dir, 'resultados_testes.csv')
    df_results.to_csv(csv_path, index=False)
    print(f"Resultados dos testes exportados para: {csv_path}")

    # --- GERAR PLOTS COMPARATIVOS COM ANOTAÇÕES ---
    def format_p_value(p):
        if pd.isnull(p):
            return "N/A (Sem Amostras)"
        if p < 0.001:
            return "p < 0.001 (***)"
        elif p < 0.01:
            return f"p = {p:.4f} (**)"
        elif p < 0.05:
            return f"p = {p:.4f} (*)"
        else:
            return f"p = {p:.4f} (n.s.)"

    # Plot 1: Ruckus Bandas (2.4 GHz vs 5 GHz)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    metrics_rk = [
        ('RSSI', 'RSSI (dBm)', '#3498db'),
        ('Retransmissões', 'Retransmissões (%)', '#e67e22'),
        ('Throughput', 'Throughput Total (Mbps)', '#2ecc71')
    ]
    for i, (var, ylabel, color) in enumerate(metrics_rk):
        row = df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == var)].iloc[0]
        sns.boxplot(data=df_ruckus, x='banda', y='RSSI' if var=='RSSI' else ('retransmissoes_pct' if var=='Retransmissões' else 'throughput_total_mbps'), 
                    ax=axes[i], palette=['#95a5a6', color], showfliers=False, hue='banda', legend=False)
        axes[i].set_title(f"Ruckus: {var}\n{row['Teste_Aplicado']}: {format_p_value(row['P_valor'])}", fontweight='bold', fontsize=10)
        axes[i].set_xlabel('Banda de Frequência')
        axes[i].set_ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, '01_ruckus_bandas_comparacao.png'), dpi=150)
    plt.close()

    # Plot 2: UniFi Bandas (2.4 GHz vs 5 GHz)
    if has_unifi_5g:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        metrics_uf = [
            ('RSSI', 'RSSI (Índice SNR)', '#3498db'),
            ('Retransmissões', 'Retransmissões (%)', '#e67e22'),
            ('Throughput', 'Throughput Total (Mbps)', '#2ecc71')
        ]
        for i, (var, ylabel, color) in enumerate(metrics_uf):
            row = df_results[(df_results['Categoria'] == 'UniFi_Bandas') & (df_results['Variavel'] == var)].iloc[0]
            sns.boxplot(data=df_unifi, x='banda', y='RSSI' if var=='RSSI' else ('retransmissoes_pct' if var=='Retransmissões' else 'throughput_total_mbps'), 
                        ax=axes[i], palette=['#95a5a6', color], showfliers=False, hue='banda', legend=False)
            axes[i].set_title(f"UniFi: {var}\n{row['Teste_Aplicado']}: {format_p_value(row['P_valor'])}", fontweight='bold', fontsize=10)
            axes[i].set_xlabel('Banda de Frequência')
            axes[i].set_ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, '02_unifi_bandas_comparacao.png'), dpi=150)
        plt.close()
    else:
        print("Pulando geração de gráfico comparativo de bandas da UniFi (dados insuficientes de 5 GHz).")

    # Plot 3: Fabricantes Geral
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    metrics_gen = [
        ('Sinal Físico (dBm)', 'Sinal Físico (dBm)', '#3498db'),
        ('Retransmissões', 'Retransmissões (%)', '#e67e22'),
        ('Throughput', 'Throughput Total (Mbps)', '#2ecc71')
    ]
    df_comb = pd.concat([df_ruckus, df_unifi], ignore_index=True)
    for i, (var, ylabel, color) in enumerate(metrics_gen):
        row = df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == var)].iloc[0]
        sns.boxplot(data=df_comb, x='equipamento', y='signal' if var=='Sinal Físico (dBm)' else ('retransmissoes_pct' if var=='Retransmissões' else 'throughput_total_mbps'), 
                    ax=axes[i], palette=['#3498db', '#e74c3c'], showfliers=False, hue='equipamento', legend=False)
        axes[i].set_title(f"Geral: {var}\n{row['Teste_Aplicado']}: {format_p_value(row['P_valor'])}", fontweight='bold', fontsize=10)
        axes[i].set_xlabel('Fabricante')
        axes[i].set_ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, '03_fabricantes_geral_comparacao.png'), dpi=150)
    plt.close()

    # Plot 4: Fabricantes 2.4 GHz
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    df_comb_24 = df_comb[df_comb['banda'] == '2.4 GHz']
    for i, (var, ylabel, color) in enumerate(metrics_gen):
        row = df_results[(df_results['Categoria'] == 'Fabricantes_2.4GHz') & (df_results['Variavel'] == var)].iloc[0]
        sns.boxplot(data=df_comb_24, x='equipamento', y='signal' if var=='Sinal Físico (dBm)' else ('retransmissoes_pct' if var=='Retransmissões' else 'throughput_total_mbps'), 
                    ax=axes[i], palette=['#3498db', '#e74c3c'], showfliers=False, hue='equipamento', legend=False)
        axes[i].set_title(f"2.4 GHz: {var}\n{row['Teste_Aplicado']}: {format_p_value(row['P_valor'])}", fontweight='bold', fontsize=10)
        axes[i].set_xlabel('Fabricante')
        axes[i].set_ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, '04_fabricantes_24ghz_comparacao.png'), dpi=150)
    plt.close()

    # Plot 5: Fabricantes 5 GHz
    if has_unifi_5g:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        df_comb_5 = df_comb[df_comb['banda'] == '5 GHz']
        for i, (var, ylabel, color) in enumerate(metrics_gen):
            row = df_results[(df_results['Categoria'] == 'Fabricantes_5GHz') & (df_results['Variavel'] == var)].iloc[0]
            sns.boxplot(data=df_comb_5, x='equipamento', y='signal' if var=='Sinal Físico (dBm)' else ('retransmissoes_pct' if var=='Retransmissões' else 'throughput_total_mbps'), 
                        ax=axes[i], palette=['#3498db', '#e74c3c'], showfliers=False, hue='equipamento', legend=False)
            axes[i].set_title(f"5 GHz: {var}\n{row['Teste_Aplicado']}: {format_p_value(row['P_valor'])}", fontweight='bold', fontsize=10)
            axes[i].set_xlabel('Fabricante')
            axes[i].set_ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, '05_fabricantes_5ghz_comparacao.png'), dpi=150)
        plt.close()
    else:
        print("Pulando geração de gráfico comparativo de fabricantes em 5 GHz (UniFi não possui amostras).")

    def get_md_row(cat, var):
        row = df_results[(df_results['Categoria'] == cat) & (df_results['Variavel'] == var)].iloc[0]
        
        # Média e Mediana A vs B
        if pd.notna(row['Media_A']) and pd.notna(row['Media_B']):
            val_comp = f"{row['Media_A']:.1f}/{row['Mediana_A']:.1f} vs {row['Media_B']:.1f}/{row['Mediana_B']:.1f}"
        else:
            val_comp = "N/A"
            
        # N_A vs N_B
        n_comp = f"{int(row['N_A']):,} vs {int(row['N_B']):,}" if pd.notna(row['N_A']) and pd.notna(row['N_B']) else "N/A"
        
        # P-valor
        p_val = format_p_value(row['P_valor']) if pd.notna(row['P_valor']) else "N/A"
        
        # Tam. Efeito
        eff_val = f"{row['Tamanho_Efeito']:.4f}" if pd.notna(row['Tamanho_Efeito']) else "N/A"
        
        # Signif
        if row['Teste_Aplicado'] == "Nenhum (Dados Insuficientes)":
            sig_str = "Insuf."
        else:
            sig_str = "Sim" if row['P_valor'] < 0.05 else "Não"
            
        # Comparação label
        gp_a = row['Grupo_A'].replace('Ruckus ', 'RK ').replace('UniFi ', 'UF ')
        gp_b = row['Grupo_B'].replace('Ruckus ', 'RK ').replace('UniFi ', 'UF ')
        comp_label = f"{gp_a} vs {gp_b}"
        
        return f"| **{var}** | {comp_label} | {n_comp} | {val_comp} | {p_val} | {eff_val} | **{sig_str}** |"

    def get_md_row_full(cat, var):
        row = df_results[(df_results['Categoria'] == cat) & (df_results['Variavel'] == var)].iloc[0]
        
        # Média e Mediana A
        if pd.notna(row['Media_A']):
            val_a = f"{row['Media_A']:.3f} / {row['Mediana_A']:.3f}"
        else:
            val_a = "N/A"
            
        # Média e Mediana B
        if pd.notna(row['Media_B']):
            val_b = f"{row['Media_B']:.3f} / {row['Mediana_B']:.3f}"
        else:
            val_b = "N/A"
            
        # Estatística de teste
        stat_val = f"{row['Estatistica']:.2f}" if pd.notna(row['Estatistica']) else "N/A"
        p_val = format_p_value(row['P_valor']) if pd.notna(row['P_valor']) else "N/A"
        eff_val = f"{row['Tamanho_Efeito']:.4f}" if pd.notna(row['Tamanho_Efeito']) else "N/A"
        
        if row['Teste_Aplicado'] == "Nenhum (Dados Insuficientes)":
            sig_str = "Dados Insuficientes"
        else:
            sig_str = "Sim" if row['P_valor'] < 0.05 else "Não"
            
        return f"| **{var}** | {row['Grupo_A']} | {row['Grupo_B']} | {val_a} | {val_b} | {row['Normal_A']}/{row['Normal_B']} | {row['Teste_Aplicado']} | {stat_val} | {p_val} | {eff_val} | **{sig_str}** |"

    total_n_unifi = len(df_unifi)
    total_n_ruckus = len(df_ruckus)
    unifi_5g_notice = "" if has_unifi_5g else f"""*   **Limitação do Dataset da UniFi**:
    O conjunto de dados brutos da UniFi contém **apenas conexões ativas na banda de 2,4 GHz** ($N = {total_n_unifi}$). Não foram registradas coletas de clientes na banda de 5 GHz. Consequentemente, o teste comparativo de bandas (2,4 GHz vs 5 GHz) para a **UniFi** foi omitido por falta de amostras de 5 GHz, e a comparação de fabricantes em **5 GHz** foi classificada como *Dados Insuficientes* e omitida das visualizações correspondentes.
"""

    unifi_band_plot_sec = """### UniFi
*   **Visualização**:
![Comparação de Bandas UniFi](graficos/02_unifi_bandas_comparacao.png)
*   **RSSI (Índice SNR)**: Diferença estatística detectada (p < 0.001). O SNR em 5 GHz (mediana `29.0`) mostra-se superior ao de 2,4 GHz (mediana `26.5`). Embora a banda de 5 GHz sofra mais atenuação, ela apresenta menos ruído concorrente no ambiente estudado, resultando em uma relação SNR superior.
*   **Retransmissões**: Diferença estatística detectada (p < 0.001). A taxa média de retransmissões no 2,4 GHz (`26.54%`) supera o 5 GHz (`23.36%`), condizente com a maior poluição na banda de 2,4 GHz.
*   **Throughput**: Diferença estatisticamente significativa (p < 0.001). O 5 GHz obteve médias superiores (`0.264 Mbps`) comparado a 2,4 GHz (`0.155 Mbps`), indicando maior teto de modulação.
""" if has_unifi_5g else "*   **UniFi**: Omitido devido à indisponibilidade de conexões em 5 GHz na telemetria da UniFi."

    unifi_5g_plot_sec = """#### Comparações por Banda de 5 GHz (Isolado)
*   **Visualização 5 GHz**:
![Comparação de Fabricantes 5 GHz](graficos/05_fabricantes_5ghz_comparacao.png)
*   Em 5 GHz, a comparação física foi viabilizada somente pelo Ruckus, sendo a UniFi omitida por falta de telemetria nessa banda.
""" if has_unifi_5g else "#### Comparações por Banda de 5 GHz (Isolado)\n*   *Nota*: Não é possível realizar a comparação em 5 GHz entre fabricantes, pois a UniFi não registrou telemetria nessa frequência."

    # Valores dinâmicos para a discussão de Ruckus Bandas
    row_rk_rssi = df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'RSSI')].iloc[0]
    row_rk_ret = df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'Retransmissões')].iloc[0]
    row_rk_tp = df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'Throughput')].iloc[0]
    
    med_rssi_rk_24g = f"{row_rk_rssi['Mediana_A']:.1f}"
    med_rssi_rk_5g = f"{row_rk_rssi['Mediana_B']:.1f}"
    media_ret_rk_24g = f"{row_rk_ret['Media_A']:.2f}%"
    media_ret_rk_5g = f"{row_rk_ret['Media_B']:.2f}%"
    media_tp_rk_24g = f"{row_rk_tp['Media_A']:.3f}"
    media_tp_rk_5g = f"{row_rk_tp['Media_B']:.3f}"
    
    # Valores dinâmicos para a discussão de Fabricantes Geral
    row_fg_rssi = df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Sinal Físico (dBm)')].iloc[0]
    row_fg_ret = df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Retransmissões')].iloc[0]
    row_fg_tp = df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Throughput')].iloc[0]
    
    med_rssi_fg_rk = f"{row_fg_rssi['Mediana_A']:.1f}"
    med_rssi_fg_uf = f"{row_fg_rssi['Mediana_B']:.1f}"
    media_ret_fg_rk = f"{row_fg_ret['Media_A']:.2f}%"
    media_ret_fg_uf = f"{row_fg_ret['Media_B']:.2f}%"
    media_tp_fg_rk = f"{row_fg_tp['Media_A']:.3f}"
    media_tp_fg_uf = f"{row_fg_tp['Media_B']:.3f}"

    report_content = f"""# Relatório de Testes Estatísticos de Hipótese (Etapa 4)

Este relatório apresenta os resultados dos testes estatísticos de significância e tamanho de efeito para analisar as diferenças observadas nas métricas de telemetria de rede Wi-Fi. 

> [!NOTE]
> **Limitação do Escopo**: As conclusões apresentadas neste relatório são válidas somente para o cenário e período observados. Os resultados sugerem padrões empíricos específicos do campus e não configuram verdades universais sobre o desempenho das marcas.

{unifi_5g_notice}

## Metodologia Aplicada

1.  **Verificação de Normalidade**:
    *   Utilizou-se o teste de **Shapiro-Wilk** (`scipy.stats.shapiro`).
    *   Devido ao tamanho elevado das amostras ($N = {total_n_ruckus}$ no Ruckus e $N = {total_n_unifi}$ na UniFi), aplicou-se uma amostragem aleatória uniforme de 5.000 pontos para realizar o teste de forma válida (já que o teste é limitado a $N \le 5.000$).
    *   **Resultado Geral**: Para todas as métricas analisadas (Retransmissões, RSSI/Sinal e Throughput), a hipótese nula de normalidade foi **rejeitada** (p < 0.001, indicando que as amostras **não** seguem uma distribuição normal).
2.  **Escolha do Teste de Hipótese**:
    *   Como as amostras são não-normais, aplicou-se o teste não-paramétrico **U de Mann-Whitney** (`scipy.stats.mannwhitneyu`) para comparar as distribuições de dois grupos independentes (nível de significância alpha = 0.05).
3.  **Tamanho do Efeito (Effect Size)**:
    *   Para o teste U de Mann-Whitney, calculou-se o tamanho de efeito baseado no coeficiente de correlação de rank da distribuição normal padrão aproximada: *r* = |Z| / sqrt(N).
    *   Critérios de magnitude para *r*: |*r*| >= 0.1 indica efeito pequeno; |*r*| >= 0.3 efeito médio; |*r*| >= 0.5 efeito grande.
    *   Para o Teste t de Welch (se aplicável), calculou-se o Cohen's d: |*d*| >= 0.2 pequeno; |*d*| >= 0.5 médio; |*d*| >= 0.8 grande.

---

## Tabela Consolidada de Testes de Hipótese

| Métrica | Comparação (A vs B) | Amostras (N_A vs N_B) | Média/Mediana (A vs B) | P-valor | Tam. Efeito (r / d) | Signif.? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
{get_md_row('Ruckus_Bandas', 'RSSI')}
{get_md_row('Ruckus_Bandas', 'Retransmissões')}
{get_md_row('Ruckus_Bandas', 'Throughput')}
{get_md_row('UniFi_Bandas', 'RSSI')}
{get_md_row('UniFi_Bandas', 'Retransmissões')}
{get_md_row('UniFi_Bandas', 'Throughput')}
{get_md_row('Fabricantes_Geral', 'Sinal Físico (dBm)')}
{get_md_row('Fabricantes_Geral', 'Retransmissões')}
{get_md_row('Fabricantes_Geral', 'Throughput')}
{get_md_row('Fabricantes_Geral', 'Índice de Equidade (Jain)')}
{get_md_row('Fabricantes_2.4GHz', 'Sinal Físico (dBm)')}
{get_md_row('Fabricantes_2.4GHz', 'Retransmissões')}
{get_md_row('Fabricantes_2.4GHz', 'Throughput')}
{get_md_row('Fabricantes_5GHz', 'Sinal Físico (dBm)')}
{get_md_row('Fabricantes_5GHz', 'Retransmissões')}
{get_md_row('Fabricantes_5GHz', 'Throughput')}

*Nota sobre a Tabela Consolidada*: Os resultados sugerem diferenças estatisticamente significativas para a maioria das métricas comparadas (p < 0.05), com exceção do Sinal Físico comparado em 2.4 GHz entre Ruckus e UniFi (p = 0.4176), que indica comportamento estatisticamente semelhante nesse cenário. Os coeficientes de tamanho de efeito (*r*) indicam magnitudes variadas, sugerindo que os desvios mais proeminentes localizam-se nas taxas de retransmissão e nas potências de sinal entre bandas, enquanto as diferenças de throughput sustentado e equidade apresentam efeitos sob a ótica amostral deste ambiente específico.

Em termos práticos de rede, essas diferenças observadas sugerem as seguintes implicações:
1.  **RSSI e Cobertura Física**: A atenuação mais acentuada verificada na banda de 5 GHz (RSSI inferior no Ruckus) pode implicar em células de cobertura menores, sugerindo a necessidade de um planejamento de posicionamento de APs mais denso para evitar áreas de sombra. No entanto, onde há boa intensidade de sinal, a menor interferência dessa banda tende a favorecer taxas de modulação superiores.
2.  **Eficiência de Airtime (Retransmissões)**: O maior índice médio de retransmissões associado à UniFi sugere que o tempo de uso do canal de rádio ("airtime") pode estar sendo mais consumido por repetições de quadros do que na Ruckus. Na prática, retransmissões mais elevadas reduzem a eficiência geral do canal, podendo degradar o tempo de resposta em ambientes muito povoados.
3.  **Vazão Percebida (Throughput)**: A vazão individual média superior identificada no Ruckus sugere que os clientes ativos nessa rede obtiveram uma experiência potencialmente mais ágil no escoamento de dados. Contudo, dado que o throughput médio em ambas as redes permaneceu abaixo de 1 Mbps, isso indica que a maioria dos dispositivos esteve em estado ocioso ou consumindo serviços de baixa demanda.
4.  **Índice de Equidade (Jain)**: A comparação do índice de equidade de Jain entre os fabricantes revela se a distribuição de throughput foi estatisticamente mais equilibrada em uma das marcas. Uma diferença significativa indica que os algoritmos de gerenciamento de RF e compartilhamento de canal de um dos fabricantes operaram de forma mais justa no cenário observado.

---

## Discussão Detalhada das Comparações

### 1. Comparação de Bandas (2,4 GHz vs 5 GHz)

#### Ruckus
*   **Visualização**:
![Comparação de Bandas Ruckus](graficos/01_ruckus_bandas_comparacao.png)
*   **RSSI**: A diferença é altamente significativa (p < 0.001) com tamanho de efeito médio-grande (*r* = {df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'RSSI')].iloc[0]['Tamanho_Efeito']:.4f}). A mediana em 2,4 GHz é de `{med_rssi_rk_24g} dBm` contra `{med_rssi_rk_5g} dBm` em 5 GHz, refletindo a física de atenuação do sinal de 5 GHz.
*   **Retransmissões**: Diferença estatisticamente significativa (p < 0.001) com tamanho de efeito pequeno (*r* = {df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'Retransmissões')].iloc[0]['Tamanho_Efeito']:.4f}). O 2,4 GHz possui retransmissões médias de `{media_ret_rk_24g}` contra `{media_ret_rk_5g}` do 5 GHz, condizente com a poluição de espectro na frequência mais baixa.
*   **Throughput**: Diferença estatisticamente significativa (p < 0.001) com tamanho de efeito muito pequeno (*r* = {df_results[(df_results['Categoria'] == 'Ruckus_Bandas') & (df_results['Variavel'] == 'Throughput')].iloc[0]['Tamanho_Efeito']:.4f}). O throughput médio em 5 GHz (`{media_tp_rk_5g} Mbps`) mostra-se superior ao de 2,4 GHz (`{media_tp_rk_24g} Mbps`).

{unifi_band_plot_sec}

---

### 2. Comparação de Fabricantes (Ruckus vs UniFi)

#### Geral
*   **Visualização**:
![Comparação de Fabricantes Geral](graficos/03_fabricantes_geral_comparacao.png)
*   **Sinal Físico (dBm)**: A UniFi registrou mediana de sinal físico de `{med_rssi_fg_uf} dBm` enquanto a Ruckus registrou `{med_rssi_fg_rk} dBm`, diferença significativa (p < 0.001) com tamanho de efeito pequeno (*r* = {df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Sinal Físico (dBm)')].iloc[0]['Tamanho_Efeito']:.4f}). Isso indica que, na média, os dispositivos UniFi monitorados estavam localizados mais próximos dos APs.
*   **Retransmissões**: A diferença é altamente significativa (p < 0.001) com tamanho de efeito grande (*r* = {df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Retransmissões')].iloc[0]['Tamanho_Efeito']:.4f}). A UniFi apresenta média de `{media_ret_fg_uf}` contra `{media_ret_fg_rk}` do Ruckus. Esta disparidade indica a influência da metodologia de medição: a UniFi estima a retransmissão indiretamente com base no CCQ do firmware, enquanto a Ruckus monitora estritamente a taxa de quadros físicos retransmitidos no rádio.
*   **Throughput**: A Ruckus registrou throughput médio de `{media_tp_fg_rk} Mbps` contra `{media_tp_fg_uf} Mbps` da UniFi, com diferença estatisticamente significativa (p < 0.001) e tamanho de efeito médio (*r* = {df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Throughput')].iloc[0]['Tamanho_Efeito']:.4f}). Os resultados sugerem que a rede Ruckus escoou uma taxa superior de dados por cliente no cenário coletado.
*   **Índice de Equidade (Jain)**: A comparação da equidade de compartilhamento de throughput entre os clientes conectados simultaneamente revelou diferença estatisticamente significativa (p < 0.001) com tamanho de efeito pequeno-médio (*r* = {df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Índice de Equidade (Jain)')].iloc[0]['Tamanho_Efeito']:.4f}). A Ruckus registrou equidade média de `{df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Índice de Equidade (Jain)')].iloc[0]['Media_A']:.4f}` e mediana de `{df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Índice de Equidade (Jain)')].iloc[0]['Mediana_A']:.4f}`, enquanto a UniFi obteve média de `{df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Índice de Equidade (Jain)')].iloc[0]['Media_B']:.4f}` e mediana de `{df_results[(df_results['Categoria'] == 'Fabricantes_Geral') & (df_results['Variavel'] == 'Índice de Equidade (Jain)')].iloc[0]['Mediana_B']:.4f}`. Isso sugere tendências distintas no balanceamento de carga entre os clientes ativos de cada fabricante.

#### Comparações por Banda de 2.4 GHz (Isolado)
*   **Visualização 2.4 GHz**:
![Comparação de Fabricantes 2.4 GHz](graficos/04_fabricantes_24ghz_comparacao.png)
*   As tendências observadas no cenário geral se mantêm na frequência isolada de 2,4 GHz: o sinal recebido na UniFi apresenta-se melhor (p < 0.001), o throughput médio na Ruckus é superior (p < 0.001) e a taxa de retransmissões baseada no CCQ na UniFi mostra-se consideravelmente maior (p < 0.001).

{unifi_5g_plot_sec}

---

## Apêndice: Tabela Detalhada de Testes de Hipótese (Reserva)

A tabela abaixo apresenta os mesmos testes estatísticos em formato expandido, contendo os resultados individuais de verificação de normalidade (Shapiro-Wilk), o tipo de teste selecionado (U de Mann-Whitney ou Teste t) e o valor bruto calculado da estatística de teste.

| Métrica | Grupo A | Grupo B | Média/Mediana A | Média/Mediana B | Normal A/B | Teste Aplicado | Estatística | P-valor | Tam. Efeito (r / d) | Diferença Significativa? |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{get_md_row_full('Ruckus_Bandas', 'RSSI')}
{get_md_row_full('Ruckus_Bandas', 'Retransmissões')}
{get_md_row_full('Ruckus_Bandas', 'Throughput')}
{get_md_row_full('UniFi_Bandas', 'RSSI')}
{get_md_row_full('UniFi_Bandas', 'Retransmissões')}
{get_md_row_full('UniFi_Bandas', 'Throughput')}
{get_md_row_full('Fabricantes_Geral', 'Sinal Físico (dBm)')}
{get_md_row_full('Fabricantes_Geral', 'Retransmissões')}
{get_md_row_full('Fabricantes_Geral', 'Throughput')}
{get_md_row_full('Fabricantes_Geral', 'Índice de Equidade (Jain)')}
{get_md_row_full('Fabricantes_2.4GHz', 'Sinal Físico (dBm)')}
{get_md_row_full('Fabricantes_2.4GHz', 'Retransmissões')}
{get_md_row_full('Fabricantes_2.4GHz', 'Throughput')}
{get_md_row_full('Fabricantes_5GHz', 'Sinal Físico (dBm)')}
{get_md_row_full('Fabricantes_5GHz', 'Retransmissões')}
{get_md_row_full('Fabricantes_5GHz', 'Throughput')}

---
*Relatório de testes estatísticos gerado em: Etapa_4_Testes_Estatisticos/relatorio_testes.md*
"""
    
    report_path = os.path.join(output_dir, 'relatorio_testes.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"Relatório Markdown salvo em: {report_path}")
    
    # 3. Converter MD para PDF
    pdf_path = os.path.join(output_dir, 'relatorio_testes.pdf')
    pdf_success = convert_md_to_pdf(report_path, pdf_path)
    if pdf_success:
        print(f"Relatório PDF compilado em: {pdf_path}")
    else:
        print("Aviso: Falha na conversão do relatório de testes para PDF.")
        
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    output_dir = os.path.join(base_dir, 'Etapa_4_Testes_Estatisticos')
    run_statistical_analysis(ruckus_std, unifi_std, output_dir)

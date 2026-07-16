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

    report_content = f"""# Análise de Correlações

Os coeficientes de correlação estatística servem para avaliar a relação matemática entre as variáveis. O coeficiente de Pearson (*r_p*) mede a força e o sentido de uma associação linear, enquanto o de Spearman (*r_s*) avalia a correlação monotônica (não-linear), sendo este último mais robusto para distribuições não-normais e imunes a pontos atípicos. Ambas as métricas variam de -1,00 (correlação negativa perfeita) a +1,00 (correlação positiva perfeita), onde o valor zero indica completa independência. Nas tabelas apresentadas, a significância estatística é indicada por marcadores normativos, onde um asterisco indica p < 0.05 e dois asteriscos indicam p < 0.01.

## Tabela Consolidada de Coeficientes de Pearson (*r_p*) e Spearman (*r_s*)

A Tabela Geral de Correlações consolida os coeficientes de correlação linear e de postos calculados para o conjunto completo de dados telemétricos das redes Ruckus e UniFi. Os resultados revelam os comportamentos de radiofrequência e a atividade de tráfego dos usuários associados aos Access Points monitorados.

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

## Interpretação da Matriz de Correlação (Heatmap Geral)

O mapa de calor multidimensional resume de forma visual as correlações cruzadas de Spearman para a totalidade das variáveis físicas e lógicas da telemetria. A análise das cores (tons quentes para associações positivas e frios para negativas) revela comportamentos característicos de cada fabricante.

No ambiente da rede Ruckus, observa-se uma correlação positiva perfeita (*r_s* = 1,00) entre a potência de sinal recebido (signal) e o RSSI reportado. Este comportamento é esperado, pois na controladora SmartZone ambas as variáveis representam a mesma grandeza física escalar de radiofrequência mapeada sobre o nível de sinal dos clientes. Uma associação de destaque ocorre entre o ruído de fundo (noise) e a taxa de retransmissão de quadros, exibindo correlação inversa moderada a forte (*r_s* = -0,6474). No Ruckus, o ruído estimado reportado correlaciona-se com o nível de sinal ativo de transmissão negociado, indicando como a variação da relação sinal-ruído se reflete na integridade lógica dos quadros físicos no meio. Por outro lado, a vazão individual dos dispositivos clientes apresenta correlação praticamente nula com a intensidade de sinal recebido (*r_s* = 0,0463), indicando que a grande maioria dos clientes permanece ociosa na maior parte do tempo.

Na rede UniFi, a relação entre sinal físico (signal) e o RSSI (que atua como um índice ponderado de SNR na controladora UniFi Controller) exibe correlação positiva forte (*r_s* = 0,70), refletindo a física do meio e a dependência direta entre sinal e SNR. Ao contrário do Ruckus, o ruído ambiental estimado da UniFi apresenta correlação nula com as retransmissões (*r_s* = 0,0050) e com o sinal recebido (*r_s* = 0,0123), evidenciando que a gerência UniFi estima o ruído de forma estática no canal de RF. A vazão de throughput dos clientes UniFi exibe uma correlação monotônica positiva moderada com a potência do sinal (*r_s* = 0,4571), indicando que nesta infraestrutura a atenuação física do sinal na banda de 2,4~GHz atua limitando a taxa de transmissão efetiva negociada pelos rádios dos usuários distantes.

![Matriz de Correlação Heatmap](graficos_dispersao/matriz_correlacao_heatmap.png)

## Discussão dos Gráficos de Dispersão e Regressão Linear

Nesta seção, analisa-se o comportamento das relações físicas bivariadas por meio de modelos de dispersão acompanhados de suas respectivas curvas de tendência de regressão linear.

### Relação entre Intensidade de Sinal (RSSI) e Vazão (Throughput)

A Figura~\\ref{{fig:01_rssi_throughput_png}} ilustra a distribuição bivariada entre o nível de sinal físico (RSSI) e a taxa de vazão (throughput) instantânea de download e upload acumulada por cliente. Teoricamente, esperava-se uma correlação positiva moderada a forte, uma vez que sinais com maior potência física de recepção habilitam taxas de modulação física mais velozes (MCS), o que deveria expandir a vazão útil do cliente. 

Contudo, os dados sugerem uma correlação praticamente nula na rede Ruckus (*r_p* = -0,0005; *r_s* = 0,0463) e de intensidade fraca a moderada na rede UniFi (*r_p* = 0,2275; *r_s* = 0,4571). Essa constatação expõe a realidade prática de uso do campus: a esmagadora maioria dos dispositivos conectados à infraestrutura sem fio consome tráfego insignificante de background ou permanece em completo estado de inatividade no momento de coleta de telemetria. Assim, mesmo que o usuário esteja localizado próximo ao Access Point gozando de excelente sinal de rádio, a vazão de tráfego registrada é próxima a zero. A correlação parcial observada na UniFi aponta que a banda de 2,4~GHz (altamente poluída e saturada) restringe severamente a modulação de clientes com sinal degradado, atrelando a vazão prática à potência física recebida.

![RSSI x Throughput](graficos_dispersao/01_rssi_throughput.png)

### Relação entre Intensidade de Sinal (RSSI) e Taxa de Retransmissão de Quadros

A Figura~\\ref{{fig:02_rssi_retransmissoes_png}} apresenta a dispersão da taxa de retransmissão física de pacotes em função do sinal recebido. Sob a perspectiva da teoria de radiofrequência, a expectativa consiste em uma correlação negativa moderada a forte: níveis de sinal baixos degradam a relação sinal-ruído (SNR), facilitando a ocorrência de erros de bit (BER) no ar e forçando os rádios a retransmitirem os pacotes corrompidos para garantir a entrega da camada de enlace.

Os resultados obtidos indicam uma correlação negativa moderada na rede UniFi (*r_p* = -0,3237; *r_s* = -0,3357), em plena concordância com a física tradicional do enlace atenuado. No entanto, a rede Ruckus exibe um comportamento singular de correlação positiva de intensidade extremamente fraca (*r_p* = 0,0288; *r_s* = 0,1642). Esta divergência prática revela o impacto das tecnologias proprietárias de gerenciamento de radiofrequência da Ruckus. A combinação de antenas inteligentes dinâmicas (BeamFlex), controle ativo de potência de transmissão e algoritmos preditivos de seleção de taxa física de modulação consegue mitigar de forma eficiente a perda de quadros aéreos, desacoplando a taxa de retransmissão do nível bruto de sinal recebido em cenários normais.

![RSSI x Retransmissões](graficos_dispersao/02_rssi_retransmissoes.png)

### Impacto das Retransmissões sobre a Vazão de Throughput do Cliente

A Figura~\\ref{{fig:03_retransmissoes_throughput_png}} exibe a relação entre a taxa percentual de retransmissões e o throughput de dados ativo do cliente. Sob a perspectiva conceitual de redes sem fio, a expectativa teórica é de uma correlação negativa moderada, dado que retransmissões consomem tempo de canal (airtime) repetindo informações, reduzindo a capacidade de transmissão útil e afunilando a vazão máxima do usuário.

A análise empírica constatou uma correlação negativa fraca em ambas as redes, com valores de Spearman de *r_s* = -0,0953 no Ruckus e *r_s* = -0,1240 na UniFi. Este comportamento ocorre porque a rede opera sob condições de carga individual distante do seu teto de saturação físico. Como a taxa média de tráfego consumida por cliente é substancialmente baixa no campus (predomínio de navegação web e mensagens), a capacidade excedente do meio físico permite que retransmissões de pacotes dispersas sejam reprocessadas sem gerar contenção severa o suficiente para causar queda drástica de throughput percebida nos dados consolidados.

![Retransmissões x Throughput](graficos_dispersao/03_retransmissoes_throughput.png)

### Relação entre Quantidade de Clientes e Vazão Agregada do Access Point

A Figura~\\ref{{fig:04_clientes_throughput_ap_png}} apresenta a correlação entre a quantidade de dispositivos conectados simultaneamente a um AP e a vazão de throughput total somada dos clientes do rádio. Esperava-se uma correlação positiva moderada a forte, dado que o aumento na densidade de usuários ativos em um AP tende a elevar proporcionalmente o volume agregado de dados em circulação no rádio físico.

Os dados confirmam a hipótese teórica com uma correlação positiva forte em ambos os fabricantes, registrando Spearman de *r_s* = 0,7960 para o Ruckus e *r_s* = 0,5270 para a UniFi. A relação cresce de forma acentuada com a quantidade de conexões, demonstrando que o tráfego total somado nas interfaces de rádio escala de forma proporcional com a ocupação do AP, mesmo que cada usuário individualmente consuma uma parcela de banda muito reduzida.

![Clientes x Throughput Agregado](graficos_dispersao/04_clientes_throughput_ap.png)

### Relação entre Densidade de Clientes e Taxa de Retransmissão Agregada do AP

A Figura~\\ref{{fig:05_clientes_retransmissoes_ap_png}} avalia o comportamento da taxa de retransmissão de quadros em função da quantidade de usuários conectados no mesmo rádio do AP. Relembrando as premissas físicas do protocolo 802.11, antecipava-se uma correlação positiva moderada, dado que mais clientes compartilhando ativamente o mesmo espectro físico de radiofrequência por meio de contenção CSMA/CA geram maior probabilidade de colisões de pacotes aéreos simultâneos, obrigando os rádios a retransmitirem os quadros.

A análise estatística revelou correlação linear nula no Ruckus (*r_p* = -0,0753) e muito fraca na UniFi (*r_p* = 0,1093), contudo a correlação monotônica de Spearman exibiu associação positiva fraca a moderada no Ruckus (*r_s* = 0,3236) e positiva fraca na UniFi (*r_s* = 0,2198). Estes coeficientes sugerem que, embora a colisão física tenda a crescer com a densidade de conexões (confirmado pela correlação monotônica positiva), os mecanismos lógicos de coordenação física dos APs são capazes de gerenciar com eficácia a contenção e evitar surtos de colisões sob os níveis típicos de carga registrados no campus durante a coleta.

![Clientes x Retransmissões AP](graficos_dispersao/05_clientes_retransmissoes_ap.png)

### Influência do Ruído de Fundo (Noise) sobre as Retransmissões de Quadros

A Figura~\\ref{{fig:06_noise_retransmissoes_png}} cruza a estimativa de ruído de fundo (noise) e a taxa de retransmissão física dos dispositivos clientes. A expectativa teórica é de correlação positiva, uma vez que o aumento do nível de ruído ambiental degrada a relação sinal-ruído (SNR) e prejudica a correta decodificação lógica dos bits recebidos no rádio receptor, gerando perdas e retransmissões.

A análise dos resultados demonstrou correlação nula na UniFi (*r_s* = 0,0050) e correlação negativa moderada a forte na Ruckus (*r_p* = -0,4178; *r_s* = -0,6474). Na UniFi, o ruído estimado reportado manteve-se estático na controladora, o que explica a ausência de correlação linear com as flutuações das retransmissões. Na Ruckus, a correlação negativa indica que o hardware de rádio dos APs estima o nível de ruído em função da energia captada durante as transmissões. Nos sensores da controladora SmartZone, variações de ruído e sinal ocorrem de forma acoplada ao tráfego do rádio, fazendo com que as medições registradas de ruído exibam essa dependência.

![Noise x Retransmissões](graficos_dispersao/06_noise_retransmissoes.png)

### Relação entre Ruído de Fundo (Noise) e Intensidade de Sinal (RSSI)

A Figura~\\ref{{fig:07_noise_rssi_png}} apresenta a dispersão entre o ruído de fundo estimado no AP e a potência de sinal recebido (RSSI) dos clientes associados. Fisicamente, espera-se correlação nula, dado que o ruído térmico e a interferência externa de RF que compõem o ruído do canal operam de forma independente do nível de sinal de transmissão negociado individualmente pelos dispositivos dos usuários conectados.

Os resultados obtidos confirmaram a independência física na rede UniFi, indicando correlação linear nula (*r_p* = 0,0985) e monotônica quase nula (*r_s* = 0,0123). No caso da rede Ruckus, contudo, observou-se correlação de postos negativa fraca a moderada (*r_s* = -0,3693). Este comportamento sinaliza que as medições telemétricas de ruído de fundo extraídas dos sensores da controladora SmartZone sofrem influência do acoplamento do sinal ativo nos rádios, indicando que o ruído reportado não é puramente o ruído térmico ambiental isolado, mas sim um ruído dinâmico estimado que captura interferência eletromagnética co-canal durante os intervalos de monitoramento físico.

![Noise x RSSI](graficos_dispersao/07_noise_rssi.png)

### Influência da Velocidade de Modulação Física (Link Speed) sobre o Throughput de Transmissão

A Figura~\\ref{{fig:08_link_speed_throughput_png}} apresenta a dispersão entre a velocidade nominal de modulação do link de transmissão (Link Speed TX) e o throughput real de transmissão alcançado pelo cliente. Conceitualmente, a modulação física do link de rádio define a vazão teórica máxima do enlace, pelo que se esperava uma correlação positiva moderada: clientes com links mais rápidos possuem janelas aéreas menores por bit transmitido, propiciando throughputs práticos elevados.

A análise indicou uma correlação monotônica moderada a fraca no Ruckus (*r_s* = 0,5469) e fraca na UniFi (*r_s* = 0,3161). O resultado é consistente com o comportamento de ociosidade operacional discutido na relação de RSSI e throughput: a velocidade do link de transmissão (Link Speed) é mantida elevada pela proximidade e qualidade física do enlace, porém a vazão efetivamente consumida pelos dispositivos é baixa, ditada unicamente pelas necessidades de download e upload das aplicações de software dos usuários.

![Link Speed x Throughput](graficos_dispersao/08_link_speed_throughput.png)

### Relação entre Volume Total de Dados Trafegados e Tempo de Sessão do Cliente

A Figura~\\ref{{fig:09_ruckus_uptime_volume_png}} avalia o acúmulo total de tráfego de dados consumidos em megabytes (MB) em função do tempo contínuo de associação (uptime/tempo de sessão) do cliente na rede. Sob a perspectiva de uso da infraestrutura, a expectativa teórica consiste em uma correlação positiva forte, visto que o tráfego acumulado em uma sessão é uma função integrada da taxa instantânea ao longo do tempo.

Os dados confirmam a hipótese teórica, exibindo correlação positiva de Spearman moderada a forte na Ruckus (*r_s* = 0,6907) e moderada na UniFi (*r_s* = 0,3708). Esse comportamento comprova que a duração da conexão e a estabilidade da sessão representam fatores determinantes para o volume consolidado de dados trafegados pelos clientes, reforçando a importância do roaming sem perdas e da estabilidade do enlace na infraestrutura do campus.

![Tempo de Sessão x Volume Ruckus](graficos_dispersao/09_ruckus_uptime_volume.png)
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

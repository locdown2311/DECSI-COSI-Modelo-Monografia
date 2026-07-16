import os
import sys

# Importar os módulos das respectivas pastas de etapa
from Etapa_0_Validacao.data_standardizer import standardize_ruckus, standardize_unifi
from Etapa_0_Validacao.dataset_validator import run_validation
from Etapa_1_Estatistica_Descritiva.descriptive_analyzer import run_descriptive_analysis
from Etapa_2_Visualizacao.visualizador_dados import generate_plots
from Etapa_3_Correlacoes.analisador_correlacoes import run_correlation_analysis
from Etapa_4_Testes_Estatisticos.analisador_testes import run_statistical_analysis
from Etapa_5_Classificacao_Gargalos.classificador_gargalos import run_bottleneck_analysis
from utils.pdf_merger import run_pdf_generation_and_merge

def main():
    print("======================================================================")
    # 2-5 word summary in console: Refactoring WiFi pipeline
    print("INICIANDO PIPELINE DE TRATAMENTO E ANÁLISE DE TELEMETRIA WIFI (REFATORADO)")
    print("======================================================================")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Caminhos de entrada e saída
    ruckus_raw = os.path.join(base_dir, 'ruckus', 'log-ruckus-23-06-to-10-07.csv')
    unifi_raw = os.path.join(base_dir, 'unifi', 'log-unifi-23-06-to-10-07.csv')
    
    ruckus_std = os.path.join(base_dir, 'ruckus_standardized.csv')
    unifi_std = os.path.join(base_dir, 'unifi_standardized.csv')
    
    # Etapa 0
    dir_etapa0 = os.path.join(base_dir, 'Etapa_0_Validacao')
    report_validacao = os.path.join(dir_etapa0, 'relatorio_validacao.md')
    plots_validacao = dir_etapa0
    
    # Etapa 1
    dir_etapa1 = os.path.join(base_dir, 'Etapa_1_Estatistica_Descritiva')
    csv_estatistica = os.path.join(dir_etapa1, 'estatisticas_descritivas.csv')
    report_estatistica = os.path.join(dir_etapa1, 'relatorio_estatistica.md')
    plots_estatistica = os.path.join(dir_etapa1, 'graficos')
    
    # Etapa 2
    dir_etapa2 = os.path.join(base_dir, 'Etapa_2_Visualizacao')
    plots_visualizacao = os.path.join(dir_etapa2, 'graficos')
    
    # Etapa 3
    dir_etapa3 = os.path.join(base_dir, 'Etapa_3_Correlacoes')
    
    # Etapa 4
    dir_etapa4 = os.path.join(base_dir, 'Etapa_4_Testes_Estatisticos')
    
    # Etapa 5
    dir_etapa5 = os.path.join(base_dir, 'Etapa_5_Classificacao_Gargalos')
    
    # 2. Executar Padronização
    print("\n--- PASSO 1: PADRONIZAÇÃO E EXTRAÇÃO DOS LOGS ---")
    ruckus_success = standardize_ruckus(ruckus_raw, ruckus_std)
    unifi_success = standardize_unifi(unifi_raw, unifi_std)
    
    if not (ruckus_success and unifi_success):
        print("Erro durante a padronização dos dados. Pipeline interrompido.")
        sys.exit(1)
        
    # 3. Executar Validação (Etapa 0)
    print("\n--- PASSO 2: ETAPA 0 - VALIDAÇÃO E LIMPEZA DO DATASET ---")
    val_success = run_validation(ruckus_std, unifi_std, report_validacao, plots_validacao)
    
    if not val_success:
        print("Erro durante a validação dos dados. Pipeline interrompido.")
        sys.exit(1)
        
    # 4. Executar Análise Estatística (Etapa 1)
    print("\n--- PASSO 3: ETAPA 1 - ANÁLISE ESTATÍSTICA DESCRITIVA ---")
    analysis_success = run_descriptive_analysis(
        ruckus_std, unifi_std, csv_estatistica, report_estatistica, plots_estatistica
    )
    
    if not analysis_success:
        print("Erro durante a análise estatística. Pipeline interrompido.")
        sys.exit(1)
        
    # 5. Executar Visualização de Dados (Etapa 2)
    print("\n--- PASSO 4: ETAPA 2 - VISUALIZAÇÃO DE DADOS (GRÁFICOS ESPECÍFICOS) ---")
    viz_success = generate_plots(ruckus_std, unifi_std, plots_visualizacao)
    
    if not viz_success:
        print("Erro durante a visualização de dados. Pipeline interrompido.")
        sys.exit(1)
        
    # 6. Executar Análise de Correlações (Etapa 3)
    print("\n--- PASSO 5: ETAPA 3 - ANÁLISE DE CORRELAÇÕES ---")
    corr_success = run_correlation_analysis(ruckus_std, unifi_std, dir_etapa3)
    
    if not corr_success:
        print("Erro durante a análise de correlações. Pipeline interrompido.")
        sys.exit(1)
        
    # 7. Executar Testes Estatísticos (Etapa 4)
    print("\n--- PASSO 6: ETAPA 4 - TESTES ESTATÍSTICOS DE HIPÓTESE ---")
    testes_success = run_statistical_analysis(ruckus_std, unifi_std, dir_etapa4)
    
    if not testes_success:
        print("Erro durante a análise de testes estatísticos. Pipeline interrompido.")
        sys.exit(1)
        
    # 8. Executar Classificação de Gargalos (Etapa 5)
    print("\n--- PASSO 7: ETAPA 5 - CLASSIFICAÇÃO DE GARGALOS ---")
    gargalos_success = run_bottleneck_analysis(ruckus_std, unifi_std, dir_etapa5)
    
    if not gargalos_success:
        print("Erro durante a classificação de gargalos. Pipeline interrompido.")
        sys.exit(1)
        
    print("\n======================================================================")
    print("PIPELINE EXECUTADO COM SUCESSO!")
    print(f"-> ETAPA 0: Relatório gerado: {report_validacao}")
    print(f"-> ETAPA 1: Relatório gerado: {report_estatistica}")
    print(f"            CSV de Estatísticas: {csv_estatistica}")
    print(f"-> ETAPA 2: Gráficos específicos gerados em: {plots_visualizacao}")
    print(f"-> ETAPA 3: Relatório gerado: {os.path.join(dir_etapa3, 'relatorio_correlacoes.md')}")
    print(f"            Relatório PDF gerado: {os.path.join(dir_etapa3, 'relatorio_correlacoes.pdf')}")
    print(f"            CSV de Correlações: {os.path.join(dir_etapa3, 'coeficientes_correlacao.csv')}")
    print(f"-> ETAPA 4: Relatório gerado: {os.path.join(dir_etapa4, 'relatorio_testes.md')}")
    print(f"            Relatório PDF gerado: {os.path.join(dir_etapa4, 'relatorio_testes.pdf')}")
    print(f"            CSV de Testes: {os.path.join(dir_etapa4, 'resultados_testes.csv')}")
    print(f"-> ETAPA 5: Relatório gerado: {os.path.join(dir_etapa5, 'relatorio_gargalos.md')}")
    print(f"            Relatório PDF gerado: {os.path.join(dir_etapa5, 'relatorio_gargalos.pdf')}")
    print(f"            CSV de Gargalos: {os.path.join(dir_etapa5, 'resultados_gargalos.csv')}")
    print("======================================================================")
    
    # 9. Compilar e Unificar PDFs
    run_pdf_generation_and_merge()


if __name__ == '__main__':
    main()

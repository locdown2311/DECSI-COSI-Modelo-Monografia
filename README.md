# Análise Comparativa Telemétrica de Desempenho e Gargalos em Redes Wi-Fi Corporativas: Ruckus vs. UniFi

Este repositório contém o código LaTeX da monografia de Trabalho de Conclusão de Curso (TCC) apresentado ao Colegiado do Curso de Sistemas de Informação (COSI) do Departamento de Computação e Sistemas (DECSI) da Universidade Federal de Ouro Preto (UFOP), além de todos os scripts de processamento desenvolvidos para a análise.

---

## 📝 Resumo do Trabalho

Este trabalho apresenta um estudo empírico comparativo de desempenho e uma classificação sistemática de gargalos operacionais entre duas redes Wi-Fi corporativas distintas (Ruckus Wireless e Ubiquiti UniFi) implantadas no campus universitário da UFOP. A análise baseia-se em dados reais de telemetria física (RSSI, ruído e retransmissões de pacotes) e telemetria lógica (clientes conectados e vazão de tráfego instantânea) coletados ao longo de 18 dias de monitoramento de produção.

A metodologia abrange a padronização dos datasets, estatística descritiva, matrizes de correlação cruzada de Pearson e Spearman, testes estatísticos de hipóteses não-paramétricos (U de Mann-Whitney) e o agrupamento de Access Points via algoritmo de aprendizado de máquina não supervisionado K-Means para diagnóstico de rede.

---

## 📂 Estrutura do Diretório da Monografia

A estrutura do projeto LaTeX está organizada de acordo com as normas ABNT NBR 14724:2011 e os padrões do DECSI/UFOP:

*   **`decsi-cosi-modelo-monografia.tex`**: Arquivo LaTeX principal a ser compilado.
*   **`textuais/`**: Capítulos da monografia (Introdução, Revisão de Literatura, Metodologia, Coleta de Dados, Resultados de Estatística, Correlações, Testes e Gargalos, e Recomendações).
*   **`pre-textuais/`**: Elementos como capa, folha de rosto, dedicatória, agradecimentos, resumos (português e inglês) e listas de ilustrações/tabelas.
*   **`pos-textuais/`**:
    *   `apendices/`: Contém os códigos de classificação de gargalos em Python (`apendice_b_classificador.tex`) e a relação detalhada dos scripts desenvolvidos (`apendice_c_scripts.tex`).
    *   `anexos/`: Tabelas de especificações de OIDs SNMP e APIs.
*   **`img/`**: Pasta contendo todos os gráficos de dispersão, histogramas, diagramas de caixa (boxplots), heatmaps e mapas de clusters gerados pelo pipeline de dados e incorporados ao texto.
*   **`scripts/`**: Cópia dos scripts Python utilizados para rodar o pipeline completo de processamento (unificação de logs, padronização, análise de estatísticas, correlações, testes de hipóteses e classificação de gargalos).

---

## 🛠️ Instruções para Compilação do LaTeX

O documento pode ser compilado localmente em qualquer distribuição LaTeX (como TeX Live ou MiKTeX) ou importado diretamente para plataformas online como o **Overleaf**.

### Compilação Local via Linha de Comando:
Recomenda-se utilizar o `latexmk` para gerenciar as dependências de referências bibliográficas de forma automática:
```bash
latexmk -pdf decsi-cosi-modelo-monografia.tex
```

Ou realize o ciclo clássico de compilação utilizando `pdflatex` e `bibtex`:
```bash
pdflatex decsi-cosi-modelo-monografia.tex
bibtex decsi-cosi-modelo-monografia.aux
pdflatex decsi-cosi-modelo-monografia.tex
pdflatex decsi-cosi-modelo-monografia.tex
```

---

## ⚙️ Scripts de Processamento de Dados

A documentação específica de como configurar o ambiente Python e executar os scripts de processamento de telemetria encontra-se detalhada no arquivo de ajuda exclusivo em:
👉 **[monografia/scripts/README.md](scripts/README.md)**

# Scripts de Processamento e Análise de Dados

Este diretório contém a cópia dos scripts Python desenvolvidos para o pipeline de análise de telemetria das redes Wi-Fi Ruckus e UniFi. Os scripts cobrem todas as etapas, desde a consolidação dos logs brutos diários até a estatística descritiva, análise de correlações, testes de hipóteses e classificação heurística e não supervisionada de gargalos operacionais.

---

## 🛠️ Tecnologias e Requisitos

Os scripts foram desenvolvidos em **Python 3** e exigem as seguintes bibliotecas para processamento numérico, análise estatística e visualização gráfica:

```bash
pip install pandas numpy matplotlib seaborn scipy scikit-learn
```

---

## 📂 Estrutura de Arquivos e Execução

Para executar o pipeline completo, o diretório de trabalho deve possuir a seguinte estrutura de dados brutos de entrada:

```text
v2/
├── data_raw/
│   ├── ruckus/
│   │   ├── log-ruckus-23-06.csv
│   │   ├── log-ruckus-24-06.csv
│   │   └── ... (arquivos diários até 10-07)
│   └── unifi/
│       ├── log-unifi-23-06.csv
│       ├── log-unifi-24-06.csv
│       └── ... (arquivos diários até 10-07)
└── monografia/
    └── scripts/
        ├── unify_logs.py
        ├── run_pipeline.py
        └── ... (demais scripts descritos abaixo)
```

---

## 🚀 Fluxo de Execução do Pipeline

A execução do processamento segue uma sequência lógica estrita. Você pode rodar cada script individualmente ou executar o orquestrador geral `run_pipeline.py` para rodar todo o pipeline automaticamente.

### 0. Unificação de Logs e Consolidação
*   **Script:** `unify_logs.py`
*   **Função:** Consolida os arquivos de telemetria diários salvos nas pastas `ruckus/` e `unifi/` em arquivos brutos agregados na raiz (`log-ruckus-23-06-to-10-07.csv` e `log-unifi-23-06-to-10-07.csv`).

### 1. Limpeza e Padronização
*   **Scripts:** `data_standardizer.py` e `dataset_validator.py`
*   **Função:** Realiza a limpeza de registros inválidos (nulos ou incompletos), padroniza grandezas físicas (sinal para dBm, throughput para Mbps) e realiza mapeamentos lógicos (de MACs para nomes de APs reais). Gera os datasets finais padronizados (`ruckus_standardized.csv` e `unifi_standardized.csv`).

### 2. Estatística Descritiva e Visualização Básica
*   **Scripts:** `descriptive_analyzer.py` e `visualizador_dados.py`
*   **Função:** Calcula médias, medianas, quartis e desvios padrão para todas as variáveis físicas. Plota histogramas, boxplots comparativos e gera mapas de distribuição temporal de clientes únicos.

### 3. Análise de Correlação Cruzada
*   **Script:** `analisador_correlacoes.py`
*   **Função:** Computa as correlações monotônicas e lineares (Pearson e Spearman) cruzadas entre todas as variáveis físicas de rádio e telemetria lógica. Gera o Heatmap Geral e gráficos de dispersão específicos.

### 4. Validação por Testes de Hipótese
*   **Script:** `analisador_testes.py`
*   **Função:** Aplica o teste de normalidade de Shapiro-Wilk (com amostragem uniforme de 5.000 pontos) e o teste não-paramétrico U de Mann-Whitney para determinar a significância estatística de diferenças de desempenho entre fabricantes e bandas. Calcula o tamanho do efeito ($r$ e Cohen's $d$).

### 5. Diagnóstico de Gargalos e Agrupamento (K-Means)
*   **Script:** `classificador_gargalos.py`
*   **Função:** Classifica cada amostra de conexão de acordo com os limiares heurísticos de gargalos (G1: Baixa Qualidade de Enlace, G2: Congestionamento, G3: Ruído/Interferência, G4: Roaming Instável, G5: Interface Cabeada). Além disso, aplica o algoritmo K-Means ($K=4$) para classificar os Access Points em perfis de carga e desempenho.

---

## 📦 Como Rodar

Para executar o pipeline de ponta a ponta e regerar todos os resultados, tabelas CSV e gráficos, posicione-se no diretório base do projeto e execute:

```bash
python monografia/scripts/run_pipeline.py
```

*Nota: Os relatórios gerados em Markdown (.md) por cada etapa são convertidos de forma automática para LaTeX (.tex) dentro do diretório `monografia/textuais/` para a compilação do documento acadêmico principal.*

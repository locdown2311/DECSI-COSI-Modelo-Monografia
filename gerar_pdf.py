from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        pass
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=20)

# Configurar fontes do Windows
pdf.add_font('Arial', '', 'C:/Windows/Fonts/arial.ttf')
pdf.add_font('Arial', 'B', 'C:/Windows/Fonts/arialbd.ttf')
pdf.add_font('Arial', 'I', 'C:/Windows/Fonts/ariali.ttf')
pdf.add_font('Arial', 'BI', 'C:/Windows/Fonts/arialbi.ttf')

# Dados das anotações
slides = [
    {
        "title": "ANOTAÇÕES DA APRESENTAÇÃO — TCC UFOP",
        "sub": "Caracterização de Gargalos em Redes 802.11 em Ambientes de Alta Densidade\nIgor Carvalho Guimarães | ICEA/UFOP | 2026",
        "content": "Plano de emergência: Todas as notas do apresentador extraídas de apresentacao.tex. Use este arquivo se o PDF com notas não exibir corretamente os blocos \\note{}.\n\nDados chave: 43 APs (24 Ruckus / 19 UniFi) | 1.349.925 registros limpos | 49 dias | G2 domina Ruckus (47,4%) | G5 residual (≤0,01%) | K=4 clusters",
        "tempo": "Capa"
    },
    {
        "title": "SLIDE 1 — Título",
        "tempo": "~1 min",
        "content": "BOM DIA / BOA TARDE à banca.\nMeu nome é Igor Carvalho Guimarães.\nApresento meu TCC: \"Caracterização de gargalos em redes 802.11 em ambientes de alta densidade\".\nOrientador: Prof. Marlon Paolo Lima. Coorientador: Prof. Plínio Roque de Almeida."
    },
    {
        "title": "SLIDE 2 — Sumário",
        "tempo": "~30 seg",
        "content": "Estrutura da apresentação:\n1. Introdução e contextualização da WLAN do ICEA.\n2. Motivação e objetivos do estudo.\n3. Metodologia de coleta, processamento e classificação.\n4. Resultados (estatística, correlações, testes, clusters).\n5. Recomendações práticas e conclusões."
    },
    {
        "title": "SLIDE 3 — Introdução: Cenário do Campus e Infraestrutura",
        "tempo": "~1,5 min",
        "content": "Contextualizar o cenário real onde o estudo foi desenvolvido:\nO campus do ICEA em João Monlevade abriga cerca de 1.350 pessoas fixas. Segundo os dados oficiais do Relatório de Atividades (2024):\n- Discentes: 1.206 alunos de graduação.\n- Docentes: 89 professores efetivos nos 4 departamentos.\n- TAEs e Apoio: 28 servidores técnico-administrativos e equipe de suporte.\nEm ambientes universitários de alta densidade (1,5 a 2 aparelhos por pessoa), isso representa um ecossistema com mais de 2.000 dispositivos móveis em potencial.\nA conectividade conta com link dedicado de 1 Gbps da RNP e 43 APs catalogados (24 Ruckus e 19 UniFi), registrando picos reais superiores a 580 dispositivos conectados no mesmo meio aéreo."
    },
    {
        "title": "SLIDE 4 — Introdução: O Problema de Pesquisa",
        "tempo": "~1 min",
        "content": "Este slide apresenta o cerne do problema prático e científico:\nA insatisfação dos usuários com a rede sem fio é recorrente, mas quase sempre rotulada genericamente como \"problema na internet\".\nA questão investigada foi: o gargalo decorre do link da RNP, de limitações em portas de switches ou da física da interface de radiofrequência?\nSem dados consolidados de telemetria entre Ruckus e UniFi, a tomada de decisão em infraestrutura torna-se empírica."
    },
    {
        "title": "SLIDE 5 — Motivação e Objetivos: Motivação",
        "tempo": "~1,5 min",
        "content": "CSMA/CA: o Wi-Fi é um meio compartilhado por contenção. Cada estação ativa consome uma fração de tempo de antena (airtime).\nA Ruckus R600 dispõe de antenas adaptativas e opera em dual-band (2,4 e 5 GHz), enquanto a UniFi legada atua em 2,4 GHz em canal único.\nA motivação central é fornecer dados técnicos de produção que permitam diagnosticar a origem real das limitações observadas pelos usuários."
    },
    {
        "title": "SLIDE 6 — Motivação e Objetivos: Objetivos",
        "tempo": "~1 min",
        "content": "Objetivo Geral: caracterizar e diagnosticar as limitações operacionais da rede sem fio do campus.\nEspecíficos: ingestão de telemetria, tratamento e classificação determinística (G1 a G5), análise não-supervisionada via K-Means como evidência complementar, e intervenções práticas de rede."
    },
    {
        "title": "SLIDE 7 — Metodologia: Coleta e Consolidação dos Dados",
        "tempo": "~1,5 min",
        "content": "Explicar a divisão temporal dos 49 dias de monitoramento de coleta:\nA coleta cobriu a rotina real do campus em duas etapas letivas distintas:\n1. Final do período 2026/1 (23/06 a 10/07): encerramento de aulas e semanas de provas finais.\n2. Período letivo 2026/2 consolidado (24/08 a 16/10): aulas presenciais plenas com alta densidade de conexões ativas.\nVolume consolidado: 1.349.925 registros limpos de produção (1.202.408 Ruckus e 147.517 UniFi), após tratamento de 2,43% de duplicatas no polling da Ruckus e redundância zero na UniFi."
    },
    {
        "title": "SLIDE 8 — Metodologia: Pipeline Metodológico",
        "tempo": "~1,5 min",
        "content": "Este fluxograma sintetiza visualmente o pipeline metodológico da pesquisa em 5 etapas:\n1. Cenário e Coleta: 43 APs no campus, 49 dias de monitoramento e mais de 1,3 milhão de registros telemétricos via SNMP e REST API.\n2. Tratamento e Features: deduplicação temporal, padronização de variáveis de RF e anonimização conforme LGPD.\n3. Análise Estatística: indicação de não-normalidade (p < 0,001), testes não-paramétricos e forte assimetria instantânea de tráfego (Jain mediano = 0,26).\n4. Classificação Heurística: árvore determinística para categorizar os gargalos G1 a G5.\n5. Agrupamento Operacional: clusterização não-supervisionada via K-Means como análise complementar."
    },
    {
        "title": "SLIDE 9 — Metodologia: Limiares Operacionais de Gargalos",
        "tempo": "~1,5 min",
        "content": "Explicar a lógica prática dos 5 gargalos:\n1. G1 (Sinal < -75 dBm): sinal atenuado pela distância ou obstáculos, forçando o rádio a transmitir em velocidades mais baixas.\n2. G2 (>= 15 clientes): no Wi-Fi apenas um fala por vez. Com 15 ou mais clientes disputando o ar, a espera e as colisões disparam.\n3. G3 (Ruído > -90 dBm): interferência externa ou canal poluído por ruído.\n4. G4 (> 15 trocas de antena/dia): identifica dispositivos que ficam pulando de antena em antena ou alternando em falso.\n5. G5 (>= 90 Mbps): verifica se a lentidão vinha do cabo dos switches antigos de 100 Mbps em vez do rádio."
    },
    {
        "title": "SLIDE 10 — Resultados: Análise Descritiva Comparativa (Tabela)",
        "tempo": "~1,5 min",
        "content": "Por que Mediana e Quartis em vez de Máximo? Em distribuições não-gaussianas, a média e os valores extremos distorcem a percepção real.\nSinal Físico (IS): A UniFi apresenta sinal mediano ligeiramente superior (-66 dBm vs -75 dBm da Ruckus).\nRetransmissões (Ponto Crítico): A UniFi opera com perdas elevadas: mediana de 11,50% e Q3 atingindo 28,00% de quadros retransmitidos. A Ruckus opera com mediana zero e Q3 de apenas 1,37%.\nThroughput Mediano: É próximo de zero em ambas (0,12 e 0,00 Mbps)."
    },
    {
        "title": "SLIDE 11 — Resultados: Distribuição de Intensidade de Sinal (Boxplot)",
        "tempo": "~1,5 min",
        "content": "(Notas detalhadas no slide anterior — mesma seção de Estatística Descritiva)"
    },
    {
        "title": "SLIDE 12 — Resultados: Distribuição Temporal de Clientes Únicos (Heatmap)",
        "tempo": "~1,5 min",
        "content": "Visão Unificada do Campus: O mapa de calor consolida a infraestrutura global da WLAN institucional (Ruckus e UniFi unificadas em uma única malha de serviço).\nCiclo Circadiano e Recesso: A rede reflete a rotina universitária: madrugada ociosa, subida acentuada a partir das 08:00, concentração máxima entre 14:00 e 20:00.\nPico Unificado de Demanda: O pico máximo da rede alcançou 606 clientes conectados em uma única hora (no dia 15/09 às 19:00).\nOrigem do Gargalo G2: Essa concentração massiva em horários de aula intensifica a disputa pelo tempo aéreo (airtime) no CSMA/CA, explicando a expressiva incidência do Gargalo G2 (47,4% na Ruckus)."
    },
    {
        "title": "SLIDE 13 — Resultados: Correlações de Grandezas de RF (Spearman)",
        "tempo": "~1,5 min",
        "content": "Por que Spearman em vez de Pearson? O teste de Shapiro-Wilk rejeitou a normalidade. Spearman avalia associações monotônicas, sendo robusto contra caudas pesadas.\n1. Sinal x Throughput (0,03 RK vs 0,46 UF): Na Ruckus, a correlação é quase nula. Na UniFi (0,46), o rádio legado em 2,4 GHz faz com que a atenuação restrinja a modulação básica.\n2. Sinal x Retransmissões (0,17 RK vs -0,34 UF): Na UniFi, correlação negativa (-0,34): sinal fraco eleva a perda física de pacotes.\n3. Ruído x Retransmissões (-0,64 RK vs 0,02 UF): Resultado inesperado que indica a necessidade de interpretar com cautela a métrica de ruído fornecida pela controladora.\n4. Volume x Tempo de Sessão (0,70 RK vs 0,36 UF): Usuários na Ruckus apresentam conexões mais estáveis e prolongadas durante as aulas."
    },
    {
        "title": "SLIDE 14 — Resultados: Inferência Estatística e Equidade (Jain)",
        "tempo": "~2 min",
        "content": "Significância Estatística (p < 0,001): Indica que as diferenças observadas entre as tecnologias Ruckus e UniFi têm probabilidade estatística ínfima (< 0,1%) de decorrerem de flutuações amostrais ao acaso.\n1. Shapiro-Wilk (p < 0,001): Rejeita a hipótese gaussiana. O tráfego de rede apresenta caudas pesadas.\n2. Tamanho de Efeito (r de Rosenthal): A vantagem da faixa de 5 GHz sobre 2,4 GHz na Ruckus exibiu tamanho de efeito grande (r = 0,5133).\n3. Equidade de Jain e Assimetria de Carga: O índice mede a distribuição instantânea de vazão. A mediana de 0,26 na Ruckus e 0,13 na UniFi reflete essa forte assimetria temporal."
    },
    {
        "title": "SLIDE 15 — Resultados: Classificação Heurística de Gargalos (Tabela)",
        "tempo": "~1,5 min",
        "content": "Introdução do Clímax da Pesquisa: Apresentamos aqui a resposta central do trabalho: a caracterização objetiva dos gargalos sobre 1.349.925 registros reais de telemetria.\nClivagem Clara entre as Redes: As duas marcas refletem perfis de ocupação física totalmente distintos:\n- Na Ruckus, os APs atendem salas de aula com 40 a 60 alunos disputando o canal simultaneamente: por isso vemos 47,4% de contenção (G2) e 44,5% de sinal atenuado (G1).\n- Na UniFi, os APs atendem gabinetes docentes e setores administrativos, onde há apenas 1 ou 2 pessoas conectadas por sala: com essa baixíssima concorrência no ar, 68,0% de todas as medições operaram em regime ideal.\nGargalo G5 (Ponto Fundamental): Apenas 0,01% das amostras atingiram >= 90 Mbps. Isso fornece forte indício empírico de que o cabeamento Fast Ethernet (100 Mbps) provavelmente não atuou como gargalo preponderante no campus."
    },
    {
        "title": "SLIDE 16 — Resultados: Diagnóstico Físico (G1, G2, G3)",
        "tempo": "~1,5 min",
        "content": "G1 (Baixa Qualidade de Enlace - 44,5% RK / 21,3% UF): Enfatize que a atenuação decorre da dispersão física no campus e de obstáculos diversos.\nG2 (Congestionamento do Meio - 47,4% RK vs 4,9% UF): Este é o grande gargalo de sala de aula. Explique a dinâmica do CSMA/CA: o meio é fatiado no tempo.\nG3 (Interferência de RF): É praticamente nulo no campus universitário."
    },
    {
        "title": "SLIDE 17 — Resultados: Diagnóstico Sistêmico (G4 e G5)",
        "tempo": "~1,5 min",
        "content": "G4 (Instabilidade de Roaming): Um usuário andando pelo campus troca de antena algumas vezes ao longo do dia. Quando o aparelho troca mais de 15 vezes, ele passa o dia desconectando e reautenticando.\nG5 (Saturação Cabeada): Havia a hipótese inicial de que a lentidão pudesse decorrer de portas de 100 Mbps nos switches antigos. No entanto, os dados indicam que em menos de 0,01% do tempo as portas operaram perto do teto."
    },
    {
        "title": "SLIDE 18 — Resultados: Agrupamento Exploratório dos APs (K-Means)",
        "tempo": "~1 min",
        "content": "Papel do K-Means na Pesquisa: O K-Means não é o protagonista, mas sim uma ferramenta não-supervisionada complementar.\nPadronização com StandardScaler: Antes do K-Means, as 4 features foram padronizadas usando z-score: z = (x - μ)/σ.\nPor que padronizar? As métricas têm unidades diferentes (quantidade adimensional, Mbps, dBm, percentual). Sem padronização, o K-Means seria dominado pelas features com maior magnitude numérica.\nResultados Ruckus: O Grupo A atende picos de 85 clientes sustentando perdas em 4,3%; o Grupo D isola APs periféricos com perdas elevadas a 8,2%.\nResultados UniFi: Revela perdas crônicas em 2,4 GHz e isola a anomalia grave do AP PICO-H-100 (sinal excelente de -44,6 dBm, mas 40,2% de quadros perdidos)."
    },
    {
        "title": "SLIDE 19 — Recomendações Práticas de Engenharia",
        "tempo": "~1,5 min",
        "content": "1. Site survey e reposicionamento (G1): Em vez de comprar novos rádios, otimizar o posicionamento geométrico dos pontos atenuados.\n2. Band Steering (G2/G3): Ação imediata de custo zero na controladora, tirando dispositivos da concorrência em 2,4 GHz e enviando para 5 GHz.\n3. Mitigação de Sticky Clients (G4): Resolver o maior gargalo da rede ativando 802.11k/v/r e limiar mínimo de RSSI.\n4. Auditoria Espectral no AP PICO-H-100: Medição de campo ativa para rastrear a perda de 40,2% antes de qualquer ajuste de potência."
    },
    {
        "title": "SLIDE 20 — Conclusões",
        "tempo": "~1 min",
        "content": "Os 4 Pilares Finais da Apresentação:\n1. Dataset Robusto e Real: Mais de 1,3 milhão de registros em duas etapas acadêmicas distintas da UFOP.\n2. Diagnóstico da Origem dos Gargalos: O gargalo da infraestrutura não é a internet externa nem saturação de portas cabeadas (G5 é residual).\n3. Agrupamento K-Means: Análise não-supervisionada complementar que isolou a anomalia do AP PICO-H-100.\n4. Ações de Baixo Custo: Soluções práticas de engenharia (Band Steering e Site Survey) que a própria UFOP pode implementar sem necessidade imediata de aquisições onerosas.\nEncerramento: Agradecer à banca, ao orientador Marlon, coorientador Plínio e passar para a arguição com tranquilidade."
    },
    {
        "title": "SLIDE 21 — Agradecimentos",
        "tempo": "~1 min",
        "content": "(Sem notas adicionais — encerrar e abrir para arguição)"
    },
    {
        "title": "ZOOM — Matriz de Correlação (Spearman)",
        "tempo": "~1,5 min",
        "content": "Estrutura do Heatmap: Cruza 7 variáveis em nível microscópico de cliente para Ruckus (esquerda) e UniFi (direita).\n1. Sinal x Throughput (0,03 RK vs 0,46 UF): Na Ruckus, a correlação é próxima de zero (rs = 0,03).\n2. Sinal x Retransmissões (0,17 RK vs -0,34 UF): Na UniFi, correlação negativa (-0,34): sinal fraco eleva a perda de pacotes.\n3. Ruído x Retransmissões (-0,64 RK vs 0,02 UF): Resultado inesperado que indica a necessidade de interpretar com cautela a métrica de ruído fornecida pela controladora.\n4. Volume x Tempo de Sessão (0,70 RK vs 0,36 UF): Usuários na Ruckus mantêm fluxo contínuo durante as aulas."
    },
    {
        "title": "ZOOM — Equidade de Jain",
        "tempo": "~1,5 min",
        "content": "Gráfico da Esquerda (Boxplot de Jain): Mostra quartis e medianas. Ruckus tem mediana de 0,26 e UniFi de 0,13.\nGráfico da Direita (Curva de Densidade - KDE): O eixo Y representa a estimativa de densidade de probabilidade (KDE), refletindo a frequência temporal relativa com que a rede operou em cada nível de equidade ao longo dos 49 dias.\nInterpretação dos Picos: A curva da UniFi atinge seu pico em 0,13, e a Ruckus em 0,26.\nPiso Teórico de Jain: Varia de 1/N = 1/43 ≈ 0,023 até 1,0."
    },
    {
        "title": "DADOS CHAVE",
        "tempo": "Consulta rápida",
        "content": "Métrica | Ruckus | UniFi\nAPs | 24 | 19\nRegistros limpos | 1.202.408 | 147.517\nG1 (Sinal fraco) | 44,5% | 21,3%\nG2 (Congestionamento) | 47,4% | 4,9%\nG3 (Interferência) | 0,0% | 0,7%\nG4 (Roaming) | 15,3% | 6,6%\nG5 (Cabo) | 0,01% | 0,004%\nSem gargalos | 24,9% | 68,0%\nJain mediano | 0,26 | 0,13\nTamanho efeito 5GHz | r = 0,5133 | —\nPico clientes simultâneos | 606 (15/09 às 19h)\nPeríodo de coleta | 49 dias\nK-Means | K = 4 clusters"
    }
]

# Gerar PDF
for slide in slides:
    pdf.add_page()
    
    # Tempo
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(150, 32, 56) # Cor vermelha do TCC
    pdf.cell(0, 10, slide['tempo'], ln=True)
    pdf.ln(2)
    
    # Título
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(150, 32, 56)
    pdf.multi_cell(0, 10, slide['title'])
    pdf.ln(4)
    
    # Conteúdo
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 7, slide['content'])

# Salvar
output_path = "notas_apresentacao.pdf"
pdf.output(output_path)
print(f"PDF gerado com sucesso: {output_path}")

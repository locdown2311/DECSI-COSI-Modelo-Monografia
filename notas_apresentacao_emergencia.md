# ANOTAÇÕES DA APRESENTAÇÃO — TCC "Caracterização de Gargalos 802.11"
## Igor Carvalho Guimarães | UFOP/ICEA | 2026

> **PLANO DE EMERGÊNCIA**: Este arquivo contém TODAS as notas do apresentador extraídas de `apresentacao.tex`. Use caso o PDF com notas (`apresentacao_com_notas.pdf`) não exiba corretamente os blocos `\note{}`.

---

## SLIDE 1 — Título
**Tempo estimado:** ~1 min

BOM DIA / BOA TARDE à banca.
Meu nome é Igor Carvalho Guimarães.
Apresento meu TCC: "Caracterização de gargalos em redes 802.11 em ambientes de alta densidade".
Orientador: Prof. Marlon Paolo Lima. Coorientador: Prof. Plínio Roque de Almeida.

---

## SLIDE 2 — Sumário
**Tempo estimado:** ~30 seg

Estrutura da apresentação:
1. Introdução e contextualização da WLAN do ICEA.
2. Motivação e objetivos do estudo.
3. Metodologia de coleta, processamento e classificação.
4. Resultados (estatística, correlações, testes, clusters).
5. Recomendações práticas e conclusões.

---

## SLIDE 3 — Introdução: Cenário do Campus e Infraestrutura
**Tempo estimado:** ~1,5 min

Contextualizar o cenário real onde o estudo foi desenvolvido:
O campus do ICEA em João Monlevade abriga cerca de 1.350 pessoas fixas. Segundo os dados oficiais do Relatório de Atividades (2024):
- Discentes: 1.206 alunos de graduação (distribuídos entre Engenharia de Computação, Sistemas de Informação, Engenharia de Produção e Engenharia Elétrica).
- Docentes: 89 professores efetivos nos 4 departamentos.
- TAEs e Apoio: 28 servidores técnico-administrativos e equipe de suporte.

Em ambientes universitários de alta densidade (1,5 a 2 aparelhos por pessoa), isso representa um ecossistema com mais de 2.000 dispositivos móveis em potencial.
A conectividade conta com link dedicado de 1 Gbps da RNP e 43 APs catalogados (24 Ruckus e 19 UniFi, com média de ~40 APs ativos concorrentemente a cada ciclo telemétrico), registrando picos reais superiores a 580 dispositivos conectados no mesmo meio aéreo.

---

## SLIDE 4 — Introdução: O Problema de Pesquisa
**Tempo estimado:** ~1 min

Este slide apresenta o cerne do problema prático e científico:
A insatisfação dos usuários com a rede sem fio é recorrente, mas quase sempre rotulada genericamente como "problema na internet".
A questão investigada foi: o gargalo decorre do link da RNP, de limitações em portas de switches ou da física da interface de radiofrequência?
Sem dados consolidados de telemetria entre Ruckus e UniFi, a tomada de decisão em infraestrutura torna-se empírica no sentido leigo. O trabalho propõe uma metodologia quantitativa para mapear os gargalos operacionais da rede.

---

## SLIDE 5 — Motivação e Objetivos: Motivação
**Tempo estimado:** ~1,5 min

CSMA/CA: o Wi-Fi é um meio compartilhado por contenção. Cada estação ativa consome uma fração de tempo de antena (airtime).
A Ruckus R600 dispõe de antenas adaptativas e opera em dual-band (2,4 e 5 GHz), enquanto a UniFi legada atua em 2,4 GHz em canal único.
A motivação central é fornecer dados técnicos de produção que permitam diagnosticar a origem real das limitações observadas pelos usuários.

---

## SLIDE 6 — Motivação e Objetivos: Objetivos
**Tempo estimado:** ~1 min

Objetivo Geral: caracterizar e diagnosticar as limitações operacionais da rede sem fio do campus.
Específicos: a sequência metodológica parte da ingestão de telemetria, passa por tratamento e classificação determinística (G1 a G5), agrega análise não-supervisionada via K-Means como evidência complementar de agrupamento dos APs, e culmina em intervenções práticas de rede.

---

## SLIDE 7 — Metodologia: Coleta e Consolidação dos Dados
**Tempo estimado:** ~1,5 min

Explicar a divisão temporal dos 49 dias de monitoramento de coleta:
A coleta cobriu a rotina real do campus em duas etapas letivas distintas:
1. Final do período 2026/1 (23/06 a 10/07): encerramento de aulas e semanas de provas finais.
2. Período letivo 2026/2 consolidado (24/08 a 16/10): aulas presenciais plenas com alta densidade de conexões ativas.

Volume consolidado: 1.349.925 registros limpos de produção (1.202.408 Ruckus e 147.517 UniFi), após tratamento de 2,43% de duplicatas no polling da Ruckus e redundância zero na UniFi.

---

## SLIDE 8 — Metodologia: Pipeline Metodológico
**Tempo estimado:** ~1,5 min

Este fluxograma sintetiza visualmente o pipeline metodológico da pesquisa em 5 etapas:
1. Cenário e Coleta (Etapa 1): 43 APs no campus (24 Ruckus e 19 UniFi), 49 dias de monitoramento e mais de 1,3 milhão de registros telemétricos via SNMP e REST API.
2. Tratamento e Features (Etapa 2): deduplicação temporal (4,25% tratada), padronização de variáveis de RF (dBm, SNR, Mbps) e anonimização conforme LGPD.
3. Análise Estatística (Etapa 3): indicação de não-normalidade (p < 0,001), testes não-paramétricos e forte assimetria instantânea de tráfego (Jain mediano = 0,26).
4. Classificação Heurística (Etapa 4): árvore determinística baseada na dinâmica de RF e referências técnicas para categorizar os gargalos G1 a G5.
5. Agrupamento Operacional (Etapa 5): clusterização não-supervisionada via K-Means como análise complementar para identificar perfis de APs sem imposição prévia de regras.

---

## SLIDE 9 — Metodologia: Limiares Operacionais de Gargalos
**Tempo estimado:** ~1,5 min

Explicar a lógica prática dos 5 gargalos:
1. G1 (Sinal < -75 dBm): sinal atenuado pela distância ou obstáculos, forçando o rádio a transmitir em velocidades mais baixas.
2. G2 (>= 15 clientes): no Wi-Fi apenas um fala por vez. Com 15 ou mais clientes disputando o ar, a espera e as colisões disparam. No campus vimos picos de mais de 60 clientes em um único AP.
3. G3 (Ruído > -90 dBm): interferência externa ou canal poluído por ruído.
4. G4 (> 15 trocas de antena/dia): identifica dispositivos que ficam pulando de antena em antena ou alternando em falso, provocando quedas e reautenticações frequentes.
5. G5 (>= 90 Mbps): verifica se a lentidão vinha do cabo dos switches antigos de 100 Mbps em vez do rádio.

---

## SLIDE 10 — Resultados: Análise Descritiva Comparativa (Tabela)
**Tempo estimado:** ~1,5 min

Por que Mediana e Quartis em vez de Máximo? Em distribuições não-gaussianas, a média e os valores extremos distorcem a percepção real. Um sinal de -20 dBm, por exemplo, ocorre apenas quando o aparelho encosta no rádio. Mediana e quartis (Q1 e Q3) fornecem estatística robusta que descreve a faixa central de operação.

Sinal Físico (IS): A UniFi apresenta sinal mediano ligeiramente superior (-66 dBm vs -75 dBm da Ruckus). Isso decorre da arquitetura do prédio: a UniFi está em gabinetes menores de professores, enquanto a Ruckus cobre grandes salas de aula e vãos abertos do campus.

Retransmissões (Ponto Crítico): A UniFi opera com perdas elevadas: mediana de 11,50% e Q3 atingindo 28,00% de quadros retransmitidos. A Ruckus opera com mediana zero e Q3 de apenas 1,37% (média de 5,70% influenciada por picos pontuais de alta carga).

Throughput Mediano: É próximo de zero em ambas (0,12 e 0,00 Mbps). A maioria das estações conectadas não está demandando tráfego pesado contínuo, mantendo apenas sessões leves e serviços em segundo plano.

---

## SLIDE 11 — Resultados: Distribuição de Intensidade de Sinal (Boxplot)
**Tempo estimado:** ~1,5 min

(Notas detalhadas no slide anterior — mesma seção de Estatística Descritiva)

---

## SLIDE 12 — Resultados: Distribuição Temporal de Clientes Únicos (Heatmap)
**Tempo estimado:** ~1,5 min

Visão Unificada do Campus: O mapa de calor consolida a infraestrutura global da WLAN institucional (Ruckus e UniFi unificadas em uma única malha de serviço), contabilizando clientes únicos conectados por horário ao longo dos 49 dias de monitoramento efetivo.

Ciclo Circadiano e Recesso: A rede reflete a rotina universitária: madrugada ociosa, subida acentuada a partir das 08:00 com o início das aulas, concentração máxima entre 14:00 e 20:00 e desocupação progressiva após as 22:00, com clara demarcação do recesso acadêmico.

Pico Unificado de Demanda: O pico máximo da rede alcançou 606 clientes conectados em uma única hora (no dia 15/09 às 19:00, durante a Fase 2), demonstrando a alta densidade suportada pela infraestrutura no retorno presencial de 2026/2.

Origem do Gargalo G2: Essa concentração massiva em horários de aula intensifica a disputa pelo tempo aéreo (airtime) no CSMA/CA, explicando a expressiva incidência do Gargalo G2 (47,4% na Ruckus).

---

## SLIDE 13 — Resultados: Correlações de Grandezas de RF (Spearman)
**Tempo estimado:** ~1,5 min

Por que Spearman em vez de Pearson? O teste de Shapiro-Wilk rejeitou a normalidade. Spearman avalia associações monotônicas (não-lineares), sendo robusto contra caudas pesadas e leituras atípicas.

1. Sinal x Throughput (0,03 RK vs 0,46 UF - Achado Contraintuitivo): Na Ruckus, a correlação é quase nula (rs = 0,03). A intuição comum sugeriria que sinal forte proporcionaria maior velocidade. No entanto, no protocolo CSMA/CA, o meio é compartilhado e a grande maioria dos clientes está ociosa, desacoplando o sinal da vazão instantânea. Na UniFi (rs = 0,46), o rádio legado em 2,4 GHz faz com que a atenuação restrinja a modulação básica (MCS) dos clientes distantes.

2. Sinal x Retransmissões (0,17 RK vs -0,34 UF): Na UniFi, correlação negativa (-0,34): sinal fraco eleva a perda física de pacotes. Na Ruckus (+0,17), o enlace fraco é sustentado pelas antenas adaptativas, mas estações próximas em salas cheias sofrem colisões aéreas.

3. Ruído x Retransmissões (-0,64 RK vs 0,02 UF): Frise à banca: trata-se de um resultado inesperado que indica a necessidade de interpretar com cautela a métrica de ruído fornecida pela controladora, influenciada pela sensibilidade dinâmica da plataforma (evitando especulações físicas prematuras).

4. Volume x Tempo de Sessão (0,70 RK vs 0,36 UF): Usuários na Ruckus apresentam conexões mais estáveis e prolongadas durante as aulas.

Nota de Densidade: Agrupando dados por rádio, a presença de clientes eleva a vazão somada do AP (rs = 0,80 RK / 0,56 UF).

---

## SLIDE 14 — Resultados: Inferência Estatística e Equidade (Jain)
**Tempo estimado:** ~2 min

Significância Estatística (p < 0,001): Indica que as diferenças observadas entre as tecnologias Ruckus e UniFi têm probabilidade estatística ínfima (< 0,1%) de decorrerem de flutuações amostrais ao acaso.

1. Shapiro-Wilk (p < 0,001): Rejeita a hipótese gaussiana. O tráfego de rede apresenta caudas pesadas e comportamento altamente assimétrico, tornando o teste t de Student inadequado.

2. Tamanho de Efeito (r de Rosenthal): O p-valor aponta diferença estatisticamente significativa; o r dimensiona a relevância prática. A vantagem da faixa de 5 GHz sobre 2,4 GHz na Ruckus exibiu tamanho de efeito grande (r = 0,5133), sugerindo a conveniência técnica da política de Band Steering.

3. Equidade de Jain e Assimetria de Carga: O índice mede a distribuição instantânea de vazão. Se vários dispositivos estão ociosos e poucos estão transferindo dados ativamente, o índice cai naturalmente pela dinâmica de contenção do CSMA/CA, sem que a rede seja intrinsicamente injusta. A mediana de 0,26 na Ruckus e 0,13 na UniFi reflete essa forte assimetria temporal e a concentração de discentes em salas de aula específicas (Gargalo G2).

---

## SLIDE 15 — Resultados: Classificação Heurística de Gargalos (Tabela)
**Tempo estimado:** ~1,5 min

Introdução do Clímax da Pesquisa: Apresentamos aqui a resposta central do trabalho: a caracterização objetiva dos gargalos sobre 1.349.925 registros reais de telemetria.

Clivagem Clara entre as Redes: As duas marcas refletem perfis de ocupação física totalmente distintos:
- Na Ruckus, os APs atendem salas de aula com 40 a 60 alunos disputando o canal simultaneamente: por isso vemos 47,4% de contenção (G2) e 44,5% de sinal atenuado (G1), com apenas 24,9% das amostras livres de problemas.
- Na UniFi, os APs atendem gabinetes docentes e setores administrativos, onde há apenas 1 ou 2 pessoas conectadas por sala: com essa baixíssima concorrência no ar, 68,0% de todas as medições operaram em regime ideal, totalmente livres de gargalos. Quando ocorrem problemas na UniFi, decorrem de atenuação por paredes (G1: 21,3%) e transições de roaming (G4: 6,6%).

Gargalo G5 (Ponto Fundamental): Apenas 0,01% das amostras atingiram >= 90 Mbps. Isso fornece forte indício empírico de que o cabeamento Fast Ethernet (100 Mbps) provavelmente não atuou como gargalo preponderante no campus. A lentidão percebida pela comunidade parece associar-se predominantemente a fatores do meio sem fio e à mobilidade.

---

## SLIDE 16 — Resultados: Diagnóstico Físico (G1, G2, G3)
**Tempo estimado:** ~1,5 min

G1 (Baixa Qualidade de Enlace - 44,5% RK / 21,3% UF): Enfatize que a atenuação decorre da dispersão física no campus e de obstáculos diversos (divisórias, estantes na biblioteca e absorção eletromagnética pelo trânsito de pessoas em salas de aula). Quando o sinal cai abaixo de -75 dBm, a estação usa taxa básica de modulação (baixo MCS). Isso faz com que ela passe muito mais tempo transmitindo no ar, penalizando todos os vizinhos.

G2 (Congestionamento do Meio - 47,4% RK vs 4,9% UF): Este é o grande gargalo de sala de aula. Explique a dinâmica do CSMA/CA: o meio é fatiado no tempo. Ter 40 celulares conectados em segundo plano gera uma tempestade de requisições de canal. O rádio atinge esgotamento de tempo aéreo (airtime starvation) mesmo que a velocidade contratada de internet esteja com 90% de folga.

G3 (Interferência de RF): É praticamente nulo no campus universitário, indicando que a separação física dos prédios e o uso de 5 GHz provavelmente contribuem para manter o piso de ruído sob controle.

---

## SLIDE 17 — Resultados: Diagnóstico Sistêmico (G4 e G5)
**Tempo estimado:** ~1,5 min

G4 (Instabilidade de Roaming): Um usuário andando pelo campus troca de antena algumas vezes ao longo do dia, e isso é esperado. No entanto, quando o aparelho troca mais de 15 vezes, ele passa o dia desconectando e reautenticando, gerando pequenas oscilações. Uma explicação plausível é a possível parametrização branda de roaming assistido na controladora, somada ao comportamento dos próprios dispositivos móveis.

G5 (Saturação Cabeada): Havia a hipótese inicial de que a lentidão pudesse decorrer de portas de 100 Mbps nos switches antigos. No entanto, os dados indicam que em menos de 0,01% do tempo as portas operaram perto do teto. O cabeamento provavelmente não atuou como gargalo relevante no período avaliado; os indícios sugerem que as causas situam-se no meio aéreo.

---

## SLIDE 18 — Resultados: Agrupamento Exploratório dos APs (K-Means)
**Tempo estimado:** ~1 min

Papel do K-Means na Pesquisa: O K-Means não é o protagonista, mas sim uma ferramenta não-supervisionada complementar para verificar se os dados brutos dos APs se agrupavam naturalmente em consonância com os gargalos.

Padronização com StandardScaler: Antes do K-Means, as 4 features (clientes_media, throughput_agregado_media, sinal_medico, retransmissoes_media) foram padronizadas usando z-score: z = (x - μ)/σ, onde μ é a média aritmética e σ o desvio padrão de cada feature no dataset de APs.

Por que padronizar? As métricas têm unidades diferentes (quantidade adimensional, Mbps, dBm, percentual). Sem padronização, o K-Means (que usa distância euclidiana) seria dominado pelas features com maior magnitude numérica — por exemplo, throughput em Mbps (centenas) ofuscaria retransmissões em % (duas casas decimais).

Features e K=4: A partição matemática em 4 grupos mostrou-se coerente segundo as métricas de silhueta, cotovelo e índice Davies-Bouldin de 0,7990.

Resultados Ruckus: O Grupo A atende picos de 85 clientes sustentando perdas em 4,3% (graças ao RF inteligente); o Grupo D isola APs periféricos com perdas elevadas a 8,2% (convergindo com o Gargalo G1).

Resultados UniFi: Revela perdas crônicas em 2,4 GHz e isola a anomalia grave do AP PICO-H-100 (sinal excelente de -44,6 dBm, mas 40,2% de quadros perdidos), justificando uma inspeção ativa de campo.

---

## SLIDE 19 — Recomendações Práticas de Engenharia
**Tempo estimado:** ~1,5 min

1. Site survey e reposicionamento (G1): Em vez de comprar novos rádios, otimizar o posicionamento geométrico dos pontos atenuados.

2. Band Steering (G2/G3): Ação imediata de custo zero na controladora, tirando dispositivos da concorrência em 2,4 GHz e enviando para 5 GHz (vantagem apoiada pelo tamanho de efeito r = 0,5133).

3. Mitigação de Sticky Clients (G4): Resolver o maior gargalo da rede ativando 802.11k/v/r e limiar mínimo de RSSI para desassociar aparelhos que se afastam.

4. Auditoria Espectral no AP PICO-H-100: Medição de campo ativa para rastrear a perda de 40,2% antes de qualquer ajuste de potência.

---

## SLIDE 20 — Conclusões
**Tempo estimado:** ~1 min

Os 4 Pilares Finais da Apresentação:

1. Dataset Robusto e Real: Mais de 1,3 milhão de registros em duas etapas acadêmicas distintas da UFOP.

2. Diagnóstico da Origem dos Gargalos: O gargalo da infraestrutura não é a internet externa nem saturação de portas cabeadas (G5 é residual). A degradação observada decorre da física de RF e da contenção no meio compartilhado CSMA/CA sob forte assimetria temporal.

3. Agrupamento K-Means: Análise não-supervisionada complementar que agrupou os APs por semelhança e isolou a anomalia do AP PICO-H-100 sem impor limiares prévios.

4. Ações de Baixo Custo: Soluções práticas de engenharia (Band Steering e Site Survey) que a própria UFOP pode implementar sem necessidade imediata de aquisições onerosas.

Encerramento: Agradecer à banca, ao orientador Marlon, coorientador Plínio e passar para a arguição com tranquilidade.

---

## SLIDE 21 — Agradecimentos
**(Sem notas adicionais — encerrar e abrir para arguição)**

---

## SLIDES DE ZOOM — Notas complementares

### Zoom — Matriz de Correlação (Spearman)
Estrutura do Heatmap: Cruza 7 variáveis em nível microscópico de cliente para Ruckus (esquerda) e UniFi (direita).
1. Sinal x Throughput (0,03 RK vs 0,46 UF): Na Ruckus, a correlação é próxima de zero (rs = 0,03), sugerindo que sob CSMA/CA e estações em segundo plano, sinal forte não assegura necessariamente maior vazão útil individual. Na UniFi (0,46), a atenuação parece restringir a modulação básica MCS.
2. Sinal x Retransmissões (0,17 RK vs -0,34 UF): Na UniFi, correlação negativa (-0,34): sinal fraco eleva a perda de pacotes. Na Ruckus (+0,17), o enlace fraco é sustentado pelas antenas, mas estações próximas em salas cheias sofrem colisões aéreas.
3. Ruído x Retransmissões (-0,64 RK vs 0,02 UF): Frise que este é um resultado inesperado que indica a necessidade de interpretar com cautela a métrica de ruído fornecida pela controladora, influenciada pela sensibilidade dinâmica da plataforma.
4. Volume x Tempo de Sessão (0,70 RK vs 0,36 UF): Usuários na Ruckus mantêm fluxo contínuo durante as aulas; na UniFi, o uso é mais intermitente.

### Zoom — Equidade de Jain
Gráfico da Esquerda (Boxplot de Jain): Mostra quartis e medianas. Ruckus tem mediana de 0,26 e UniFi de 0,13.
Gráfico da Direita (Curva de Densidade - KDE):
- O que significa o Eixo Y (Densidade)? O eixo Y representa a estimativa de densidade de probabilidade (KDE), refletindo a frequência temporal relativa com que a rede operou em cada nível de equidade ao longo dos 49 dias. A área total sob a curva é igual a 1 (100% do tempo).
- Interpretação dos Picos: A curva da UniFi atinge seu pico em 0,13, e a Ruckus em 0,26. Isso reflete a forte assimetria instantânea gerada pela dinâmica do CSMA/CA e pela concentração de alunos em salas de aula específicas (Gargalo G2).
- Densidade em 1,0: Próximo a 1,0 (equilíbrio instantâneo estrito), a densidade é praticamente nula, o que é esperado em redes móveis onde as demandas dos clientes ocorrem em rajadas assíncronas.
- Piso Teórico de Jain: Varia de 1/N = 1/43 ≈ 0,023 (onde 1 rádio concentra todo o tráfego e 42 ficam ociosos) até 1,0 (partilha idêntica).

---

## DADOS CHAVE (para consulta rápida)

| Métrica | Ruckus | UniFi |
|---------|--------|-------|
| APs | 24 | 19 |
| Registros limpos | 1.202.408 | 147.517 |
| G1 (Sinal fraco) | 44,5% | 21,3% |
| G2 (Congestionamento) | 47,4% | 4,9% |
| G3 (Interferência) | 0,0% | 0,7% |
| G4 (Roaming) | 15,3% | 6,6% |
| G5 (Cabo) | 0,01% | 0,004% |
| Sem gargalos | 24,9% | 68,0% |
| Jain mediano | 0,26 | 0,13 |
| Tamanho efeito 5GHz | r = 0,5133 | — |
| Pico clientes simultâneos | \multicolumn{2}{c}{606 (15/09 às 19h)} |
| Período de coleta | \multicolumn{2}{c}{49 dias (4 fases letivas)} |
| K-Means | \multicolumn{2}{c}{K = 4 clusters} |

---

> **Gerado automaticamente de `apresentacao.tex`** — Verifique se algum ajuste de última hora foi feito no LaTeX antes da apresentação.

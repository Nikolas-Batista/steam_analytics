# Metodologia — Como Calculamos Faturamento e Oportunidade

> Documento explicativo sobre os critérios e ponderações usados no Steam Market Intelligence para estimar faturamento de jogos e calcular o Opportunity Score.

---

## 1. Como estimamos o faturamento de um jogo

### O desafio

A Steam não divulga publicamente quantas cópias um jogo vendeu nem quanto ele faturou. Essa informação é confidencial entre a Valve e o desenvolvedor. Para contornar isso, usamos um método de mercado amplamente reconhecido chamado **Método Boxleiter**.

### Como funciona

O método parte de um dado que **é público**: o número de reviews de um jogo. Em 2014, a própria Valve revelou — sem querer — uma proporção histórica entre reviews e número de compradores. Desde então, ferramentas de mercado usam essa proporção como base.

```
Número de reviews × multiplicador  ≈  Número estimado de donos (owners)
```

O multiplicador varia historicamente entre **35 e 80**, dependendo de quantas reviews o jogo tem (jogos com poucas reviews tendem a ter proporção diferente de jogos populares).

| Faixa de reviews | Multiplicador aproximado | Intuição |
|---|---|---|
| Menos de 100 | ~70–80 | Jogos pequenos têm proporcionalmente menos gente disposta a deixar review — cada review "representa" mais compradores |
| 100 – 1.000 | ~50–60 | Faixa intermediária, mais comum entre indies com tração moderada |
| 1.000 – 10.000 | ~40–50 | Jogos com base de jogadores maior tendem a ter mais reviews por comprador |
| Mais de 10.000 | ~30–40 | Jogos populares atraem um público mais engajado em deixar avaliações, reduzindo o multiplicador necessário |

> No nosso pipeline atual usamos um multiplicador único e simplificado (não diferenciado por faixa). A tabela acima mostra o range histórico de referência do método — uma possível evolução futura é aplicar o multiplicador variável por faixa, o que tornaria a estimativa de owners ainda mais precisa para jogos pequenos (que são justamente o nosso foco).

### De "donos estimados" para "faturamento"

Uma vez estimado o número de donos, multiplicamos pelo preço do jogo:

```
Receita Bruta Estimada = Donos Estimados × Preço do Jogo
```

Mas esse número **não é o que o desenvolvedor recebe**. Há uma série de descontos no caminho:

| Desconto | Impacto médio | O que representa |
|---|---|---|
| Preço regional ajustado | ~9% | Jogadores de países como Brasil, Argentina, Turquia pagam preços menores — reduz a média global |
| Promoções/Sales | ~20% | A maioria das vendas na Steam acontece durante promoções, não no preço cheio |
| Reembolsos | ~12% | A Steam permite reembolso em até 2 horas de jogo — uma fração relevante das compras é devolvida |
| Taxa da Steam | 30% (padrão) | A Valve retém 30% de toda venda (cai para 25% acima de US$10M e 20% acima de US$50M em receita vitalícia) |
| Impostos (VAT/Sales Tax) | ~12% | Cada país tem sua tributação sobre vendas digitais |

### A fórmula que aplicamos

Para simplificar o cálculo e manter consistência entre os 4.826 jogos analisados, combinamos todos esses descontos em um único fator:

```
Receita Estimada = Donos Estimados (mínimo) × Preço × 0.35
```

**Por que 0.35 e não um número maior?**

Multiplicando os descontos médios acima:
```
0.91 (regional) × 0.80 (promoções) × 0.88 (reembolsos) × 0.70 (taxa Steam) × 0.88 (impostos)
≈ 0.313
```

Arredondamos para **0.35** para ficar levemente conservador — preferimos subestimar do que supor um cenário otimista demais, já que a decisão de negócio (qual jogo desenvolver) precisa ser robusta mesmo em cenários ruins.

**Por que usamos o valor mínimo de donos, não o máximo?**

A fonte de dados retorna uma faixa (ex: "1.000.000 .. 2.000.000 donos"). Usar o valor mínimo é uma escolha deliberadamente conservadora — preferimos errar para baixo na estimativa de faturamento.

### O que isso significa na prática

> Os valores de "Receita Estimada" no dashboard são **estimativas de ordem de grandeza**, não números exatos. Um jogo com receita estimada de US$1M pode na realidade ter faturado entre US$700K e US$2M.

Para a tomada de decisão isso **não é um problema**, porque:

1. O viés é o mesmo para todos os 4.826 jogos — comparações relativas continuam válidas
2. Usamos majoritariamente a **receita por review** (eficiência), não a receita absoluta
3. O objetivo é identificar **padrões de mercado** (que tipo de jogo, que faixa de preço, que nicho), não prever o faturamento exato do projeto de vocês

---

## 2. Como calculamos o Opportunity Score

O Opportunity Score é um número de 0 a 100 que resume, em uma única métrica, **o quão atrativo é um determinado tipo de jogo para o perfil de vocês** (dupla desenvolvedor + artista, ciclo de produção de 3 a 6 meses).

### A fórmula

```
Opportunity Score = ( Receita por Review × 0.40
                     + Avaliação Positiva × 0.35
                     + Retenção (CCU/Owners) × 0.25 )
                     ÷ Complexidade de Produção
```

Cada componente é normalizado numa escala de 0 a 100 antes de entrar na fórmula, para que nenhum deles domine artificialmente o resultado por ter uma escala numérica maior que os outros.

---

### Componente 1 — Receita por Review (peso 40%)

```
Receita por Review = Receita Estimada ÷ Total de Reviews
```

**Por que esse é o componente com maior peso?**

Receita absoluta favorece injustamente jogos gigantes (ex: Elden Ring, GTA V) que estão completamente fora do alcance de um micro-estúdio. Receita por review, por outro lado, mede **eficiência de monetização** — quanto cada jogador "vale" em termos de receita.

Um jogo pequeno e eficiente (ex: Balatro, Hidden Folks) pode ter uma receita por review excelente mesmo com volume total baixo — e é exatamente esse padrão de eficiência que queremos replicar, não o volume absoluto de um blockbuster.

---

### Componente 2 — Avaliação Positiva (peso 35%)

```
Avaliação Positiva = % de reviews positivas do jogo
```

**Por que esse é o segundo maior peso?**

Um jogo pode ter receita alta e ainda assim ser malvisto pelo mercado (ex: lançamentos com microtransações agressivas que geram receita de curto prazo mas reputação ruim). Para uma dupla que está construindo um portfólio e uma marca, **reputação importa tanto quanto receita**.

Além disso, avaliação positiva é o sinal mais direto de "o mercado aceita bem esse tipo de produto" — é validação de que a fórmula (gênero + preço + execução) funciona.

---

### Componente 3 — Retenção / CCU-to-Owners (peso 25%)

```
Retenção = Pico de Jogadores Simultâneos ÷ Donos Estimados
```

Esse valor representa **qual fração dos donos do jogo ainda está jogando ativamente**. Um valor alto indica que o jogo tem "pernas" — as pessoas continuam voltando muito tempo depois da compra.

**Por que o menor peso entre os três?**

Retenção é importante, mas é a métrica com **maior margem de erro** — depende de quando capturamos o CCU (pode ser horário de pico ou vale) e jogos mais antigos naturalmente têm CCU menor mesmo sendo bem-sucedidos. Por isso entra na fórmula, mas com peso reduzido.

---

### Componente 4 — Complexidade de Produção (divisor)

```
Complexidade = pontuação de 1 a 10 baseada nas tags do jogo
```

Diferente dos três componentes anteriores, a complexidade **não soma** — ela **divide** o resultado final. Isso significa que ela funciona como um **fator de penalização**: mesmo um jogo com receita, avaliação e retenção excelentes recebe um score final baixo se for complexo demais para o perfil de vocês.

### Como a complexidade é calculada

Cada tag do jogo soma ou subtrai pontos de uma base neutra (5 pontos):

| Faixa de complexidade | Tempo de desenvolvimento estimado | Impacto por tag | Exemplos de tags |
|---|---|---|---|
| **Baixa** | 3 a 6 meses | -0.5 ponto | Puzzle, Platformer, Visual Novel, Arcade, Roguelite, Card Game |
| **Média** | 6 a 12 meses | +0.5 ponto | RPG, Metroidvania, Survival, Multiplayer, Simulation, Strategy |
| **Alta** | 12+ meses | +2.0 pontos | MMO, Open World, Battle Royale, 4X, Grand Strategy, MMORPG |

**Por que calibramos especificamente para "dupla dev + artista"?**

A complexidade real de um projeto depende de **quem está fazendo**. Tags como "Pixel Graphics", "Hand-drawn" ou "Anime" — que poderiam ser um gargalo para um desenvolvedor solo sem habilidades artísticas — não penalizam o score de vocês, porque o parceiro artista já resolve essa parte.

Da mesma forma, tags que indicam sistemas complexos de jogo (não de arte) — como "Open World", "MMO", "Grand Strategy" — penalizam fortemente, porque **nenhuma habilidade artística reduz o tempo necessário para construir esses sistemas**. Esse tempo de engenharia é o gargalo real para uma dupla pequena.

---

## 3. O Ranking — critérios de desempate

O Opportunity Score é normalizado em uma escala de 0 a 100, o que significa que **empates são esperados** — vários jogos podem chegar a scores muito próximos ou idênticos (ex: 100.0).

Para transformar o score em um **ranking definitivo** (posição #1, #2, #3...), aplicamos uma hierarquia de critérios de desempate:

| Posição | Critério | Direção | Por quê |
|---|---|---|---|
| 1º | Opportunity Score | Maior é melhor | Critério principal — combina receita, avaliação e retenção |
| 2º (desempate) | Complexidade de Produção | **Menor** é melhor | Entre duas oportunidades equivalentes, a mais simples reduz risco de execução para a dupla |
| 3º (desempate) | Avaliação Positiva | Maior é melhor | Reputação de mercado já validada é sinal de "fórmula aprovada" |
| 4º (desempate) | Receita por Review | Maior é melhor | Critério mais sensível a ruído — usado apenas como último recurso |

### Exemplo prático

```
Jogo A → Opportunity Score: 80.0 | Complexidade: 2.0 | Avaliação: 95%
Jogo B → Opportunity Score: 80.0 | Complexidade: 1.5 | Avaliação: 90%

Resultado: Jogo B fica em posição superior no ranking,
porque em empate de score, menor complexidade vence.
```

### Por que essa ordem específica

A lógica reflete como uma dupla pequena deveria pensar na prática: **"entre duas apostas igualmente promissoras, escolha a que você consegue executar com menos risco"**. Só depois de resolver isso é que entram critérios sobre como o mercado recebeu o jogo (avaliação) e, por último, a eficiência financeira pura — que é o dado mais sujeito a ruído na nossa estimativa.

A coluna **#** no dashboard reflete diretamente essa posição final — é a ordem recomendada de prioridade para análise.

---

## 4. Resumo — por que essas escolhas fazem sentido para o negócio

| Decisão | Razão de negócio |
|---|---|
| Receita por review > Receita absoluta | Evita que jogos AAA distorçam o ranking; mede eficiência replicável |
| Avaliação com peso alto (35%) | Reputação é ativo de longo prazo para um estúdio iniciante |
| Retenção com peso menor (25%) | Métrica útil mas com maior ruído nos dados |
| Fator de receita 0.35 (conservador) | Decisões de negócio devem ser robustas mesmo em cenário pessimista |
| Complexidade como divisor (não soma) | Garante que projetos inviáveis para a dupla nunca apareçam no topo, independente do potencial financeiro |
| Complexidade calibrada para dupla dev+artista | O modelo reflete as competências reais do time, não um perfil genérico |

---

## 5. Limitações que devem ser consideradas

- Os valores de receita são **estimativas de ordem de grandeza**, não auditorias financeiras
- A base de dados reflete o mercado **histórico** — não garante que um nicho continuará com a mesma demanda no futuro
- O CCU (jogadores online) é um **snapshot no tempo da coleta**, não uma média histórica
- Jogos com menos de 10 reviews ou preço abaixo de US$3 foram excluídos da análise por falta de confiabilidade estatística

---

*Este documento acompanha o Steam Market Intelligence e deve ser consultado sempre que houver dúvida sobre a origem de um número apresentado no dashboard.*
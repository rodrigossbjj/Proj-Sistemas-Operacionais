# 🖥️ Trabalho 1 — Sistemas Operacionais

> **Instituição:** IFCE – Campus Maracanaú  
> **Disciplina:** Sistemas Operacionais  
> **Professor:** Daniel Ferreira  

---

## 📋 Sumário

- [Visão Geral](#visão-geral)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Questão 1 — Simulador RR vs SRTF](#questão-1--simulador-rr-vs-srtf)
- [Questão 2 — Programadores, Compilador e Banco de Dados](#questão-2--programadores-compilador-e-banco-de-dados)
- [Questão 3 — Hospital Veterinário (Cães e Gatos)](#questão-3--hospital-veterinário-cães-e-gatos)

---

## Visão Geral

Este repositório contém as soluções para o **Trabalho 1** da disciplina de Sistemas Operacionais, abordando:

| # | Tema | Tópico | Arquivo |
|---|------|--------|---------|
| 1 | Escalonamento | Simulação e comparação de RR e SRTF | `scheduler_sim.py` |
| 2 | Sincronização | Programadores com semáforos (compilador + banco) | `synchronization/` |
| 3 | Sincronização | Sala de repouso veterinária (cães e gatos) | `room-sync/` |

---

## Estrutura do Projeto

```
Proj-Sistemas-Operacionais/
│
├── scheduler_sim.py                   # Questão 1 — Simulador RR vs SRTF
│
├── synchronization/
│   ├── threading_Semaphore.py         # Questão 2 — Semáforo nativo do Python
│   └── threading_SemaphoreManual.py   # Questão 2 — Semáforo implementado manualmente
│
├── room-sync/
│   ├── input.json                     # Questão 3 — Entrada padronizada
│   └── vet_room.py                    # Questão 3 — Simulação da sala veterinária
│
└── README.md
```

---

## Pré-requisitos

- **Python 3.10+**
- Nenhuma dependência externa — apenas biblioteca padrão do Python (`threading`, `random`, `time`, `json`, `dataclasses`)

```bash
python --version   # verifique se está em 3.10+
```

---

## Questão 1 — Simulador RR vs SRTF

**Arquivo:** [`scheduler_sim.py`](./scheduler_sim.py)  
**Valor:** 1 ponto

### Descrição

Simulação que compara dois algoritmos clássicos de escalonamento de processos:

- **Round Robin (RR)** — preemptivo, fatia de tempo fixa (quantum)
- **SRTF (Shortest Remaining Time First)** — preemptivo, sempre executa o processo com menor tempo restante

O simulador avalia as métricas para **múltiplos valores de quantum** (1, 2, 4, 8, 16) e para 3 cenários de carga de trabalho diferentes.

### Funcionalidades

- ✅ Tempos de chegada distintos por processo
- ✅ Custo de troca de contexto de **1 unidade de tempo** aplicado a toda mudança de CPU (incluindo preempções)
- ✅ Desempate **aleatório** com **seed fixa** (reprodutibilidade garantida)
- ✅ Timeline visual colorida por processo (cores ANSI no terminal)
- ✅ Métricas calculadas:
  - **Tempo médio de resposta** (± desvio padrão)
  - **Tempo médio de retorno / turnaround** (± desvio padrão)
  - **Vazão** — processos concluídos na janela T = 100

### Cenários de Carga

| Cenário | Burst Time | Intervalo |
|---------|------------|-----------|
| `curto` | Pequeno | [1, 5] ticks |
| `longo` | Grande | [20, 50] ticks |
| `misto` | Misturado | 50% curto + 50% longo |

> O cenário misto expõe as diferenças mais críticas entre RR e SRTF: processos longos podem causar inanição no SRTF, enquanto no RR todos recebem CPU periodicamente.

### Formato de Entrada (JSON embutido no código)

```json
{
  "spec_version": "1.0",
  "challenge_id": "rr_srtf_preemptivo_demo",
  "metadata": {
    "context_switch_cost": 1,
    "throughput_window_T": 100,
    "algorithms": ["RR", "SRTF"],
    "rr_quantums": [1, 2, 4, 8, 16]
  },
  "workload": {
    "time_unit": "ticks",
    "processes": [
      {"pid": "P01", "arrival_time": 0, "burst_time": 5},
      {"pid": "P02", "arrival_time": 1, "burst_time": 17},
      {"pid": "P03", "arrival_time": 2, "burst_time": 3},
      {"pid": "P04", "arrival_time": 4, "burst_time": 22},
      {"pid": "P05", "arrival_time": 6, "burst_time": 7}
    ]
  }
}
```

### Como Executar

```bash
python scheduler_sim.py
```

### Exemplo de Saída

```
======================================================================
CENÁRIO: CURTO
======================================================================

Carga de trabalho:
P01 | arrival=3 | burst=4
P02 | arrival=1 | burst=2
...

ROUND ROBIN

Timeline — RR(q=1)
  02020202010101...

Métricas — RR(q=1)
Tempo médio resposta: 1.40
Tempo médio retorno: 9.20
Vazão: 5

...

SRTF

Timeline — SRTF
  0202010101...

Métricas — SRTF
Tempo médio resposta: 0.60
Tempo médio retorno: 5.80
Vazão: 5

COMPARATIVO
RR(q=1)         Resp=1.40 Turn=9.20 Thr=5
RR(q=2)         Resp=1.20 Turn=8.60 Thr=5
...
SRTF            Resp=0.60 Turn=5.80 Thr=5
```

### Análise: Vantagens e Desvantagens

#### Round Robin (RR)

| | |
|---|---|
| ✅ **Vantagens** | Justo — todos os processos recebem CPU periodicamente |
| | Evita inanição |
| | Excelente para sistemas interativos e de tempo compartilhado |
| ❌ **Desvantagens** | Quantum muito **pequeno** → muitas trocas de contexto → alto overhead |
| | Quantum muito **grande** → comportamento similar ao FCFS |
| | Tempo médio de retorno geralmente maior que SRTF |

#### SRTF (Shortest Remaining Time First)

| | |
|---|---|
| ✅ **Vantagens** | **Minimiza o tempo médio de retorno** (turnaround) |
| | Processos curtos terminam rapidamente |
| | Ótimo teórico para minimizar espera |
| ❌ **Desvantagens** | **Pode causar inanição** de processos longos |
| | Requer conhecimento prévio do burst time (impraticável em sistemas reais) |
| | Muitas preempções → alto custo de troca de contexto |

---

## Questão 2 — Programadores, Compilador e Banco de Dados

**Arquivos:**
- [`synchronization/threading_Semaphore.py`](./synchronization/threading_Semaphore.py) — usa `threading.Semaphore` nativo
- [`synchronization/threading_SemaphoreManual.py`](./synchronization/threading_SemaphoreManual.py) — implementa semáforo manualmente com `Condition`

**Valor:** 0,5 ponto

### Descrição

Simulação de **5 programadores** em um laboratório compartilhando dois recursos:

- **Compilador** — exclusivo (apenas 1 por vez)
- **Banco de Dados** — compartilhado com limite de **2 acessos simultâneos**

Cada programador executa em **laço infinito**:
1. **Pensa** (descansa por tempo aleatório)
2. Aguarda acesso ao **banco de dados**
3. Aguarda acesso ao **compilador**
4. **Compila** o código
5. Libera os recursos e repete

### Mecanismo de Sincronização

| Recurso | Semáforo | Valor inicial |
|---------|----------|---------------|
| Compilador | `Semaphore(1)` | 1 (mutex) |
| Banco de dados | `Semaphore(2)` | 2 (compartilhado) |

O sistema garante:
- ✅ **Sem deadlock** — a ordem de aquisição é sempre a mesma (banco → compilador), evitando espera circular
- ✅ **Sem inanição** — o `threading.Semaphore` do Python usa fila FIFO internamente

### Versões Implementadas

#### `threading_Semaphore.py` — Semáforo Nativo

Usa diretamente `threading.Semaphore` da biblioteca padrão. Mais simples e direto.

```bash
python synchronization/threading_Semaphore.py
```

#### `threading_SemaphoreManual.py` — Semáforo Manual

Implementa a classe `SemaphoreManual` usando apenas `threading.Lock` e `threading.Condition`, demonstrando como semáforos funcionam internamente.

```python
class SemaphoreManual:
    def acquire(self):
        with self.condition:
            while self.value == 0:
                self.condition.wait()   # bloqueia até ser notificado
            self.value -= 1

    def release(self):
        with self.condition:
            self.value += 1
            self.condition.notify()     # acorda uma thread em espera
```

```bash
python synchronization/threading_SemaphoreManual.py
```

### Exemplo de Saída

```
0001 | [P1] pensando...
0002 | [P2] pensando...
0003 | [P3] pensando...
0004 | [P4] pensando...
0005 | [P5] pensando...
0006 | [P2] quer acessar o banco
0007 | [P2] entrou no banco
0008 | [P2] quer usar o compilador
0009 | [P2] pegou o compilador
0010 | [P2] COMPILANDO...
0011 | [P4] quer acessar o banco
0012 | [P4] entrou no banco
0013 | [P4] quer usar o compilador   ← aguarda compilador (bloqueado)
0014 | [P2] terminou compilação
0015 | [P2] liberou compilador
0016 | [P4] pegou o compilador
...
```

> O programa executa em **laço infinito**. Para encerrar: `Ctrl + C`

---

## Questão 3 — Hospital Veterinário (Cães e Gatos)

**Valor:** 0,5 ponto  
**Arquivos:**
- [`room-sync/vet_room.py`](./room-sync/vet_room.py) — simulador da sala veterinária
- [`room-sync/input.json`](./room-sync/input.json) — entrada padronizada do enunciado

### Descrição

Protocolo de sala de repouso em hospital veterinário com as seguintes regras:

- Se há **cães** na sala, outros cães podem entrar, mas gatos aguardam.
- Se há **gatos** na sala, outros gatos podem entrar, mas cães aguardam.
- Cães e gatos nunca podem ocupar a sala ao mesmo tempo.
- A placa da sala pode estar em apenas 3 estados: **EMPTY**, **DOGS**, **CATS**.

A simulação é determinística e avança por **ticks**, usando os campos `arrival_time` e `rest_duration` do JSON.

### Formato de Entrada (JSON)

```json
{
  "spec_version": "1.0",
  "challenge_id": "vet_room_protocol_demo",
  "metadata": {
    "room_count": 1,
    "allowed_states": ["EMPTY", "DOGS", "CATS"],
    "sign_change_latency": 0,
    "tiebreaker": ["arrival_time", "id"]
  },
  "room": {
    "initial_sign_state": "EMPTY"
  },
  "workload": {
    "time_unit": "ticks",
    "animals": [
      {"id": "D01", "species": "DOG", "arrival_time": 0, "rest_duration": 5},
      {"id": "C01", "species": "CAT", "arrival_time": 1, "rest_duration": 4},
      {"id": "D02", "species": "DOG", "arrival_time": 2, "rest_duration": 6},
      {"id": "C02", "species": "CAT", "arrival_time": 3, "rest_duration": 2},
      {"id": "D03", "species": "DOG", "arrival_time": 4, "rest_duration": 3}
    ]
  }
}
```

### Modos Implementados

| Versão | Inanição | Mecanismo |
|--------|----------|-----------|
| `unfair` | ✅ Possível | Animais da mesma espécie da placa atual continuam entrando mesmo com a outra espécie esperando |
| `fair` | ❌ Evitada | Quando a espécie oposta está esperando, novas entradas da espécie atual são bloqueadas até a sala esvaziar |
| `both` | Comparativo | Executa `unfair` e depois `fair` com a mesma entrada |

#### Solução com possibilidade de inanição (`unfair`)

Quando a sala está vazia, entra o primeiro animal aguardando e a placa muda para a espécie dele. Enquanto a placa estiver em `DOGS`, cães podem continuar entrando; enquanto estiver em `CATS`, gatos podem continuar entrando.

Essa política pode causar inanição porque uma sequência contínua de chegadas da espécie atual pode manter a placa ocupada, fazendo a espécie oposta esperar indefinidamente.

#### Solução sem possibilidade de inanição (`fair`)

Quando existe animal da espécie oposta aguardando, novas entradas da espécie que já está na sala são bloqueadas. O grupo atual termina seu descanso, a sala fica vazia, a placa muda e a espécie que estava aguardando recebe acesso.

Essa política impede que novos animais ultrapassem indefinidamente a espécie oposta que já estava bloqueada.

### Como Executar

```bash
cd room-sync

python vet_room.py --mode unfair --input input.json
python vet_room.py --mode fair --input input.json
python vet_room.py --mode both --input input.json
```

> Em ambientes onde `python` não aponta para Python 3, use `python3`.

### Saída

O programa imprime um log por tick com:

- `ARRIVE` — animal chegou ao hospital;
- `ENTER` — animal entrou na sala e informa o tick previsto de saída;
- `EXIT` — animal saiu da sala;
- `SIGN` — alteração da placa da porta;
- `WAIT` — animais bloqueados aguardando.

Ao final, imprime um resumo com ordem de entrada, ordem de saída, tempo de espera por animal e estado final da placa.

### Exemplo de Diferença entre os Modos

Com a entrada padrão, no modo `unfair`, `D02` e `D03` entram enquanto `C01` já está esperando, pois a placa ainda está em `DOGS`.

No modo `fair`, depois que `C01` chega e passa a esperar, novos cães são bloqueados. Quando `D01` sai, a sala muda para `CATS` e os gatos aguardando entram antes dos novos cães.

---

## 🔬 Conceitos Abordados

| Conceito | Aplicação |
|---|---|
| Escalonamento preemptivo | RR e SRTF na Questão 1 |
| Troca de contexto | Custo de 1 tick simulado na Questão 1 |
| Semáforo binário (mutex) | Compilador exclusivo na Questão 2 |
| Semáforo contador | Banco com 2 acessos simultâneos na Questão 2 |
| Exclusão mútua | Sala veterinária na Questão 3 |
| Deadlock | Evitado por ordem de aquisição na Questão 2 |
| Inanição (starvation) | Analisada no SRTF (Q1) e Questão 3 |
| Reprodutibilidade | Seed fixa no RR e SRTF |

---

## 📚 Referências

- Silberschatz, A.; Galvin, P. B.; Gagne, G. — *Operating System Concepts*, 10ª ed.
- Tanenbaum, A. S. — *Modern Operating Systems*, 4ª ed.
- Documentação oficial Python — [`threading`](https://docs.python.org/3/library/threading.html)

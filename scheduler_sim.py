import json
import random
import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# SIMULADOR DE ESCALONAMENTO DE PROCESSOS
# =============================================================================
# Este código compara dois algoritmos clássicos de escalonamento:
#
#   • Round Robin (RR)
#   • Shortest Remaining Time First (SRTF)
#
# O simulador mede:
#   • Tempo médio de resposta
#   • Tempo médio de retorno (turnaround)
#   • Vazão (throughput)
#
# Além disso:
#   • Considera custo de troca de contexto
#   • Permite workloads curtos, longos e mistos
#   • Mostra timeline de execução
#   • Exibe tabelas detalhadas dos processos
#
# =============================================================================


# =============================================================================
# ESTRUTURA DE PROCESSO
# =============================================================================
@dataclass
class Process:
    """
    Representa um processo do sistema operacional.

    pid            -> Identificador do processo
    arrival_time   -> Momento em que o processo chega
    burst_time     -> Tempo total necessário de CPU

    remaining_time -> Tempo restante para finalizar
    start_time     -> Primeiro instante em que executou
    finish_time    -> Momento em que terminou
    """

    pid: str
    arrival_time: int
    burst_time: int

    # Campos preenchidos automaticamente
    remaining_time: int = field(init=False)
    start_time: Optional[int] = field(default=None, init=False)
    finish_time: Optional[int] = field(default=None, init=False)

    def __post_init__(self):
        """
        Executado automaticamente após criar o objeto.
        Inicializa remaining_time com burst_time.
        """
        self.remaining_time = self.burst_time

    def reset(self):
        """
        Reinicia o processo para reutilização em outro algoritmo.
        """
        self.remaining_time = self.burst_time
        self.start_time = None
        self.finish_time = None


# =============================================================================
# CARREGAMENTO DOS PROCESSOS
# =============================================================================
def load_processes(spec: dict) -> list[Process]:
    """
    Converte o JSON/spec em objetos Process.
    """
    return [
        Process(p["pid"], p["arrival_time"], p["burst_time"])
        for p in spec["workload"]["processes"]
    ]


def clone_processes(processes: list[Process]) -> list[Process]:
    """
    Faz uma cópia profunda dos processos.

    Isso é importante porque cada algoritmo modifica:
        • remaining_time
        • start_time
        • finish_time

    Assim cada algoritmo recebe uma cópia limpa.
    """
    return [copy.deepcopy(p) for p in processes]


# =============================================================================
# MÉTRICAS
# =============================================================================
def compute_metrics(processes: list[Process], window_T: int) -> dict:
    """
    Calcula métricas importantes de escalonamento.

    Métricas:
        • Tempo de resposta
        • Tempo de retorno
        • Vazão
    """

    # Tempo de resposta:
    # instante que começou - instante que chegou
    response_times = [
        p.start_time - p.arrival_time
        for p in processes
        if p.start_time is not None
    ]

    # Tempo de retorno:
    # instante que terminou - instante que chegou
    turnaround_times = [
        p.finish_time - p.arrival_time
        for p in processes
        if p.finish_time is not None
    ]

    # Quantos terminaram antes da janela T
    completed_in_T = sum(
        1 for p in processes
        if p.finish_time is not None and p.finish_time <= window_T
    )

    # Média simples
    def mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    # Desvio padrão
    def std(lst):
        if len(lst) < 2:
            return 0.0

        m = mean(lst)

        return (
            sum((x - m) ** 2 for x in lst) / len(lst)
        ) ** 0.5

    return {
        "avg_response": mean(response_times),
        "std_response": std(response_times),

        "avg_turnaround": mean(turnaround_times),
        "std_turnaround": std(turnaround_times),

        "throughput": completed_in_T,
    }


# =============================================================================
# ROUND ROBIN
# =============================================================================
def simulate_rr(
        processes: list[Process],
        quantum: int,
        context_switch_cost: int,
        seed: int = 42
):
    """
    Simula o algoritmo Round Robin.

    Características:
        • Preemptivo
        • Cada processo recebe uma fatia de tempo (quantum)
        • Ao acabar o quantum:
            -> processo volta para o fim da fila
    """

    rng = random.Random(seed)

    # Copia os processos
    procs = clone_processes(processes)

    # Ordena por chegada
    procs.sort(key=lambda p: p.arrival_time)

    # Timeline:
    # guarda cada tick executado
    timeline = []

    # Fila FIFO de prontos
    ready = deque()

    # Processo atual da CPU
    current: Optional[Process] = None

    # Contador do quantum atual
    time_slice = 0

    # Relógio do sistema
    t = 0

    # Quantos processos finalizaram
    done_count = 0

    # Tempo restante de troca de contexto
    overhead_remaining = 0

    # Enquanto ainda houver processos vivos
    while done_count < len(procs):

        # ============================================================
        # CHEGADA DE NOVOS PROCESSOS
        # ============================================================
        for p in procs:

            # Processo chega exatamente no instante t
            if (
                p.arrival_time == t
                and p.start_time is None
                and p.remaining_time == p.burst_time
            ):

                # Evita duplicatas na fila
                if p not in ready and p is not current:
                    ready.append(p)

        # ============================================================
        # TROCA DE CONTEXTO
        # ============================================================
        if overhead_remaining > 0:

            timeline.append((t, "CTX", "context_switch"))

            overhead_remaining -= 1
            t += 1

            continue

        # ============================================================
        # TROCA DE PROCESSO
        # ============================================================
        if (
            current is None
            or current.remaining_time == 0
            or time_slice == quantum
        ):

            # Se o processo ainda não terminou:
            # volta para o fim da fila
            if current is not None and current.remaining_time > 0:
                ready.append(current)

            # Existe alguém pronto?
            if ready:

                # FIFO
                first = ready[0]

                # Desempate:
                # se vários chegaram juntos
                same_arrival = [
                    p for p in ready
                    if p.arrival_time == first.arrival_time
                ]

                if len(same_arrival) > 1:

                    # Escolha aleatória
                    chosen = rng.choice(same_arrival)

                    ready.remove(chosen)

                else:
                    chosen = ready.popleft()

                # Troca de contexto
                if current is not None and chosen is not current:

                    overhead_remaining = context_switch_cost

                    timeline.append((t, "CTX", "context_switch"))

                    overhead_remaining -= 1
                    t += 1

                    current = chosen
                    time_slice = 0

                    continue

                else:
                    current = chosen
                    time_slice = 0

            else:
                # CPU sem processo
                timeline.append((t, "IDLE", "idle"))
                t += 1
                continue

        # ============================================================
        # EXECUÇÃO DO PROCESSO
        # ============================================================

        # Primeira vez executando
        if current.start_time is None:
            current.start_time = t

        # Marca timeline
        timeline.append((t, current.pid, "run"))

        # Consome CPU
        current.remaining_time -= 1

        # Conta quantum
        time_slice += 1

        # Avança relógio
        t += 1

        # ============================================================
        # PROCESSO TERMINOU?
        # ============================================================
        if current.remaining_time == 0:

            current.finish_time = t

            done_count += 1

            # força troca de contexto
            if ready:
                overhead_remaining = context_switch_cost

            current = None
            time_slice = 0

    return timeline, procs


# =============================================================================
# SRTF - SHORTEST REMAINING TIME FIRST
# =============================================================================
def simulate_srtf(
        processes: list[Process],
        context_switch_cost: int,
        seed: int = 42
):
    """
    Simula SRTF.

    Características:
        • Preemptivo
        • Sempre escolhe o processo com menor remaining_time
        • Se chegar um processo menor:
              ocorre preempção
    """

    rng = random.Random(seed)

    procs = clone_processes(processes)

    procs.sort(key=lambda p: p.arrival_time)

    timeline = []

    ready = []

    current = None

    t = 0

    overhead_remaining = 0

    done_count = 0

    while done_count < len(procs):

        # ============================================================
        # CHEGADA DE PROCESSOS
        # ============================================================
        for p in procs:

            if (
                p.arrival_time == t
                and p.remaining_time == p.burst_time
                and p.finish_time is None
            ):

                if p not in ready and p is not current:
                    ready.append(p)

        # ============================================================
        # TROCA DE CONTEXTO
        # ============================================================
        if overhead_remaining > 0:

            timeline.append((t, "CTX", "context_switch"))

            overhead_remaining -= 1

            t += 1

            continue

        # ============================================================
        # PREEMPÇÃO
        # ============================================================
        if current is not None and ready:

            # menor tempo restante na fila
            min_remaining = min(
                p.remaining_time for p in ready
            )

            # chegou alguém menor?
            if min_remaining < current.remaining_time:

                # devolve atual para fila
                ready.append(current)

                # candidatos empatados
                candidates = [
                    p for p in ready
                    if p.remaining_time == min_remaining
                ]

                chosen = rng.choice(candidates)

                ready.remove(chosen)

                current = chosen

                # troca de contexto
                overhead_remaining = context_switch_cost

                timeline.append((t, "CTX", "context_switch"))

                overhead_remaining -= 1
                t += 1

                continue

        # ============================================================
        # CPU OCIOSA
        # ============================================================
        if current is None:

            if ready:

                # pega menor remaining_time
                min_remaining = min(
                    p.remaining_time for p in ready
                )

                candidates = [
                    p for p in ready
                    if p.remaining_time == min_remaining
                ]

                chosen = rng.choice(candidates)

                ready.remove(chosen)

                current = chosen

            else:

                timeline.append((t, "IDLE", "idle"))

                t += 1

                continue

        # ============================================================
        # EXECUÇÃO
        # ============================================================

        # Primeira vez executando
        if current.start_time is None:
            current.start_time = t

        timeline.append((t, current.pid, "run"))

        current.remaining_time -= 1

        t += 1

        # ============================================================
        # TERMINOU?
        # ============================================================
        if current.remaining_time == 0:

            current.finish_time = t

            done_count += 1

            current = None

            if ready:
                overhead_remaining = context_switch_cost

    return timeline, procs


# =============================================================================
# EXIBIÇÃO VISUAL
# =============================================================================

# Cores ANSI
COLORS = {
    "P01": "\033[91m",
    "P02": "\033[92m",
    "P03": "\033[93m",
    "P04": "\033[94m",
    "P05": "\033[95m",

    "CTX": "\033[90m",
    "IDLE": "\033[37m",
}

RESET = "\033[0m"
BOLD = "\033[1m"


def color(pid: str, text: str) -> str:
    """
    Aplica cor ANSI.
    """
    return COLORS.get(pid, "") + text + RESET


def print_timeline(timeline, label, max_ticks=80):
    """
    Mostra a sequência de execução.

    Exemplo:
        0101CC0202...
    """

    print(f"\nTimeline — {label}")

    line = "  "

    for t, pid, _ in timeline[:max_ticks]:

        if pid == "CTX":
            line += color("CTX", "C")

        elif pid == "IDLE":
            line += color("IDLE", "_")

        else:
            line += color(pid, pid[-2:])

    print(line)


def print_metrics(metrics, label):
    """
    Mostra métricas calculadas.
    """

    print(f"\nMétricas — {label}")

    print(
        f"Tempo médio resposta: "
        f"{metrics['avg_response']:.2f}"
    )

    print(
        f"Tempo médio retorno: "
        f"{metrics['avg_turnaround']:.2f}"
    )

    print(
        f"Vazão: "
        f"{metrics['throughput']}"
    )


# =============================================================================
# GERAÇÃO DE WORKLOAD
# =============================================================================
def generate_workload(
        n: int,
        scenario: str,
        seed: int = 42
):
    """
    Gera processos aleatórios.

    Cenários:

        curto:
            bursts pequenos

        longo:
            bursts grandes

        misto:
            mistura os dois
    """

    rng = random.Random(seed)

    processes = []

    for i in range(n):

        pid = f"P{str(i+1).zfill(2)}"

        # chegada aleatória
        arrival_time = rng.randint(0, 10)

        # define burst conforme cenário
        if scenario == "curto":

            burst_time = rng.randint(1, 5)

        elif scenario == "longo":

            burst_time = rng.randint(20, 50)

        elif scenario == "misto":

            if rng.random() < 0.5:
                burst_time = rng.randint(1, 5)
            else:
                burst_time = rng.randint(20, 50)

        else:
            raise ValueError("Cenário inválido")

        processes.append({
            "pid": pid,
            "arrival_time": arrival_time,
            "burst_time": burst_time
        })

    return processes


# =============================================================================
# CONFIGURAÇÃO DO EXPERIMENTO
# =============================================================================
SPEC = {
    "spec_version": "1.0",

    "challenge_id": "rr_srtf_preemptivo_demo",

    "metadata": {

        # custo da troca de contexto
        "context_switch_cost": 1,

        # janela da vazão
        "throughput_window_T": 100,

        # algoritmos comparados
        "algorithms": ["RR", "SRTF"],

        # quantums testados no RR
        "rr_quantums": [1, 2, 4, 8, 16]
    },

    "workload": {

        "time_unit": "ticks",

        "processes": [
            {"pid": "P01", "arrival_time": 0, "burst_time": 5},
            {"pid": "P02", "arrival_time": 1, "burst_time": 17},
            {"pid": "P03", "arrival_time": 2, "burst_time": 3},
            {"pid": "P04", "arrival_time": 4, "burst_time": 22},
            {"pid": "P05", "arrival_time": 6, "burst_time": 7},
        ]
    }
}


# =============================================================================
# MAIN
# =============================================================================
def main():

    meta = SPEC["metadata"]

    ctx_cost = meta["context_switch_cost"]

    window_T = meta["throughput_window_T"]

    quantums = meta["rr_quantums"]

    # Cenários testados
    scenarios = ["curto", "longo", "misto"]

    # ================================================================
    # LOOP DOS CENÁRIOS
    # ================================================================
    for scenario in scenarios:

        print("\n" + "=" * 70)

        print(f"CENÁRIO: {scenario.upper()}")

        print("=" * 70)

        # Gera workload aleatório
        SPEC["workload"]["processes"] = generate_workload(
            5,
            scenario
        )

        # Carrega processos
        processes = load_processes(SPEC)

        # ============================================================
        # MOSTRA CARGA
        # ============================================================
        print("\nCarga de trabalho:")

        for p in processes:

            print(
                f"{p.pid} | "
                f"arrival={p.arrival_time} | "
                f"burst={p.burst_time}"
            )

        results = {}

        # ============================================================
        # ROUND ROBIN
        # ============================================================
        print("\nROUND ROBIN")

        for q in quantums:

            label = f"RR(q={q})"

            timeline, procs_done = simulate_rr(
                processes,
                q,
                ctx_cost
            )

            metrics = compute_metrics(
                procs_done,
                window_T
            )

            results[label] = metrics

            print_timeline(timeline, label)

            print_metrics(metrics, label)

        # ============================================================
        # SRTF
        # ============================================================
        print("\nSRTF")

        timeline, procs_done = simulate_srtf(
            processes,
            ctx_cost
        )

        metrics = compute_metrics(
            procs_done,
            window_T
        )

        results["SRTF"] = metrics

        print_timeline(timeline, "SRTF")

        print_metrics(metrics, "SRTF")

        # ============================================================
        # COMPARATIVO FINAL
        # ============================================================
        print("\nCOMPARATIVO")

        for algo, m in results.items():

            print(
                f"{algo:<15} "
                f"Resp={m['avg_response']:.2f} "
                f"Turn={m['avg_turnaround']:.2f} "
                f"Thr={m['throughput']}"
            )

        # ============================================================
        # ANÁLISE TEÓRICA
        # ============================================================
        print("\nANÁLISE")

        print("""
ROUND ROBIN:
    Vantagens:
        • Justiça/Fairness
        • Evita inanição
        • Bom para sistemas interativos

    Desvantagens:
        • Muito overhead se quantum pequeno
        • Quantum grande vira FCFS

SRTF:
    Vantagens:
        • Minimiza turnaround médio
        • Favorece jobs curtos

    Desvantagens:
        • Pode causar starvation
        • Precisa conhecer burst time
        • Muitas preempções
""")


# =============================================================================
# EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    main()
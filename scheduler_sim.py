import json
import random
import copy
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# ── Estruturas de dados ──────────────────────────────────────────────────────

@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    remaining_time: int = field(init=False)
    start_time: Optional[int] = field(default=None, init=False)
    finish_time: Optional[int] = field(default=None, init=False)

    def __post_init__(self):
        self.remaining_time = self.burst_time

    def reset(self):
        self.remaining_time = self.burst_time
        self.start_time = None
        self.finish_time = None


def load_processes(spec: dict) -> list[Process]:
    return [
        Process(p["pid"], p["arrival_time"], p["burst_time"])
        for p in spec["workload"]["processes"]
    ]


def clone_processes(processes: list[Process]) -> list[Process]:
    return [copy.deepcopy(p) for p in processes]


# ── Métricas ─────────────────────────────────────────────────────────────────

def compute_metrics(processes: list[Process], window_T: int) -> dict:
    response_times = [p.start_time - p.arrival_time for p in processes if p.start_time is not None]
    turnaround_times = [p.finish_time - p.arrival_time for p in processes if p.finish_time is not None]
    completed_in_T = sum(1 for p in processes if p.finish_time is not None and p.finish_time <= window_T)

    def mean(lst): return sum(lst) / len(lst) if lst else 0.0
    def std(lst):
        if len(lst) < 2: return 0.0
        m = mean(lst)
        return (sum((x - m) ** 2 for x in lst) / len(lst)) ** 0.5

    return {
        "avg_response":   mean(response_times),
        "std_response":   std(response_times),
        "avg_turnaround": mean(turnaround_times),
        "std_turnaround": std(turnaround_times),
        "throughput":     completed_in_T,
    }


# ── Round Robin ───────────────────────────────────────────────────────────────

def simulate_rr(processes: list[Process], quantum: int,
                context_switch_cost: int, seed: int = 42) -> tuple[list, list[Process]]:
    rng = random.Random(seed)
    procs = clone_processes(processes)
    procs.sort(key=lambda p: p.arrival_time)

    timeline = []          # (tick, pid, event)  event: RUN | CTX
    ready: deque[Process] = deque()
    current: Optional[Process] = None
    time_slice = 0
    t = 0
    total = sum(p.burst_time for p in procs)
    done_count = 0
    overhead_remaining = 0

    while done_count < len(procs):
        # Novos chegando
        for p in procs:
            if p.arrival_time == t and p.start_time is None and p.remaining_time == p.burst_time:
                if p not in ready and p is not current:
                    ready.append(p)

        # Contexto overhead
        if overhead_remaining > 0:
            timeline.append((t, "CTX", "context_switch"))
            overhead_remaining -= 1
            t += 1
            # Chegadas durante CTX
            for p in procs:
                if p.arrival_time == t and p.start_time is None and p.remaining_time == p.burst_time:
                    if p not in ready and p is not current:
                        ready.append(p)
            continue

        # Escolhe processo
        if current is None or current.remaining_time == 0 or time_slice == quantum:
            # Devolve à fila se não terminou e não esgotou
            if current is not None and current.remaining_time > 0:
                ready.append(current)
            
            if ready:
                # Pega o primeiro da fila (FIFO)
                first = ready[0]

                # Verifica empate de arrival_time com outros na fila
                same_arrival = [p for p in ready if p.arrival_time == first.arrival_time]

                if len(same_arrival) > 1:
                    # Desempate aleatório apenas entre empatados
                    chosen = rng.choice(same_arrival)
                    ready.remove(chosen)
                else:
                    # Sem empate → segue FIFO normal
                    chosen = ready.popleft()

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
                # CPU ociosa
                timeline.append((t, "IDLE", "idle"))
                t += 1
                continue

        # Executa
        if current.start_time is None:
            current.start_time = t

        timeline.append((t, current.pid, "run"))
        current.remaining_time -= 1
        time_slice += 1
        t += 1

        # Chegadas no próximo tick
        for p in procs:
            if p.arrival_time == t and p.start_time is None and p.remaining_time == p.burst_time:
                if p not in ready and p is not current:
                    ready.append(p)

        if current.remaining_time == 0:
            current.finish_time = t
            done_count += 1
            # Força troca
            if ready:
                overhead_remaining = context_switch_cost
            current = None
            time_slice = 0

    return timeline, procs


# ── SRTF ──────────────────────────────────────────────────────────────────────

def simulate_srtf(processes: list[Process],
                  context_switch_cost: int, seed: int = 42) -> tuple[list, list[Process]]:
    rng = random.Random(seed)
    procs = clone_processes(processes)
    procs.sort(key=lambda p: p.arrival_time)

    timeline = []
    ready: list[Process] = []
    current: Optional[Process] = None
    t = 0
    overhead_remaining = 0
    done_count = 0

    while done_count < len(procs):
        # Chegadas
        for p in procs:
            if p.arrival_time == t and p.remaining_time == p.burst_time and p.finish_time is None:
                if p not in ready and p is not current:
                    ready.append(p)

        # Overhead de contexto
        if overhead_remaining > 0:
            timeline.append((t, "CTX", "context_switch"))
            overhead_remaining -= 1
            t += 1
            for p in procs:
                if p.arrival_time == t and p.remaining_time == p.burst_time and p.finish_time is None:
                    if p not in ready and p is not current:
                        ready.append(p)
            continue

        # Preempção: existe alguém na fila com remaining < current?
        if current is not None and ready:
            min_remaining = min(p.remaining_time for p in ready)
            if min_remaining < current.remaining_time:
                # Preempt
                ready.append(current)
                candidates = [p for p in ready if p.remaining_time == min_remaining]
                chosen = rng.choice(candidates)
                ready.remove(chosen)
                current = chosen
                overhead_remaining = context_switch_cost
                timeline.append((t, "CTX", "context_switch"))
                overhead_remaining -= 1
                t += 1
                continue

        # Sem processo atual
        if current is None:
            if ready:
                min_remaining = min(p.remaining_time for p in ready)
                candidates = [p for p in ready if p.remaining_time == min_remaining]
                chosen = rng.choice(candidates)
                ready.remove(chosen)
                if current is not None:
                    overhead_remaining = context_switch_cost
                current = chosen
            else:
                timeline.append((t, "IDLE", "idle"))
                t += 1
                continue

        # Executa
        if current.start_time is None:
            current.start_time = t

        timeline.append((t, current.pid, "run"))
        current.remaining_time -= 1
        t += 1

        for p in procs:
            if p.arrival_time == t and p.remaining_time == p.burst_time and p.finish_time is None:
                if p not in ready and p is not current:
                    ready.append(p)

        if current.remaining_time == 0:
            current.finish_time = t
            done_count += 1
            prev = current
            current = None
            if ready:
                overhead_remaining = context_switch_cost

    return timeline, procs


# ── Exibição ──────────────────────────────────────────────────────────────────

COLORS = {
    "P01": "\033[91m", "P02": "\033[92m", "P03": "\033[93m",
    "P04": "\033[94m", "P05": "\033[95m", "P06": "\033[96m",
    "CTX": "\033[90m", "IDLE": "\033[37m",
}
RESET = "\033[0m"
BOLD  = "\033[1m"


def color(pid: str, text: str) -> str:
    return COLORS.get(pid, "") + text + RESET


def print_timeline(timeline: list, label: str, max_ticks: int = 80):
    print(f"\n  {BOLD}Sequência de execução — {label}{RESET}")
    print("  " + "─" * 60)
    line = "  "
    for t, pid, _ in timeline[:max_ticks]:
        if pid == "CTX":
            line += color("CTX", "C")
        elif pid == "IDLE":
            line += color("IDLE", "_")
        else:
            line += color(pid, pid[-2:])  # últimas 2 chars do pid
    if len(timeline) > max_ticks:
        line += f"  …(+{len(timeline)-max_ticks} ticks)"
    print(line)
    # Régua de tempo
    ruler = "  "
    for i in range(min(len(timeline), max_ticks)):
        ruler += "|" if i % 10 == 0 else " "
    print(ruler)
    ticks_label = "  "
    for i in range(0, min(len(timeline), max_ticks), 10):
        ticks_label += f"{i:<10}"
    print(ticks_label)


def print_metrics(metrics: dict, label: str):
    print(f"\n  {BOLD}Métricas — {label}{RESET}")
    print(f"  {'Resp. médio':<22}: {metrics['avg_response']:6.2f} ± {metrics['std_response']:.2f}")
    print(f"  {'Retorno médio':<22}: {metrics['avg_turnaround']:6.2f} ± {metrics['std_turnaround']:.2f}")
    print(f"  {'Vazão (T={100})':<22}: {metrics['throughput']} processos")


def print_process_table(procs: list[Process], label: str):
    print(f"\n  {BOLD}Tabela de processos — {label}{RESET}")
    print(f"  {'PID':<6} {'Chegada':>8} {'Burst':>6} {'Início':>7} {'Fim':>6} {'Resposta':>9} {'Retorno':>8}")
    print("  " + "─" * 58)
    for p in procs:
        resp = (p.start_time - p.arrival_time) if p.start_time is not None else "-"
        turn = (p.finish_time - p.arrival_time) if p.finish_time is not None else "-"
        print(f"  {p.pid:<6} {p.arrival_time:>8} {p.burst_time:>6} "
              f"{str(p.start_time):>7} {str(p.finish_time):>6} "
              f"{str(resp):>9} {str(turn):>8}")

# Geração de um Workload controlado
def generate_workload(n: int, scenario: str, seed: int = 42):
    rng = random.Random(seed)
    processes = []

    for i in range(n):
        pid = f"P{str(i+1).zfill(2)}"
        arrival_time = rng.randint(0, 10)

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

# ── Main ──────────────────────────────────────────────────────────────────────

SPEC = {
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
            {"pid": "P01", "arrival_time": 0,  "burst_time": 5},
            {"pid": "P02", "arrival_time": 1,  "burst_time": 17},
            {"pid": "P03", "arrival_time": 2,  "burst_time": 3},
            {"pid": "P04", "arrival_time": 4,  "burst_time": 22},
            {"pid": "P05", "arrival_time": 6,  "burst_time": 7},
        ]
    }
}


def main():
    meta = SPEC["metadata"]
    ctx_cost = meta["context_switch_cost"]
    window_T = meta["throughput_window_T"]
    quantums = meta["rr_quantums"]

    scenarios = ["curto", "longo", "misto"] # Define o cenário de carga de trabalho que vai ser avaliado, existem ["curto", "longo", "misto"]

    for scenario in scenarios:
        print(f"\n{'='*70}")
        print(f"  CENÁRIO: {scenario.upper()}")
        print(f"{'='*70}")

        SPEC["workload"]["processes"] = generate_workload(5, scenario)
        processes = load_processes(SPEC)

        print(f"\n{'═'*70}")
        print(f"  {BOLD}SIMULADOR DE ESCALONAMENTO — RR vs SRTF{RESET}")
        print(f"{'═'*70}")
        print(f"  Processos: {len(processes)} | Custo troca de contexto: {ctx_cost} tick(s)")
        print(f"  Janela de vazão: T = {window_T}")

        print(f"\n  {BOLD}Carga de trabalho:{RESET}")
        print(f"  {'PID':<6} {'Chegada':>8} {'Burst':>6}")
        print("  " + "─" * 24)
        for p in processes:
            print(f"  {p.pid:<6} {p.arrival_time:>8} {p.burst_time:>6}")

        results = {}

        # ── RR ────────────────────────────────────────────────────────────────────
        print(f"\n{'─'*70}")
        print(f"  {BOLD}ROUND ROBIN (RR){RESET}")
        print(f"{'─'*70}")

        for q in quantums:
            label = f"RR (quantum={q})"
            timeline, procs_done = simulate_rr(processes, q, ctx_cost)
            metrics = compute_metrics(procs_done, window_T)
            results[label] = metrics
            print_timeline(timeline, label)
            print_process_table(procs_done, label)
            print_metrics(metrics, label)

        # ── SRTF ──────────────────────────────────────────────────────────────────
        print(f"\n{'─'*70}")
        print(f"  {BOLD}SRTF (Shortest Remaining Time First){RESET}")
        print(f"{'─'*70}")

        timeline, procs_done = simulate_srtf(processes, ctx_cost)
        metrics = compute_metrics(procs_done, window_T)
        results["SRTF"] = metrics
        print_timeline(timeline, "SRTF")
        print_process_table(procs_done, "SRTF")
        print_metrics(metrics, "SRTF")

    # ── Tabela comparativa ────────────────────────────────────────────────────
        print(f"\n{'═'*70}")
        print(f"  {BOLD}COMPARATIVO GERAL{RESET}")
        print(f"{'═'*70}")
        print(f"  {'Algoritmo':<22} {'Resp. médio':>12} {'Ret. médio':>12} {'Vazão':>8}")
        print("  " + "─" * 58)
        for algo, m in results.items():
            print(f"  {algo:<22} {m['avg_response']:>10.2f}   {m['avg_turnaround']:>10.2f}   {m['throughput']:>6}")

        # ── Análise ───────────────────────────────────────────────────────────────
        print(f"\n{'═'*70}")
        print(f"  {BOLD}ANÁLISE: VANTAGENS E DESVANTAGENS{RESET}")
        print(f"{'═'*70}")

        print(f"""
    {BOLD}Round Robin (RR){RESET}
    ┌─────────────────────────────────────────────────────────┐
    │ Vantagens                                               │
    │  • Fairness: todos os processos recebem fatias iguais   │
    │  • Bom tempo de resposta para processos curtos (q peq.) │
    │  • Ausência de inanição                                 │
    ├─────────────────────────────────────────────────────────┤
    │ Desvantagens                                            │
    │  • Quantum pequeno → alto overhead de troca de contexto │
    │  • Quantum grande → degenera para FCFS                  │
    │  • Processos curtos podem esperar por processos longos  │
    └─────────────────────────────────────────────────────────┘

    {BOLD}SRTF (Shortest Remaining Time First){RESET}
    ┌─────────────────────────────────────────────────────────┐
    │ Vantagens                                               │
    │  • Minimiza o tempo médio de retorno (ótimo teórico)    │
    │  • Processos curtos terminam rapidamente                │
    ├─────────────────────────────────────────────────────────┤
    │ Desvantagens                                            │
    │  • Inanição: processos longos podem esperar para sempre │
    │  • Requer conhecimento prévio do burst time             │
    │  • Alto overhead se muitos processos curtos chegam      │
    └─────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()

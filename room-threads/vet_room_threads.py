from __future__ import annotations

import argparse
import json
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EMPTY = "EMPTY"
DOG = "DOG"
CAT = "CAT"
DOGS = "DOGS"
CATS = "CATS"

STATE_BY_SPECIES = {
    DOG: DOGS,
    CAT: CATS,
}

OPPOSITE_SPECIES = {
    DOG: CAT,
    CAT: DOG,
}


@dataclass(frozen=True)
class Animal:
    id: str
    species: str
    arrival_time: int
    rest_duration: int


class VetRoom:
    def __init__(self, mode: str, started_at: float) -> None:
        self.mode = mode
        self.started_at = started_at
        self.condition = threading.Condition()
        self.sign_state = EMPTY
        self.inside = {DOG: 0, CAT: 0}
        self.waiting = {DOG: 0, CAT: 0}
        self.waiting_ids = {DOG: set[str](), CAT: set[str]()}
        self.fair_batch_ids: set[str] = set()
        self.arrived_at: dict[str, float] = {}
        self.wait_times: dict[str, float] = {}
        self.entry_order: list[str] = []
        self.exit_order: list[str] = []
        self.violations = 0

    def enter(self, animal: Animal) -> None:
        with self.condition:
            self.arrived_at[animal.id] = time.monotonic()
            self.waiting[animal.species] += 1
            self.waiting_ids[animal.species].add(animal.id)
            self._log("ARRIVE", animal)

            while not self._can_enter(animal):
                self._log("WAIT  ", animal)
                self.condition.wait()

            if self.sign_state == EMPTY:
                self.sign_state = STATE_BY_SPECIES[animal.species]
                if self.mode == "fair":
                    self.fair_batch_ids = set(self.waiting_ids[animal.species])
                self._log("SIGN  ", state=self.sign_state)

            self.waiting[animal.species] -= 1
            self.waiting_ids[animal.species].remove(animal.id)
            self.inside[animal.species] += 1
            self.entry_order.append(animal.id)
            self.wait_times[animal.id] = time.monotonic() - self.arrived_at[animal.id]
            self._assert_exclusion()
            self._log("ENTER ", animal)

    def leave(self, animal: Animal) -> None:
        with self.condition:
            self.inside[animal.species] -= 1
            self.exit_order.append(animal.id)
            self._log("EXIT  ", animal)

            if self.inside[DOG] == 0 and self.inside[CAT] == 0:
                self.sign_state = EMPTY
                self.fair_batch_ids.clear()
                self._log("SIGN  ", state=EMPTY)

            self.condition.notify_all()

    def summary(self) -> None:
        with self.condition:
            print()
            print("SUMMARY")
            print(f"Final sign state: {self.sign_state}")
            print(f"Dogs inside: {self.inside[DOG]}")
            print(f"Cats inside: {self.inside[CAT]}")
            print(f"Mutual exclusion violations: {self.violations}")
            print(f"Entry order: {', '.join(self.entry_order)}")
            print(f"Exit order: {', '.join(self.exit_order)}")
            print("Wait times:")
            for animal_id in sorted(self.wait_times):
                print(f"  {animal_id}: {self.wait_times[animal_id]:.3f}s")

    def _can_enter(self, animal: Animal) -> bool:
        species = animal.species
        if self.sign_state == EMPTY:
            if self.mode == "fair":
                return self._is_fair_turn(species)
            return True

        if self.sign_state != STATE_BY_SPECIES[species]:
            return False

        if self.mode == "fair":
            opposite = OPPOSITE_SPECIES[species]
            if self.waiting[opposite] > 0:
                return animal.id in self.fair_batch_ids

        return True

    def _is_fair_turn(self, species: str) -> bool:
        opposite = OPPOSITE_SPECIES[species]
        if self.waiting[opposite] == 0:
            return True
        if self.waiting[species] == 0:
            return False

        own_first = self._oldest_waiting_arrival(species)
        opposite_first = self._oldest_waiting_arrival(opposite)
        if own_first is None:
            return False
        if opposite_first is None:
            return True
        return own_first <= opposite_first

    def _oldest_waiting_arrival(self, species: str) -> float | None:
        oldest: float | None = None
        for animal_id in self.waiting_ids[species]:
            arrived_at = self.arrived_at[animal_id]
            if oldest is None or arrived_at < oldest:
                oldest = arrived_at
        return oldest

    def _assert_exclusion(self) -> None:
        if self.inside[DOG] > 0 and self.inside[CAT] > 0:
            self.violations += 1
            raise RuntimeError("DOG and CAT are inside the room at the same time")

    def _log(self, event: str, animal: Animal | None = None, state: str | None = None) -> None:
        elapsed = time.monotonic() - self.started_at
        room = f"sign={self.sign_state} dogs={self.inside[DOG]} cats={self.inside[CAT]}"
        if animal is not None:
            print(f"[{elapsed:7.3f}s] {event} | {animal.id} ({animal.species}) | {room}", flush=True)
            return
        print(f"[{elapsed:7.3f}s] {event} | {state} | {room}", flush=True)


def load_input(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def parse_animals(data: dict[str, Any]) -> list[Animal]:
    validate_metadata(data)

    raw_animals = data.get("workload", {}).get("animals")
    if not isinstance(raw_animals, list):
        raise SystemExit("Invalid input: workload.animals must be a list")

    animals: list[Animal] = []
    seen_ids: set[str] = set()

    for raw in raw_animals:
        if not isinstance(raw, dict):
            raise SystemExit("Invalid input: each animal must be an object")

        animal_id = raw.get("id")
        species = raw.get("species")
        arrival_time = raw.get("arrival_time")
        rest_duration = raw.get("rest_duration")

        if not isinstance(animal_id, str) or not animal_id:
            raise SystemExit("Invalid input: every animal needs a non-empty string id")
        if animal_id in seen_ids:
            raise SystemExit(f"Invalid input: duplicated animal id {animal_id}")
        if species not in {DOG, CAT}:
            raise SystemExit(f"Invalid input: {animal_id} has unsupported species {species!r}")
        if not isinstance(arrival_time, int) or arrival_time < 0:
            raise SystemExit(f"Invalid input: {animal_id} arrival_time must be >= 0")
        if not isinstance(rest_duration, int) or rest_duration <= 0:
            raise SystemExit(f"Invalid input: {animal_id} rest_duration must be > 0")

        seen_ids.add(animal_id)
        animals.append(Animal(animal_id, species, arrival_time, rest_duration))

    return sorted(animals, key=lambda animal: (animal.arrival_time, animal.id))


def validate_metadata(data: dict[str, Any]) -> None:
    if data.get("spec_version") != "1.0":
        raise SystemExit("Invalid input: spec_version must be 1.0")
    if data.get("metadata", {}).get("room_count") != 1:
        raise SystemExit("Invalid input: metadata.room_count must be 1")

    allowed_states = data.get("metadata", {}).get("allowed_states")
    if allowed_states != [EMPTY, DOGS, CATS]:
        raise SystemExit("Invalid input: metadata.allowed_states must be ['EMPTY', 'DOGS', 'CATS']")

    sign_change_latency = data.get("metadata", {}).get("sign_change_latency")
    if sign_change_latency != 0:
        raise SystemExit("Invalid input: only sign_change_latency 0 is supported")

    initial_state = data.get("room", {}).get("initial_sign_state")
    if initial_state != EMPTY:
        raise SystemExit("Invalid input: room.initial_sign_state must be EMPTY")


def animal_thread(animal: Animal, room: VetRoom, tick_seconds: float) -> None:
    time.sleep(animal.arrival_time * tick_seconds)
    time.sleep(random.uniform(0.0, tick_seconds / 2))
    room.enter(animal)
    time.sleep(animal.rest_duration * tick_seconds)
    room.leave(animal)


def run_mode(mode: str, animals: list[Animal], tick_seconds: float) -> None:
    print(f"MODE: {mode}")
    if mode == "unfair":
        print("Policy: same-species arrivals may enter even while the opposite species is waiting.")
    else:
        print("Policy: once the opposite species is waiting, new same-species arrivals are held back.")
    print()

    started_at = time.monotonic()
    room = VetRoom(mode, started_at)
    threads = [
        threading.Thread(
            target=animal_thread,
            name=f"{animal.id}-{animal.species}",
            args=(animal, room, tick_seconds),
        )
        for animal in animals
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    room.summary()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Veterinary rest room synchronization demo with threads")
    parser.add_argument("--mode", choices=["unfair", "fair"], required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--tick-seconds",
        type=float,
        default=0.2,
        help="Real seconds used to represent one JSON tick.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.tick_seconds <= 0:
        raise SystemExit("Invalid argument: --tick-seconds must be > 0")

    data = load_input(args.input)
    animals = parse_animals(data)

    run_mode(args.mode, animals, args.tick_seconds)


if __name__ == "__main__":
    main()

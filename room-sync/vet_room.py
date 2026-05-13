from __future__ import annotations

import argparse
import json
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

SPECIES_BY_STATE = {
    DOGS: DOG,
    CATS: CAT,
}


@dataclass(frozen=True)
class Animal:
    id: str
    species: str
    arrival_time: int
    rest_duration: int


@dataclass(frozen=True)
class Stay:
    animal: Animal
    exit_time: int


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


def run_unfair(animals: list[Animal]) -> None:
    print("MODE: unfair")
    print("Policy: same-species arrivals may enter even while the opposite species is waiting.")
    print()

    time = 0
    sign_state = EMPTY
    next_arrival = 0
    waiting: list[Animal] = []
    inside: list[Stay] = []
    entry_order: list[str] = []
    exit_order: list[str] = []
    wait_times: dict[str, int] = {}

    while len(exit_order) < len(animals):
        while next_arrival < len(animals) and animals[next_arrival].arrival_time == time:
            animal = animals[next_arrival]
            waiting.append(animal)
            waiting.sort(key=lambda item: (item.arrival_time, item.id))
            print(f"{time:04d} | ARRIVE | {animal.id} ({animal.species})")
            next_arrival += 1

        exiting = [stay for stay in inside if stay.exit_time == time]
        for stay in sorted(exiting, key=lambda item: item.animal.id):
            inside.remove(stay)
            exit_order.append(stay.animal.id)
            print(f"{time:04d} | EXIT   | {stay.animal.id} ({stay.animal.species})")

        if not inside and sign_state != EMPTY:
            sign_state = EMPTY
            print(f"{time:04d} | SIGN   | EMPTY")

        admitted = admit_unfair(time, waiting, inside, sign_state, wait_times, entry_order)
        if admitted and sign_state == EMPTY:
            sign_state = STATE_BY_SPECIES[admitted[0].animal.species]
            print(f"{time:04d} | SIGN   | {sign_state}")
            # The sign changed from EMPTY, so retry admission with the chosen state.
            for stay in admitted:
                inside.append(stay)
        elif admitted:
            for stay in admitted:
                inside.append(stay)

        if waiting:
            blocked = ", ".join(animal.id for animal in waiting)
            print(f"{time:04d} | WAIT   | {blocked}")

        time += 1

    print_summary(sign_state, entry_order, exit_order, wait_times)


def admit_unfair(
    time: int,
    waiting: list[Animal],
    inside: list[Stay],
    sign_state: str,
    wait_times: dict[str, int],
    entry_order: list[str],
) -> list[Stay]:
    if not waiting:
        return []

    target_state = sign_state
    if target_state == EMPTY:
        target_state = STATE_BY_SPECIES[waiting[0].species]

    allowed_species = SPECIES_BY_STATE[target_state]
    admitted_animals = [animal for animal in waiting if animal.species == allowed_species]
    admitted_stays: list[Stay] = []

    for animal in admitted_animals:
        waiting.remove(animal)
        wait_times[animal.id] = time - animal.arrival_time
        entry_order.append(animal.id)
        exit_time = time + animal.rest_duration
        admitted_stays.append(Stay(animal, exit_time))
        print(f"{time:04d} | ENTER  | {animal.id} ({animal.species}) exits_at={exit_time}")

    if violates_exclusion(inside, admitted_stays):
        raise SystemExit("Simulation error: DOG and CAT entered the room together")

    return admitted_stays


def violates_exclusion(inside: list[Stay], admitted: list[Stay]) -> bool:
    species = {stay.animal.species for stay in inside}
    species.update(stay.animal.species for stay in admitted)
    return len(species) > 1


def print_summary(
    sign_state: str,
    entry_order: list[str],
    exit_order: list[str],
    wait_times: dict[str, int],
) -> None:
    print()
    print("SUMMARY")
    print(f"Final sign state: {sign_state}")
    print(f"Entry order: {', '.join(entry_order)}")
    print(f"Exit order: {', '.join(exit_order)}")
    print("Wait times:")
    for animal_id in sorted(wait_times):
        print(f"  {animal_id}: {wait_times[animal_id]} ticks")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Veterinary rest room synchronization demo")
    parser.add_argument("--mode", choices=["unfair", "fair", "both"], required=True)
    parser.add_argument("--input", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data = load_input(args.input)
    animals = parse_animals(data)

    if args.mode == "unfair":
        run_unfair(animals)
        return

    raise SystemExit(f"Mode {args.mode!r} is not implemented yet. Implemented mode: unfair")


if __name__ == "__main__":
    main()

from __future__ import annotations

import random
from collections.abc import Iterable

from .logging_utils import get_logger


LOGGER = get_logger()


def sample_neighboring_warehouse_sets(
    active_warehouse_ids: Iterable[str],
    base_set: set[str],
    locked_warehouse_ids: set[str],
    max_samples: int,
    random_seed: int,
) -> list[set[str]]:
    if max_samples <= 0:
        return []

    base = sorted(base_set)
    locked = set(locked_warehouse_ids)
    warehouse_ids = sorted(active_warehouse_ids)
    alternatives = sorted(set(warehouse_ids) - set(base))
    rng = random.Random(random_seed)

    swap_pairs = [
        (remove_id, add_id) for remove_id in base if remove_id not in locked for add_id in alternatives
    ]
    rng.shuffle(swap_pairs)

    results: list[set[str]] = []
    seen: set[tuple[str, ...]] = {tuple(base)}
    for remove_id, add_id in swap_pairs:
        candidate = set(base)
        candidate.remove(remove_id)
        candidate.add(add_id)
        key = tuple(sorted(candidate))
        if key in seen:
            continue
        seen.add(key)
        results.append(candidate)
        if len(results) >= max_samples:
            break

    LOGGER.info(
        "Generated %d neighboring sampled warehouse set(s) from best-model solution",
        len(results),
    )
    return results

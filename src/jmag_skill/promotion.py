"""Enforce the candidate lifecycle and explicit approval gate."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


class PromotionError(RuntimeError):
    pass


TRANSITIONS = {
    "observed": {"candidate", "rejected"},
    "candidate": {"verified", "rejected"},
    "verified": {"approved", "rejected"},
    "approved": {"stable", "rejected"},
    "stable": set(), "rejected": set(),
}


def transition(manifest: dict[str, Any], target: str) -> dict[str, Any]:
    current = manifest.get("state")
    if target not in TRANSITIONS.get(current, set()):
        raise PromotionError(f"Invalid candidate transition: {current!r} -> {target!r}")
    result = deepcopy(manifest)
    result["state"] = target
    return result


def promote(manifest: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    if manifest.get("state") != "verified":
        raise PromotionError("Only a verified candidate can request promotion")
    if not approved:
        raise PromotionError("Explicit user approval is required")
    return transition(manifest, "approved")


def stabilize(manifest: dict[str, Any], verifier: Callable[[], bool]) -> dict[str, Any]:
    if manifest.get("state") != "approved":
        raise PromotionError("Only an approved candidate can become stable")
    if not verifier():
        raise PromotionError("Fresh verification failed; catalog was not updated")
    return transition(manifest, "stable")

from __future__ import annotations

from typing import Any, Iterable, NamedTuple

from django_components import Component, register


@register("spinwheel")
class SpinWheel(Component):
    template_file = "template.html"

    class Kwargs(NamedTuple):
        prizes: Iterable[Any]
        mode: str = "showcase"  # showcase | spinning | stop_on
        stop_on: Any | None = None
        confetti: bool = False
        wheel_id: str | None = None

    def _normalize_prize(self, prize: Any) -> dict[str, Any]:
        if isinstance(prize, dict):
            name = prize.get("name") or str(prize)
            icon = prize.get("icon") or "fa-solid fa-gift"
            prize_id = prize.get("id")
        else:
            name = getattr(prize, "name", None) or str(prize)
            icon = getattr(prize, "icon", None) or "fa-solid fa-gift"
            prize_id = getattr(prize, "id", None)
        return {
            "id": prize_id,
            "name": name,
            "icon": icon,
        }

    def _resolve_stop_index(self, prizes: list[dict[str, Any]], stop_on: Any) -> int | None:
        if stop_on is None:
            return None

        if isinstance(stop_on, int):
            if 0 <= stop_on < len(prizes):
                return stop_on
            for idx, prize in enumerate(prizes):
                if prize.get("id") == stop_on:
                    return idx
            return None

        if isinstance(stop_on, str):
            target = stop_on.strip().lower()
            for idx, prize in enumerate(prizes):
                if str(prize.get("name", "")).strip().lower() == target:
                    return idx
            return None

        # Object with id or name
        target_id = getattr(stop_on, "id", None)
        if target_id is not None:
            for idx, prize in enumerate(prizes):
                if prize.get("id") == target_id:
                    return idx

        target_name = getattr(stop_on, "name", None)
        if target_name:
            target = str(target_name).strip().lower()
            for idx, prize in enumerate(prizes):
                if str(prize.get("name", "")).strip().lower() == target:
                    return idx

        return None

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        prizes = [self._normalize_prize(prize) for prize in kwargs.prizes]
        mode = kwargs.mode if kwargs.mode in {"showcase", "spinning", "stop_on"} else "showcase"
        wheel_id = kwargs.wheel_id or "spinwheel"
        stop_index = self._resolve_stop_index(prizes, kwargs.stop_on)

        return {
            "prizes": prizes,
            "mode": mode,
            "stop_index": stop_index,
            "confetti": bool(kwargs.confetti),
            "wheel_id": wheel_id,
            "prizes_json_id": f"{wheel_id}-prizes",
        }

from typing import Protocol


class VisionProvider(Protocol):
    async def explain_changes(self, before_path: str, after_path: str, summary: str) -> str: ...


def get_vision_provider(provider_name: str) -> VisionProvider | None:
    """Provider factory. The local CV pipeline remains fully functional when disabled."""
    if provider_name.lower() in {"", "disabled", "none"}:
        return None
    # Provider-specific adapters can be registered here without coupling them to CV.
    return None

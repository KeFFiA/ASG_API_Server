def to_bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t")


__all__ = ["to_bool"]

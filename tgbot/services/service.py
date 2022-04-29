ARROWS = {False: "↑", True: "↓"}


def create_text_position(old_position: int | None, new_position: int) -> str:
    if old_position:
        return f"{old_position} → {new_position}" \
               f"{ARROWS[new_position > old_position] if old_position != new_position else ''}"
    else:
        return f" → {new_position}"


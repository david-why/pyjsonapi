from typing import Any, Dict, List, Tuple

__all__ = ['find_included']


def find_included(included: List[Dict[str, Any]], *keys: Tuple[str, str]):
    found = []
    for type, id in keys:
        for item in included:
            if item['type'] == type and item['id'] == id:
                found.append(item)
                break
        else:
            found.append(None)
    return found

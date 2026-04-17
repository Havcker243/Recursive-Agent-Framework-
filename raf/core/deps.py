from typing import Any, Dict, List, Tuple


class DependencyError(ValueError):
    pass


def validate_plan(plan: Dict[str, Any], max_children: int) -> None:
    children = plan.get("children", [])
    if len(children) > max_children:
        raise DependencyError("Plan exceeds max children")

    ids = [child["child_id"] for child in children]
    if len(ids) != len(set(ids)):
        raise DependencyError("Child IDs must be unique")

    id_set = set(ids)
    for child in children:
        for dep in child.get("depends_on", []):
            if dep not in id_set:
                raise DependencyError(f"Missing dependency: {dep}")

    _ = topo_sort(children)


def topo_sort(children: List[Dict[str, Any]]) -> List[str]:
    incoming = {child["child_id"]: 0 for child in children}
    edges = {child["child_id"]: [] for child in children}

    for child in children:
        for dep in child.get("depends_on", []):
            edges[dep].append(child["child_id"])
            incoming[child["child_id"]] += 1

    queue = [node for node, count in incoming.items() if count == 0]
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in edges[node]:
            incoming[neighbor] -= 1
            if incoming[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(children):
        raise DependencyError("Cycle detected in plan")

    return order

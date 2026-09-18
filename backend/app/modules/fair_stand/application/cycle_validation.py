from __future__ import annotations


class CyclicItemCompositionError(ValueError):
    pass


def assert_acyclic_components(edges: list[tuple[str, str]]) -> None:
    graph: dict[str, list[str]] = {}
    for parent, child in edges:
        graph.setdefault(parent, []).append(child)
        graph.setdefault(child, [])

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = stack[stack.index(node) :] + [node]
            raise CyclicItemCompositionError(" -> ".join(cycle))
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child, stack + [child])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [node])

"""Ordered DFS augmentation shared by the legacy scorer and strict diagnostics.

Neighbors are already ordered by the caller. This iterative implementation
preserves recursive successful-unwind ownership exactly; it neither reorders
edges nor optimizes distance or individual counts. No clock or cap is imposed
on the legacy caller. A bounded caller supplies its existing check callback.
"""


def ordered_event_owners(edges, *, check=None):
    """Return event-index -> target-index maximum-cardinality ownership."""
    tick = check if check is not None else lambda: None
    owners = {}
    for root in range(len(edges)):
        tick()
        seen = set()
        # Incoming is the event whose current owner this frame is relocating.
        stack = [(root, iter(edges[root]), None)]
        while stack:
            tick()
            target, neighbors, incoming = stack[-1]
            try:
                event = next(neighbors)
            except StopIteration:
                stack.pop()
                continue
            if event in seen:
                continue
            seen.add(event)
            if event in owners:
                owner = owners[event]
                stack.append((owner, iter(edges[owner]), event))
                continue
            owners[event] = target
            for index in range(len(stack) - 1, 0, -1):
                tick()
                owners[stack[index][2]] = stack[index - 1][0]
            break
    tick()
    return owners

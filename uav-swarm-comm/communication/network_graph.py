"""
communication/network_graph.py

Maintains the communication topology as a graph.
Tracks which UAVs can reach GCS, detects broken links,
and identifies disconnected nodes.
"""

import json
import math
import logging
from collections import deque

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from swarm.constants import GCS_NODE_ID, LINK_QUALITY_MIN, LINK_QUALITY_DEAD

logger = logging.getLogger(__name__)


class NetworkGraph:
    """
    Undirected weighted graph of communication links.

    Nodes  = GCS + all UAV IDs
    Edges  = active comm links with a quality weight
    """

    def __init__(self):
        # adjacency: {node_id: {neighbor_id: quality, ...}}
        self._adj: dict[str, dict[str, float]] = {}
        # snapshot of all defined links (active or not)
        self._all_links: list[dict] = []

    # ── Build / Load ──────────────────────────────────────

    def load_links(self, links_path: str) -> None:
        """Build graph from config/links.json."""
        with open(links_path, "r") as f:
            data = json.load(f)
        self._all_links = data["links"]
        self._rebuild()

    def load_links_from_list(self, links: list[dict]) -> None:
        """Build graph from a list of link dicts (for runtime use)."""
        self._all_links = links
        self._rebuild()

    def register_nodes(self, node_ids: list[str]) -> None:
        """Ensure every node exists in adjacency even if it has no links."""
        for nid in node_ids:
            if nid not in self._adj:
                self._adj[nid] = {}

    def _rebuild(self) -> None:
        """Reconstruct adjacency from _all_links (only active ones)."""
        self._adj.clear()
        self._adj[GCS_NODE_ID] = {}
        for link in self._all_links:
            if not link.get("active", True):
                continue
            if link["quality"] <= LINK_QUALITY_DEAD:
                continue
            a, b, q = link["from"], link["to"], link["quality"]
            self._adj.setdefault(a, {})[b] = q
            self._adj.setdefault(b, {})[a] = q

    # ── Queries ───────────────────────────────────────────

    def get_neighbors(self, node_id: str) -> dict[str, float]:
        """Return {neighbor: quality} for a node."""
        return dict(self._adj.get(node_id, {}))

    def get_all_nodes(self) -> list[str]:
        return list(self._adj.keys())

    def get_link_quality(self, a: str, b: str) -> float | None:
        """Return link quality between two nodes, or None if no link."""
        return self._adj.get(a, {}).get(b)

    def node_degree(self, node_id: str) -> int:
        """Number of active links for a node."""
        return len(self._adj.get(node_id, {}))

    # ── GCS Reachability ──────────────────────────────────

    def can_reach_gcs(self, node_id: str) -> bool:
        """BFS check: can node_id reach GCS through active links?"""
        if node_id == GCS_NODE_ID:
            return True
        if node_id not in self._adj:
            return False
        return self._bfs_reachable(node_id, GCS_NODE_ID)

    def find_path_to_gcs(self, node_id: str) -> list[str] | None:
        """BFS shortest-hop path from node_id to GCS. Returns path or None."""
        if node_id == GCS_NODE_ID:
            return [GCS_NODE_ID]
        if node_id not in self._adj:
            return None
        return self._bfs_path(node_id, GCS_NODE_ID)

    def get_all_reachable_from_gcs(self) -> set[str]:
        """Return set of all nodes reachable from GCS."""
        return self._bfs_all_reachable(GCS_NODE_ID)

    def get_disconnected_nodes(self) -> list[str]:
        """Return list of nodes that CANNOT reach GCS."""
        reachable = self.get_all_reachable_from_gcs()
        all_nodes = set(self._adj.keys())
        return [n for n in sorted(all_nodes - reachable) if n != GCS_NODE_ID]

    # ── Link Mutation ─────────────────────────────────────

    def fail_link(self, a: str, b: str) -> bool:
        """
        Mark a link as failed (remove from adjacency, mark inactive in _all_links).
        Returns True if the link existed and was removed.
        """
        removed = False
        if b in self._adj.get(a, {}):
            del self._adj[a][b]
            removed = True
        if a in self._adj.get(b, {}):
            del self._adj[b][a]
            removed = True

        for link in self._all_links:
            if (link["from"] == a and link["to"] == b) or \
               (link["from"] == b and link["to"] == a):
                link["active"] = False
                link["quality"] = LINK_QUALITY_DEAD

        if removed:
            logger.info("Link failed: %s <-> %s", a, b)
        return removed

    def restore_link(self, a: str, b: str, quality: float) -> None:
        """Restore or create a link between two nodes."""
        self._adj.setdefault(a, {})[b] = quality
        self._adj.setdefault(b, {})[a] = quality

        found = False
        for link in self._all_links:
            if (link["from"] == a and link["to"] == b) or \
               (link["from"] == b and link["to"] == a):
                link["active"] = True
                link["quality"] = quality
                found = True
                break
        if not found:
            self._all_links.append({
                "from": a, "to": b,
                "quality": quality, "active": True,
            })
        logger.info("Link restored: %s <-> %s (q=%.2f)", a, b, quality)

    def remove_node(self, node_id: str) -> list[str]:
        """
        Remove a node and all its edges (e.g. UAV failure).
        Returns list of neighbors that lost a link.
        """
        affected = list(self._adj.get(node_id, {}).keys())
        if node_id in self._adj:
            del self._adj[node_id]
        for neighbor in affected:
            self._adj.get(neighbor, {}).pop(node_id, None)

        for link in self._all_links:
            if link["from"] == node_id or link["to"] == node_id:
                link["active"] = False
                link["quality"] = LINK_QUALITY_DEAD

        logger.info("Node removed: %s  (affected neighbors: %s)", node_id, affected)
        return affected

    def add_relay_links(self, relay_id: str, neighbors: list[str],
                        quality: float = 0.7) -> None:
        """
        When a UAV is repositioned as relay, create links to its new neighbors.
        Meant to be called after the relay physically moves into position.
        """
        for n in neighbors:
            self.restore_link(relay_id, n, quality)
        logger.info("Relay %s linked to %s", relay_id, neighbors)

    # ── Degraded-link detection ───────────────────────────

    def get_degraded_links(self) -> list[dict]:
        """Return links whose quality is below LINK_QUALITY_MIN but still active."""
        degraded = []
        seen = set()
        for link in self._all_links:
            if not link.get("active", True):
                continue
            key = tuple(sorted([link["from"], link["to"]]))
            if key in seen:
                continue
            seen.add(key)
            if link["quality"] < LINK_QUALITY_MIN:
                degraded.append(link)
        return degraded

    # ── Internals (BFS) ───────────────────────────────────

    def _bfs_reachable(self, start: str, target: str) -> bool:
        visited = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in self._adj.get(node, {}):
                if neighbor == target:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def _bfs_path(self, start: str, target: str) -> list[str] | None:
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            node, path = queue.popleft()
            for neighbor in self._adj.get(node, {}):
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def _bfs_all_reachable(self, start: str) -> set[str]:
        visited = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in self._adj.get(node, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    # ── Snapshot ──────────────────────────────────────────

    def snapshot(self) -> dict:
        """Return serializable snapshot of current graph state."""
        return {
            "nodes": self.get_all_nodes(),
            "active_links": [
                l for l in self._all_links if l.get("active", True)
            ],
            "disconnected": self.get_disconnected_nodes(),
        }

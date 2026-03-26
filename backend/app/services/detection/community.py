"""Community detection and epoch comparison for identifying structural changes."""

import logging
from dataclasses import dataclass

import networkx as nx

logger = logging.getLogger(__name__)


class CommunityChangeType:
    """Types of structural changes between community epochs."""

    NEW_CLUSTER = "NEW_CLUSTER"
    MERGING = "MERGING"
    SPLITTING = "SPLITTING"
    GROWING_FAST = "GROWING_FAST"
    STABLE = "STABLE"
    SHRINKING = "SHRINKING"


@dataclass
class CommunityChange:
    """Describes a change detected between two community epochs."""

    change_type: str
    community_id: int
    members: list[str]
    previous_members: list[str]
    growth_rate: float
    description: str


class CommunityDetector:
    """Detector for community structure and structural changes over time.

    Uses networkx for community detection (greedy modularity / Louvain)
    and compares community structures across epochs to identify
    emerging, merging, splitting, and fast-growing clusters.
    """

    def __init__(self, resolution: float = 1.0) -> None:
        self.resolution = resolution

    def detect_communities(self, graph_data: dict) -> list[dict]:
        """Detect communities from graph data using modularity-based algorithms.

        Args:
            graph_data: Dict with 'nodes' list and 'edges' list.
                Each node has at least an 'id' key.
                Each edge has 'source', 'target', and optional 'weight' keys.

        Returns:
            List of dicts, each with 'community_id' and 'members' (list of node IDs).
        """
        G = self._build_graph(graph_data)

        if G.number_of_nodes() == 0:
            logger.info("Empty graph, no communities to detect")
            return []

        try:
            # Try Louvain first (available in networkx >= 3.0)
            communities_gen = nx.community.louvain_communities(
                G, resolution=self.resolution, seed=42
            )
            community_sets = list(communities_gen)
        except AttributeError:
            # Fall back to greedy modularity communities
            logger.info("Louvain not available, using greedy modularity")
            communities_gen = nx.community.greedy_modularity_communities(
                G, resolution=self.resolution
            )
            community_sets = list(communities_gen)
        except Exception as exc:
            logger.error("Community detection failed: %s", exc)
            # Ultimate fallback: connected components
            community_sets = list(nx.connected_components(G))

        result = []
        for idx, members in enumerate(community_sets):
            result.append({
                "community_id": idx,
                "members": sorted(list(members)),
            })

        logger.info(
            "Detected %d communities from graph with %d nodes and %d edges",
            len(result), G.number_of_nodes(), G.number_of_edges(),
        )
        return result

    def compare_epochs(
        self,
        communities_t: list[dict],
        communities_t_minus_1: list[dict],
    ) -> list[CommunityChange]:
        """Compare two community snapshots to detect structural changes.

        Args:
            communities_t: Current epoch communities (list of dicts with community_id, members).
            communities_t_minus_1: Previous epoch communities.

        Returns:
            List of CommunityChange objects describing detected changes.
        """
        changes: list[CommunityChange] = []

        # Build membership maps: member -> community_id
        prev_member_map: dict[str, int] = {}
        prev_communities: dict[int, set[str]] = {}
        for comm in communities_t_minus_1:
            cid = comm["community_id"]
            members = set(comm["members"])
            prev_communities[cid] = members
            for member in members:
                prev_member_map[member] = cid

        curr_communities: dict[int, set[str]] = {}
        for comm in communities_t:
            cid = comm["community_id"]
            curr_communities[cid] = set(comm["members"])

        # Detect changes for each current community
        for cid, current_members in curr_communities.items():
            # Find which previous communities this overlaps with
            overlapping_prev: dict[int, int] = {}
            new_members: set[str] = set()

            for member in current_members:
                if member in prev_member_map:
                    prev_cid = prev_member_map[member]
                    overlapping_prev[prev_cid] = overlapping_prev.get(prev_cid, 0) + 1
                else:
                    new_members.add(member)

            if not overlapping_prev:
                # No overlap with any previous community: NEW_CLUSTER
                changes.append(CommunityChange(
                    change_type=CommunityChangeType.NEW_CLUSTER,
                    community_id=cid,
                    members=sorted(current_members),
                    previous_members=[],
                    growth_rate=1.0,
                    description=f"New cluster with {len(current_members)} members: "
                                f"{', '.join(sorted(current_members)[:5])}",
                ))
                continue

            # Find the best matching previous community
            best_prev_cid = max(overlapping_prev, key=overlapping_prev.get)
            best_prev_members = prev_communities.get(best_prev_cid, set())

            # Check for merging: current community has significant overlap with multiple prev communities
            significant_overlaps = [
                pcid for pcid, count in overlapping_prev.items()
                if count >= max(2, len(prev_communities.get(pcid, set())) * 0.3)
            ]

            if len(significant_overlaps) >= 2:
                changes.append(CommunityChange(
                    change_type=CommunityChangeType.MERGING,
                    community_id=cid,
                    members=sorted(current_members),
                    previous_members=sorted(best_prev_members),
                    growth_rate=len(current_members) / max(len(best_prev_members), 1),
                    description=f"Community {cid} formed by merging {len(significant_overlaps)} "
                                f"previous communities",
                ))
                continue

            # Compute growth rate
            prev_size = len(best_prev_members) if best_prev_members else 1
            curr_size = len(current_members)
            growth_rate = curr_size / prev_size

            if growth_rate >= 1.5:
                changes.append(CommunityChange(
                    change_type=CommunityChangeType.GROWING_FAST,
                    community_id=cid,
                    members=sorted(current_members),
                    previous_members=sorted(best_prev_members),
                    growth_rate=round(growth_rate, 3),
                    description=f"Community {cid} grew by {(growth_rate - 1) * 100:.0f}% "
                                f"({prev_size} -> {curr_size} members)",
                ))
            elif growth_rate <= 0.7:
                changes.append(CommunityChange(
                    change_type=CommunityChangeType.SHRINKING,
                    community_id=cid,
                    members=sorted(current_members),
                    previous_members=sorted(best_prev_members),
                    growth_rate=round(growth_rate, 3),
                    description=f"Community {cid} shrank by {(1 - growth_rate) * 100:.0f}%",
                ))
            else:
                changes.append(CommunityChange(
                    change_type=CommunityChangeType.STABLE,
                    community_id=cid,
                    members=sorted(current_members),
                    previous_members=sorted(best_prev_members),
                    growth_rate=round(growth_rate, 3),
                    description=f"Community {cid} is stable ({prev_size} -> {curr_size} members)",
                ))

        # Detect splitting: check if any previous community maps to multiple current communities
        prev_to_curr: dict[int, list[int]] = {}
        for cid, current_members in curr_communities.items():
            for member in current_members:
                if member in prev_member_map:
                    prev_cid = prev_member_map[member]
                    if prev_cid not in prev_to_curr:
                        prev_to_curr[prev_cid] = []
                    if cid not in prev_to_curr[prev_cid]:
                        prev_to_curr[prev_cid].append(cid)

        for prev_cid, curr_cids in prev_to_curr.items():
            if len(curr_cids) >= 2:
                prev_members = prev_communities.get(prev_cid, set())
                # Check for significant splits (not just a few members drifting)
                split_sizes = [len(curr_communities.get(cc, set())) for cc in curr_cids]
                if min(split_sizes) >= max(2, len(prev_members) * 0.2):
                    changes.append(CommunityChange(
                        change_type=CommunityChangeType.SPLITTING,
                        community_id=prev_cid,
                        members=sorted(prev_members),
                        previous_members=sorted(prev_members),
                        growth_rate=len(curr_cids),
                        description=f"Previous community {prev_cid} split into "
                                    f"{len(curr_cids)} communities",
                    ))

        logger.info("Detected %d community changes between epochs", len(changes))
        return changes

    def find_emerging_clusters(self, changes: list[CommunityChange]) -> list[dict]:
        """Identify emerging topic clusters from community changes.

        Emerging clusters are NEW_CLUSTER or GROWING_FAST communities
        that indicate new or rapidly growing research areas.

        Args:
            changes: List of CommunityChange from epoch comparison.

        Returns:
            List of dicts describing emerging topics.
        """
        emerging: list[dict] = []

        for change in changes:
            if change.change_type in (
                CommunityChangeType.NEW_CLUSTER,
                CommunityChangeType.GROWING_FAST,
            ):
                emerging.append({
                    "change_type": change.change_type,
                    "community_id": change.community_id,
                    "members": change.members,
                    "growth_rate": change.growth_rate,
                    "description": change.description,
                    "member_count": len(change.members),
                    "is_new": change.change_type == CommunityChangeType.NEW_CLUSTER,
                })

        # Sort by growth rate (new clusters have rate 1.0, so growing_fast comes first)
        emerging.sort(key=lambda e: e["growth_rate"], reverse=True)

        logger.info("Found %d emerging clusters", len(emerging))
        return emerging

    @staticmethod
    def _build_graph(graph_data: dict) -> nx.Graph:
        """Build a networkx Graph from node/edge data.

        Args:
            graph_data: Dict with 'nodes' and 'edges' lists.

        Returns:
            An undirected networkx Graph.
        """
        G = nx.Graph()

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        for node in nodes:
            node_id = node.get("id")
            if node_id:
                G.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                weight = edge.get("weight", 1.0)
                G.add_edge(source, target, weight=weight or 1.0)

        return G

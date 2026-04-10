import networkx as nx

def add_node(G: nx.DiGraph, name: str, **attributes):
    """Add a node to the graph, merging if it already exists."""
    if name in G.nodes:
        # Node exists — increment citation count
        G.nodes[name]["citations"] = G.nodes[name].get("citations", 1) + 1
    else:
        G.add_node(name, citations=1, **attributes)

def add_edge(G: nx.DiGraph, from_node: str, to_node: str, **attributes):
    """Add a directed edge between two nodes."""
    if from_node in G.nodes and to_node in G.nodes:
        G.add_edge(from_node, to_node, **attributes)

def get_most_influential(G: nx.DiGraph, top_n: int = 10) -> list[dict]:
    """Return top N nodes by influence score (PageRank)."""
    nodes = []
    for name, data in G.nodes(data=True):
        nodes.append({
            "name": name,
            "type": data.get("type", "unknown"),
            "influence_score": data.get("influence_score", 0.0),
            "citations": data.get("citations", 1),
            "source": data.get("source", ""),
        })
    
    return sorted(nodes, key=lambda x: x["influence_score"], reverse=True)[:top_n]

def get_nodes_by_type(G: nx.DiGraph, node_type: str) -> list[dict]:
    """Return all nodes of a specific type."""
    return [
        {"name": n, **data}
        for n, data in G.nodes(data=True)
        if data.get("type") == node_type
    ]

def get_neighbors(G: nx.DiGraph, node_name: str) -> list[dict]:
    """Return all neighboring nodes of a given node."""
    if node_name not in G.nodes:
        return []
    return [
        {"name": n, **G.nodes[n]}
        for n in G.neighbors(node_name)
    ]

def query_graph(G: nx.DiGraph, keywords: list[str], top_n: int = 5) -> list[dict]:
    """
    Find the most relevant nodes for a given set of keywords.
    Used by agents to pull evidence during debate.
    """
    results = []
    keywords_lower = [k.lower() for k in keywords]
    
    for name, data in G.nodes(data=True):
        name_lower = name.lower()
        description_lower = data.get("description", "").lower()
        
        score = 0
        for keyword in keywords_lower:
            if keyword in name_lower:
                score += 2
            if keyword in description_lower:
                score += 1
        
        if score > 0:
            results.append({
                "name": name,
                "score": score * data.get("influence_score", 0.01),
                "description": data.get("description", ""),
                "source": data.get("source", ""),
                "citations": data.get("citations", 1),
                "type": data.get("type", "unknown")
            })
    
    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
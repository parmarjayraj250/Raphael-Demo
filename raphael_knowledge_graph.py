import os, sqlite3, re
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_graph.db")

class RaphaelKnowledgeGraph:
    """
    Second-Brain Knowledge Graph:
    - SQLite persistence + NetworkX in-memory graph
    - Entity deduplication & confidence filtering
    - Node / Edge traversal and search
    """
    def __init__(self, safety_manager):
        self.safety_manager = safety_manager
        self.graph = nx.DiGraph() if NETWORKX_AVAILABLE else None
        self._init_db()
        self._load_graph_from_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                entity_type TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                source TEXT,
                relation TEXT,
                target TEXT,
                confidence REAL,
                PRIMARY KEY (source, relation, target),
                FOREIGN KEY (source) REFERENCES entities(name),
                FOREIGN KEY (target) REFERENCES entities(name)
            )
        ''')
        conn.commit()
        conn.close()

    def _load_graph_from_db(self):
        if self.graph is None:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, entity_type FROM entities")
        for name, etype in cur.fetchall():
            self.graph.add_node(name, type=etype)

        cur.execute("SELECT source, relation, target FROM relationships")
        for src, rel, tgt in cur.fetchall():
            self.graph.add_edge(src, tgt, relation=rel)
        conn.close()

    def add_relation(self, source: str, relation: str, target: str, confidence: float = 0.85) -> bool:
        """
        Inserts verified relationship into graph only if confidence >= 0.75.
        Filters out passwords, keys, and transient chat noise.
        """
        if confidence < 0.75:
            return False

        src = source.strip().lower()
        tgt = target.strip().lower()
        rel = relation.strip().upper()

        # Privacy Filter: Never store credentials or keys in graph
        # Uses substring check (not word-boundary only) to catch compound identifiers
        # like "api_key", "my_secret", "oauth_token", etc.
        _SENSITIVE = ("password", "token", "secret", "key", "bearer", "credit")
        for word in [src, tgt]:
            if any(kw in word for kw in _SENSITIVE):
                return False

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO entities (name, entity_type, confidence) VALUES (?, ?, ?)", (src, "concept", confidence))
        cur.execute("INSERT OR REPLACE INTO entities (name, entity_type, confidence) VALUES (?, ?, ?)", (tgt, "concept", confidence))
        cur.execute("INSERT OR REPLACE INTO relationships (source, relation, target, confidence) VALUES (?, ?, ?, ?)", (src, rel, tgt, confidence))
        conn.commit()
        conn.close()

        if self.graph is not None:
            self.graph.add_node(src, type="concept")
            self.graph.add_node(tgt, type="concept")
            self.graph.add_edge(src, tgt, relation=rel)

        return True

    def search(self, query: str) -> str:
        q = query.strip().lower()
        if self.graph is None:
            return "Knowledge graph library (networkx) is unavailable."

        results = []
        for node in self.graph.nodes:
            if q in node:
                # Outgoing
                for neighbor in self.graph.successors(node):
                    rel = self.graph[node][neighbor].get("relation", "RELATED_TO")
                    results.append(f"  ● {node.title()} --[{rel}]--> {neighbor.title()}")
                # Incoming
                for pred in self.graph.predecessors(node):
                    rel = self.graph[pred][node].get("relation", "RELATED_TO")
                    results.append(f"  ● {pred.title()} --[{rel}]--> {node.title()}")

        if not results:
            return f"No direct graph connections found for '{query}'."
        return f"🕸️ Knowledge Graph Connections for '{query}':\n" + "\n".join(list(set(results))[:15])

    def delete_node(self, node_name: str) -> str:
        name = node_name.strip().lower()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM relationships WHERE source = ? OR target = ?", (name, name))
        cur.execute("DELETE FROM entities WHERE name = ?", (name,))
        conn.commit()
        conn.close()

        if self.graph is not None and name in self.graph:
            self.graph.remove_node(name)
        return f"Node '{name}' and associated connections deleted from knowledge graph."

    def get_stats(self) -> str:
        nodes_cnt = self.graph.number_of_nodes() if self.graph is not None else 0
        edges_cnt = self.graph.number_of_edges() if self.graph is not None else 0
        return f"Knowledge Graph Stats: {nodes_cnt} Entities | {edges_cnt} Relationships"
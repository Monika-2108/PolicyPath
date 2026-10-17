import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

db = FalkorDB(
    host=os.getenv("FALKORDB_HOST"),
    port=int(os.getenv("FALKORDB_PORT")),
    username=os.getenv("FALKORDB_USERNAME"),
    password=os.getenv("FALKORDB_PASSWORD"),
    ssl=False,
    socket_connect_timeout=5,
    socket_timeout=10,
)

graph = db.select_graph(os.getenv("FALKORDB_GRAPH"))

# Create sample company policies and their relationships.
queries = [
    """
    MERGE (p:Policy {id: 'POL-001'})
    SET p.title = 'Customer Data Retention Policy',
        p.description = 'Customer support call recordings must be deleted after 90 days.',
        p.category = 'Data Privacy',
        p.status = 'Active'
    """,
    """
    MERGE (c:Control {id: 'CTRL-001'})
    SET c.title = 'Recording Deletion Control',
        c.description = 'Delete recordings after the approved retention period.'
    """,
    """
    MERGE (r:Risk {id: 'RISK-001'})
    SET r.title = 'Customer Privacy Exposure',
        r.severity = 'High',
        r.description = 'Keeping recordings longer may increase privacy and compliance risk.'
    """,
    """
    MERGE (o:Owner {id: 'OWNER-001'})
    SET o.name = 'Data Protection Officer',
        o.role = 'Policy Approver'
    """,
    """
    MATCH (p:Policy {id: 'POL-001'})
    MATCH (c:Control {id: 'CTRL-001'})
    MERGE (p)-[:ENFORCED_BY]->(c)
    """,
    """
    MATCH (p:Policy {id: 'POL-001'})
    MATCH (r:Risk {id: 'RISK-001'})
    MERGE (p)-[:MITIGATES_OR_RELATES_TO]->(r)
    """,
    """
    MATCH (p:Policy {id: 'POL-001'})
    MATCH (o:Owner {id: 'OWNER-001'})
    MERGE (p)-[:APPROVED_BY]->(o)
    """,
]

for i, query in enumerate(queries, start=1):
    graph.query(query)
    print(f"Added graph item {i}/{len(queries)}", flush=True)

print("\nSUCCESS: Sample PolicyPath graph created!", flush=True)
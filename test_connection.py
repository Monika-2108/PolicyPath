import os
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

print("Starting PolicyPath connection test...", flush=True)

try:
    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST"),
        port=int(os.getenv("FALKORDB_PORT")),
        username=os.getenv("FALKORDB_USERNAME"),
        password=os.getenv("FALKORDB_PASSWORD"),
        ssl=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    print("Connecting to FalkorDB...", flush=True)

    graph = db.select_graph(os.getenv("FALKORDB_GRAPH"))
    result = graph.query(
        'RETURN "PolicyPath connected!" AS message'
    )

    print("Query result:", result.result_set, flush=True)
    print("SUCCESS: PolicyPath is connected!", flush=True)

except Exception as error:
    print("CONNECTION FAILED:", type(error).__name__, str(error), flush=True)
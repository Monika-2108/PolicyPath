
# PolicyPath 🧭
### AI-Powered Policy Intelligence Using FalkorDB

PolicyPath is a graph-powered policy intelligence system that connects company policies, controls, risks, and owners to help teams understand policy-related decisions.

## Problem

Company policies are often scattered across documents. Understanding related controls, risks, and approval owners can take time.

## Solution

PolicyPath uses a knowledge graph stored in FalkorDB to connect policies with their controls, risks, and approvers. Users can explore these connections and obtain policy-related answers through a Streamlit dashboard.

## Features

- Policy search and filtering
- Graph explorer
- Risk heatmap
- Decision briefs with JSON download
- Policy question assistant
- Connected policy, control, risk, and owner information

## Technology Stack

- Python
- Streamlit
- FalkorDB
- Cypher
- Plotly
- Pandas

## Graph Data Model

### Nodes

- `Policy`
- `Control`
- `Risk`
- `Owner`

### Relationships

- `ENFORCED_BY`: Policy → Control
- `MITIGATES_OR_RELATES_TO`: Policy → Risk
- `APPROVED_BY`: Policy → Owner

### Example Graph

```text
(Policy)-[:ENFORCED_BY]->(Control)
(Policy)-[:MITIGATES_OR_RELATES_TO]->(Risk)
(Policy)-[:APPROVED_BY]->(Owner)
```

## Example Cypher Queries

### 1. Find all policies

```cypher
MATCH (p:Policy)
RETURN p
```

### 2. Find a policy and its related controls, risks, and owners

```cypher
MATCH (p:Policy)
OPTIONAL MATCH (p)-[:ENFORCED_BY]->(c:Control)
OPTIONAL MATCH (p)-[:MITIGATES_OR_RELATES_TO]->(r:Risk)
OPTIONAL MATCH (p)-[:APPROVED_BY]->(o:Owner)
RETURN p, c, r, o
```

### 3. Find policies associated with high-severity risks

```cypher
MATCH (p:Policy)-[:MITIGATES_OR_RELATES_TO]->(r:Risk)
WHERE r.severity = 'High'
RETURN p, r
```

These are example queries for the documented graph model. Confirm that the property names and query syntax match your actual seeded data before relying on them.

## Example Use Case

A company wants to understand its customer support call-recording retention policy. PolicyPath connects the 90-day retention rule with its deletion control, customer privacy risk, and approval owner.

## Setup

### Prerequisites

- Python 3.12 recommended
- A FalkorDB database and connection credentials
- Git

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Monika-2108/PolicyPath.git
cd PolicyPath
```

2. Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

4. Configure your FalkorDB connection using the environment variables expected by the application. Keep credentials in a local `.env` file and never commit secrets to GitHub.

5. Start the application:

```bash
python -m streamlit run app.py
```

6. Open the local URL shown in the terminal.

## Security

- Do not commit database passwords, API keys, or `.env` files.
- Use environment variables for database credentials.
- Review policy decisions with the appropriate human owner before acting on them.

## Limitations

PolicyPath is a prototype. Its answers depend on the graph data available and the application's current query and response logic. Human review is recommended for policy exceptions and consequential decisions.

## Repository

[PolicyPath on GitHub](https://github.com/Monika-2108/PolicyPath)

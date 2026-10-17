# PolicyPath 🧭
### AI-Powered Policy Intelligence Using FalkorDB

PolicyPath is a graph-powered policy intelligence system that connects company policies, controls, risks, and owners to help teams understand policy-related decisions.

## Problem
Company policies are often scattered across documents. Understanding related controls, risks, and approval owners can take time.

## Solution
PolicyPath uses a knowledge graph stored in FalkorDB to connect policies with their controls, risks, and approvers.

## Features
- Policy search and filtering
- Interactive graph explorer
- Risk heatmap
- Decision brief with JSON download
- Policy question assistant
- Connected policy, control, risk, and owner information

## Technology Stack
- Python
- Streamlit
- FalkorDB
- Cypher graph queries
- Plotly
- Pandas

## Graph Model
Nodes:
- Policy
- Control
- Risk
- Owner

Relationships:
- `ENFORCED_BY`
- `MITIGATES_OR_RELATES_TO`
- `APPROVED_BY`

## Example Use Case
A company wants to understand its customer support call-recording retention policy. PolicyPath helps connect the 90-day retention rule with its deletion control, privacy risk, and approval owner.

## Setup

1. Clone this repository.
2. Create a Python virtual environment.
3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
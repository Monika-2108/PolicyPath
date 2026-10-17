
import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="PolicyPath | Policy Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# DESIGN: READABLE INPUTS + MODERN DASHBOARD
# --------------------------------------------------

st.markdown(
    """
    <style>
    :root {
        --pp-bg: #f4f7fc;
        --pp-card: #ffffff;
        --pp-text: #172033;
        --pp-muted: #58657a;
        --pp-border: #dce3ef;
        --pp-input-bg: #ffffff;
        --pp-input-text: #172033;
    }

    .stApp {
        background: var(--pp-bg);
        color: var(--pp-text);
    }

    [data-testid="stSidebar"] {
        background: #10172a;
    }

    [data-testid="stSidebar"] * {
        color: #f1f5ff;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [contenteditable="true"] {
        background-color: #ffffff !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        caret-color: #172033 !important;
    }

    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stChatInput"] textarea {
        background-color: #ffffff !important;
        color: #172033 !important;
        -webkit-text-fill-color: #172033 !important;
        caret-color: #172033 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
    }

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder,
    [data-testid="stChatInput"] textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }

    [data-testid="stSelectbox"] div,
    [data-testid="stMultiSelect"] div {
        color: #172033;
    }

    .pp-hero {
        padding: 30px;
        border-radius: 22px;
        color: white;
        background: linear-gradient(120deg, #172554, #4338ca, #9333ea);
        margin-bottom: 22px;
        box-shadow: 0 12px 35px rgba(67, 56, 202, 0.18);
    }

    .pp-hero h1 {
        color: white;
        font-size: 36px;
        margin-bottom: 8px;
    }

    .pp-hero p {
        color: #e5e7ff;
        font-size: 16px;
        margin-bottom: 0;
    }

    .pp-card {
        background: white;
        border: 1px solid #e1e7f0;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.045);
    }

    .pp-card h3 {
        color: #172033;
        margin-top: 0;
    }

    .pp-muted {
        color: #58657a;
        font-size: 14px;
    }

    .pp-tag {
        display: inline-block;
        background: #ede9fe;
        color: #5b21b6;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin: 3px 4px 3px 0;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 40px;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e1e7f0;
        border-radius: 14px;
        padding: 16px;
    }

    hr {
        border-color: #dce3ef;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# FALKORDB CONNECTION
# --------------------------------------------------

@st.cache_resource
def get_graph():
    host = os.getenv("FALKORDB_HOST")
    port = os.getenv("FALKORDB_PORT")
    username = os.getenv("FALKORDB_USERNAME")
    password = os.getenv("FALKORDB_PASSWORD")
    graph_name = os.getenv("FALKORDB_GRAPH", "policypath")

    if not host or not port or not password:
        raise ValueError(
            "Missing FalkorDB settings. Check your local .env file."
        )

    db = FalkorDB(
        host=host,
        port=int(port),
        username=username or "falkordb",
        password=password,
        ssl=False,
        socket_connect_timeout=8,
        socket_timeout=15,
    )

    return db.select_graph(graph_name)


def query_rows(cypher):
    graph = get_graph()
    result = graph.query(cypher)

    headers = []
    for item in result.header:
        if isinstance(item, (list, tuple)):
            headers.append(str(item[-1]))
        else:
            headers.append(str(item))

    return [
        dict(zip(headers, row))
        for row in result.result_set
    ]


# --------------------------------------------------
# DATA ACCESS
# --------------------------------------------------

POLICY_QUERY = """
MATCH (p:Policy)
OPTIONAL MATCH (p)-[:ENFORCED_BY]->(c:Control)
OPTIONAL MATCH (p)-[:MITIGATES_OR_RELATES_TO]->(r:Risk)
OPTIONAL MATCH (p)-[:APPROVED_BY]->(o:Owner)
RETURN
    p.id AS id,
    p.title AS title,
    p.description AS description,
    p.category AS category,
    p.status AS status,
    collect(DISTINCT c.title) AS controls,
    collect(DISTINCT r.title) AS risks,
    collect(DISTINCT r.severity) AS severities,
    collect(DISTINCT o.name) AS owners
ORDER BY p.title
"""


def get_policies():
    return query_rows(POLICY_QUERY)


def get_nodes():
    return query_rows("""
        MATCH (n)
        RETURN
            labels(n) AS labels,
            n.id AS id,
            n.title AS title,
            n.name AS name,
            n.description AS description,
            n.severity AS severity,
            n.category AS category,
            n.status AS status
    """)


def get_relationships():
    return query_rows("""
        MATCH (a)-[r]->(b)
        RETURN
            labels(a) AS source_type,
            coalesce(a.title, a.name, a.id) AS source,
            type(r) AS relationship,
            labels(b) AS target_type,
            coalesce(b.title, b.name, b.id) AS target
    """)


def display_value(value):
    if value is None:
        return "Not specified"
    if isinstance(value, list):
        values = [str(x) for x in value if x]
        return ", ".join(values) if values else "Not specified"
    return str(value)


def normalise(value):
    return str(value or "").lower()


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🧭 PolicyPath")
    st.caption("Policy intelligence powered by FalkorDB")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Command Center",
            "Policy Explorer",
            "Graph Explorer",
            "Risk Heatmap",
            "Decision Brief",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("### 💬 Ask PolicyPath")
    st.caption("Ask about policies, controls, risks, or owners.")

    question = st.text_area(
        "Your question",
        placeholder="Example: What is our data retention policy?",
        height=105,
        key="policy_question",
        label_visibility="collapsed",
    )

    ask_button = st.button(
        "Ask question",
        type="primary",
        use_container_width=True,
    )

    if ask_button:
        if question.strip():
            st.session_state["policy_answer"] = question.strip()
        else:
            st.warning("Type a question first.")

    if st.button("Refresh data", use_container_width=True):
        get_graph.clear()
        st.rerun()

    st.divider()
    st.caption("Human review is required for policy decisions.")

# --------------------------------------------------
# CONNECTION AND DATA LOADING
# --------------------------------------------------

try:
    policies = get_policies()
    nodes = get_nodes()
    relationships = get_relationships()
    connection_ok = True

except Exception as exc:
    connection_ok = False
    policies = []
    nodes = []
    relationships = []

    st.markdown(
        """
        <div class="pp-hero">
            <h1>🧭 PolicyPath</h1>
            <p>Graph-powered policy intelligence</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.error("Could not load data from FalkorDB.")
    st.code(str(exc))
    st.info(
        "Check your .env connection settings and confirm that your "
        "FalkorDB instance is running."
    )
    st.stop()

# --------------------------------------------------
# COMMON HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="pp-hero">
        <h1>🧭 PolicyPath</h1>
        <p>
            Understand company policies by connecting rules, controls,
            risks, and approval owners in one knowledge graph.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_status, col_graph, col_policy = st.columns(3)

with col_status:
    st.success("● FalkorDB connected")

with col_graph:
    st.metric("Graph nodes", len(nodes))

with col_policy:
    st.metric("Relationships", len(relationships))

# --------------------------------------------------
# ANSWER QUESTIONS USING REAL GRAPH DATA
# --------------------------------------------------

def answer_question(user_question):
    q = normalise(user_question)
    results = []

    # Search policy details
    for policy in policies:
        searchable = " ".join([
            normalise(policy.get("id")),
            normalise(policy.get("title")),
            normalise(policy.get("description")),
            normalise(policy.get("category")),
            normalise(policy.get("status")),
            normalise(policy.get("controls")),
            normalise(policy.get("risks")),
            normalise(policy.get("owners")),
        ])

        keywords = [
            word.strip(".,?!:;()")
            for word in q.split()
            if len(word.strip(".,?!:;()")) > 3
        ]

        matches = sum(1 for word in keywords if word in searchable)

        if matches:
            results.append((matches, policy))

    results.sort(key=lambda item: item[0], reverse=True)

    # General questions should still return useful graph context.
    if not results:
        return (
            "I couldn't find a direct match for that question in the "
            "current graph. Try asking about customer data retention, "
            "recordings, deletion controls, privacy risks, or the policy "
            "approver.\n\n"
            f"Current graph: {len(policies)} policies, "
            f"{len(nodes)} nodes, and {len(relationships)} relationships."
        )

    best_score = results[0][0]
    matched_policies = [
        policy for score, policy in results
        if score >= max(1, best_score - 1)
    ][:3]

    answer_parts = []

    for policy in matched_policies:
        answer_parts.append(
            f"### {display_value(policy.get('title'))}\n"
            f"**Policy ID:** {display_value(policy.get('id'))}\n\n"
            f"**Rule / description:** "
            f"{display_value(policy.get('description'))}\n\n"
            f"**Category:** {display_value(policy.get('category'))}\n\n"
            f"**Status:** {display_value(policy.get('status'))}\n\n"
            f"**Controls:** {display_value(policy.get('controls'))}\n\n"
            f"**Related risks:** {display_value(policy.get('risks'))}\n\n"
            f"**Risk severity:** "
            f"{display_value(policy.get('severities'))}\n\n"
            f"**Approval owner(s):** "
            f"{display_value(policy.get('owners'))}"
        )

    answer_parts.append(
        "**Important:** This answer is based on the current graph data. "
        "The graph does not automatically establish whether a proposed "
        "exception is legally permitted. Ask the responsible policy owner "
        "to review exceptions."
    )

    return "\n\n---\n\n".join(answer_parts)


if "policy_answer" in st.session_state:
    st.markdown("## 💬 Ask PolicyPath")
    st.markdown(
        f"**Question:** {st.session_state['policy_answer']}"
    )

    with st.container(border=True):
        st.markdown(
            answer_question(st.session_state["policy_answer"])
        )

    if st.button("Clear answer"):
        del st.session_state["policy_answer"]
        st.rerun()

    st.divider()

# --------------------------------------------------
# COMMAND CENTER
# --------------------------------------------------

if page == "Command Center":
    st.subheader("Command Center")
    st.caption("A live overview of the policy knowledge graph.")

    total_policies = len(policies)
    total_nodes = len(nodes)
    total_relationships = len(relationships)

    high_risks = sum(
        1 for node in nodes
        if normalise(node.get("severity")) == "high"
    )

    metrics = st.columns(4)
    metrics[0].metric("Policies", total_policies)
    metrics[1].metric("Graph nodes", total_nodes)
    metrics[2].metric("Connections", total_relationships)
    metrics[3].metric("High-severity risks", high_risks)

    st.markdown("### Policy overview")

    if policies:
        df = pd.DataFrame(policies)

        left, right = st.columns(2)

        with left:
            if "category" in df.columns:
                category_df = (
                    df["category"]
                    .fillna("Uncategorised")
                    .replace("", "Uncategorised")
                    .value_counts()
                    .reset_index()
                )
                category_df.columns = ["Category", "Policies"]

                fig = px.pie(
                    category_df,
                    names="Category",
                    values="Policies",
                    hole=0.55,
                    title="Policies by category",
                )
                st.plotly_chart(fig, use_container_width=True)

        with right:
            status_df = (
                df["status"]
                .fillna("Unknown")
                .replace("", "Unknown")
                .value_counts()
                .reset_index()
            )
            status_df.columns = ["Status", "Count"]

            fig = px.bar(
                status_df,
                x="Status",
                y="Count",
                color="Status",
                title="Policy status",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Policies to review")

        for policy in policies[:5]:
            with st.container(border=True):
                st.markdown(
                    f"**{display_value(policy.get('title'))}**"
                )
                st.caption(
                    f"{display_value(policy.get('category'))} · "
                    f"{display_value(policy.get('status'))}"
                )
                st.write(
                    display_value(policy.get("description"))
                )
    else:
        st.info(
            "No policies found. Run seed_graph.py to insert the "
            "example graph data."
        )

# --------------------------------------------------
# POLICY EXPLORER
# --------------------------------------------------

elif page == "Policy Explorer":
    st.subheader("🔎 Policy Explorer")
    st.write("Search and filter policies stored in FalkorDB.")

    search_text = st.text_input(
        "Search policies",
        placeholder="Search title, description, category, or owner...",
    )

    categories = sorted({
        str(p.get("category"))
        for p in policies
        if p.get("category")
    })

    selected_category = st.selectbox(
        "Category",
        ["All categories"] + categories,
    )

    filtered = []

    for policy in policies:
        text_to_search = " ".join([
            normalise(policy.get("id")),
            normalise(policy.get("title")),
            normalise(policy.get("description")),
            normalise(policy.get("category")),
            normalise(policy.get("owners")),
            normalise(policy.get("controls")),
            normalise(policy.get("risks")),
        ])

        matches_search = (
            not search_text.strip()
            or search_text.lower() in text_to_search
        )

        matches_category = (
            selected_category == "All categories"
            or policy.get("category") == selected_category
        )

        if matches_search and matches_category:
            filtered.append(policy)

    st.caption(f"{len(filtered)} matching policies")

    if filtered:
        for policy in filtered:
            with st.container(border=True):
                st.markdown(f"### {display_value(policy.get('title'))}")
                st.caption(
                    f"ID: {display_value(policy.get('id'))} · "
                    f"{display_value(policy.get('category'))} · "
                    f"{display_value(policy.get('status'))}"
                )

                st.write(
                    display_value(policy.get("description"))
                )

                a, b = st.columns(2)
                with a:
                    st.markdown("**Controls**")
                    st.write(display_value(policy.get("controls")))

                with b:
                    st.markdown("**Related risks**")
                    st.write(display_value(policy.get("risks")))

                st.markdown("**Approval owners**")
                st.write(display_value(policy.get("owners")))
    else:
        st.info("No matching policies found.")

# --------------------------------------------------
# GRAPH EXPLORER
# --------------------------------------------------

elif page == "Graph Explorer":
    st.subheader("🕸️ Graph Explorer")
    st.write(
        "Explore the nodes and relationships stored in FalkorDB."
    )

    if nodes:
        node_df = pd.DataFrame(nodes)

        if "labels" in node_df.columns:
            node_df["node_type"] = node_df["labels"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )

        st.markdown("### Nodes")
        st.dataframe(node_df, use_container_width=True, hide_index=True)

    if relationships:
        rel_df = pd.DataFrame(relationships)

        st.markdown("### Relationships")
        st.dataframe(rel_df, use_container_width=True, hide_index=True)

        graph_fig = go.Figure()

        positions = {}
        node_names = []

        for rel in relationships:
            for name in [rel.get("source"), rel.get("target")]:
                if name and name not in node_names:
                    node_names.append(name)

        import math

        count = max(len(node_names), 1)

        for i, name in enumerate(node_names):
            angle = 2 * math.pi * i / count
            positions[name] = (math.cos(angle), math.sin(angle))

        edge_x, edge_y = [], []

        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")

            if source in positions and target in positions:
                x0, y0 = positions[source]
                x1, y1 = positions[target]

                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

        graph_fig.add_trace(go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=2, color="#a5b4fc"),
            hoverinfo="none",
            name="Relationships",
        ))

        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")

            if source in positions and target in positions:
                x0, y0 = positions[source]
                x1, y1 = positions[target]
                graph_fig.add_annotation(
                    x=(x0 + x1) / 2,
                    y=(y0 + y1) / 2,
                    text=str(rel.get("relationship", "")),
                    showarrow=False,
                    font=dict(size=10, color="#4338ca"),
                    bgcolor="white",
                )

        graph_fig.add_trace(go.Scatter(
            x=[positions[n][0] for n in node_names],
            y=[positions[n][1] for n in node_names],
            mode="markers+text",
            text=node_names,
            textposition="top center",
            marker=dict(
                size=30,
                color="#6366f1",
                line=dict(width=2, color="#ffffff"),
            ),
            hovertemplate="%{text}<extra></extra>",
            name="Graph nodes",
        ))

        graph_fig.update_layout(
            title="Policy relationship map",
            showlegend=False,
            height=520,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        st.plotly_chart(graph_fig, use_container_width=True)
    else:
        st.info("No relationships found in the graph.")

# --------------------------------------------------
# RISK HEATMAP
# --------------------------------------------------

elif page == "Risk Heatmap":
    st.subheader("🔥 Risk Heatmap")
    st.write("Review risks connected to policies.")

    risk_nodes = [
        node for node in nodes
        if isinstance(node.get("labels"), list)
        and "Risk" in node.get("labels", [])
    ]

    if risk_nodes:
        risk_df = pd.DataFrame(risk_nodes)

        risk_df["severity"] = (
            risk_df["severity"]
            .fillna("Unknown")
            .replace("", "Unknown")
        )

        severity_counts = (
            risk_df["severity"]
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Risk count")
        )

        left, right = st.columns([1, 2])

        with left:
            st.markdown("### Severity summary")
            st.dataframe(
                severity_counts,
                use_container_width=True,
                hide_index=True,
            )

        with right:
            fig = px.bar(
                severity_counts,
                x="Severity",
                y="Risk count",
                color="Severity",
                title="Risks by severity",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Risk details")

        for risk in risk_nodes:
            severity = display_value(risk.get("severity"))

            with st.container(border=True):
                st.markdown(f"**{display_value(risk.get('title'))}**")
                st.caption(f"Severity: {severity}")
                st.write(display_value(risk.get("description")))
    else:
        st.info(
            "No Risk nodes found. Check that your graph contains "
            "nodes labelled Risk."
        )

# --------------------------------------------------
# DECISION BRIEF
# --------------------------------------------------

elif page == "Decision Brief":
    st.subheader("📄 Decision Brief")
    st.write(
        "Create a downloadable snapshot of a policy and its connected "
        "controls, risks, and owners."
    )

    if policies:
        policy_options = {
            display_value(p.get("title")): p for p in policies
        }

        selected_title = st.selectbox(
            "Select a policy",
            list(policy_options.keys()),
        )

        selected_policy = policy_options[selected_title]

        report = {
            "report_title": "PolicyPath Decision Brief",
            "generated_at": datetime.now().astimezone().isoformat(),
            "policy": selected_policy,
            "connected_graph": {
                "nodes": len(nodes),
                "relationships": len(relationships),
            },
            "review_notice": (
                "This report is generated from current graph data. "
                "It is not legal advice or automatic approval."
            ),
        }

        st.markdown("### Report preview")

        st.markdown(f"**Policy:** {selected_title}")
        st.write(
            display_value(selected_policy.get("description"))
        )

        st.markdown("**Controls**")
        st.write(display_value(selected_policy.get("controls")))

        st.markdown("**Related risks**")
        st.write(display_value(selected_policy.get("risks")))

        st.markdown("**Approval owners**")
        st.write(display_value(selected_policy.get("owners")))

        st.warning(
            "A human policy owner must review and approve any exception."
        )

        st.download_button(
            "⬇️ Download decision brief (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name="policypath_decision_brief.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        st.info("No policies available to generate a report.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "PolicyPath · FalkorDB Graph Hacks · Company Brain · "
    "Graph-backed policy intelligence with human review."
)

import os
import json
import math
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

st.set_page_config(
    page_title="PolicyPath",
    page_icon="🧭",
    layout="wide",
)

# -------------------- DESIGN --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: Manrope, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 5% 0%, #eeeaff, transparent 28%),
        radial-gradient(circle at 95% 5%, #dffaff, transparent 25%),
        #f5f7fb;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #171b32, #33295f, #174b58);
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

.block-container {
    padding-top: 1.5rem;
    max-width: 1450px;
}

.hero {
    padding: 32px;
    border-radius: 26px;
    color: white;
    background: linear-gradient(115deg, #191c35, #49337a, #087e8b);
    box-shadow: 0 18px 45px rgba(40, 40, 90, 0.18);
}

.hero h1 {
    color: white;
    font-size: clamp(2rem, 4vw, 3.2rem);
    font-weight: 800;
    line-height: 1.08;
}

.hero p {
    color: #e4e8ff;
    max-width: 750px;
}

.eyebrow {
    color: #7657ff;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 2px;
}

.metric-card {
    background: white;
    border: 1px solid #e5e9f2;
    border-radius: 19px;
    padding: 19px;
    box-shadow: 0 8px 24px rgba(30, 40, 80, 0.06);
    min-height: 125px;
}

.metric-label {
    color: #758097;
    font-size: 0.78rem;
    font-weight: 700;
}

.metric-value {
    color: #202744;
    font-size: 2.1rem;
    font-weight: 800;
}

.metric-foot {
    color: #929bad;
    font-size: 0.75rem;
}

.section-heading {
    font-size: 1.2rem;
    font-weight: 800;
    margin: 20px 0 12px;
}

.stButton > button {
    border: none;
    border-radius: 12px;
    color: white;
    font-weight: 800;
    background: linear-gradient(100deg, #7657ff, #258edb);
}

.stDownloadButton > button {
    border-radius: 12px;
    font-weight: 800;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(46, 204, 143, .5); }
    70% { box-shadow: 0 0 0 8px rgba(46, 204, 143, 0); }
    100% { box-shadow: 0 0 0 0 rgba(46, 204, 143, 0); }
}

.pulse-dot {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #38d49a;
    animation: pulse 1.8s infinite;
    margin-right: 8px;
}

.risk-high {
    color: #a52d2d;
    background: #ffe2df;
    padding: 5px 10px;
    border-radius: 20px;
    font-weight: 800;
}

.risk-medium {
    color: #875500;
    background: #fff0ce;
    padding: 5px 10px;
    border-radius: 20px;
    font-weight: 800;
}

.risk-low {
    color: #126844;
    background: #dcf8e9;
    padding: 5px 10px;
    border-radius: 20px;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)


# -------------------- FALKORDB CONNECTION --------------------

@st.cache_resource
def connect_graph():
    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        username=os.getenv("FALKORDB_USERNAME"),
        password=os.getenv("FALKORDB_PASSWORD"),
        ssl=False,
        socket_connect_timeout=5,
        socket_timeout=10,
    )

    return db.select_graph(
        os.getenv("FALKORDB_GRAPH", "policypath")
    )


def query_rows(graph, cypher):
    result = graph.query(cypher)

    headers = []
    for item in getattr(result, "header", []) or []:
        if isinstance(item, (list, tuple)):
            headers.append(str(item[-1]))
        else:
            headers.append(str(item))

    output = []

    for row in getattr(result, "result_set", []) or []:
        record = {}

        for index, value in enumerate(row):
            key = headers[index] if index < len(headers) else f"column_{index}"
            record[key] = value

        output.append(record)

    return output


def count_nodes(graph, label):
    result = query_rows(
        graph,
        f"MATCH (n:{label}) RETURN count(n) AS total"
    )

    if not result:
        return 0

    return int(result[0].get("total", 0))


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
    c.title AS control,
    r.title AS risk,
    r.severity AS severity,
    o.name AS owner
ORDER BY p.title
"""


# -------------------- SIDEBAR --------------------

st.sidebar.markdown("# 🧭 PolicyPath")
st.sidebar.caption("DECISION INTELLIGENCE")

page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Command Center",
        "Policy Explorer",
        "Graph Explorer",
        "Risk Heatmap",
        "Decision Brief",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("FalkorDB Cloud · policypath")

if st.sidebar.button("Refresh graph data"):
    st.cache_resource.clear()
    st.rerun()


# -------------------- LOAD GRAPH DATA --------------------

try:
    graph = connect_graph()
    policies = query_rows(graph, POLICY_QUERY)

    relationships = query_rows(
        graph,
        """
        MATCH (a)-[r]->(b)
        RETURN labels(a) AS source,
               type(r) AS relationship,
               labels(b) AS target
        """
    )

    connected = True
    connection_error = None

except Exception as error:
    connected = False
    connection_error = str(error)
    policies = []
    relationships = []


df = pd.DataFrame(policies)

required_columns = [
    "id", "title", "description", "category", "status",
    "control", "risk", "severity", "owner"
]

for column in required_columns:
    if column not in df.columns:
        df[column] = ""

if not df.empty:
    df = df.fillna("")


# -------------------- HELPER FUNCTIONS --------------------

def metric_card(label, value, description, symbol):
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="display:flex;justify-content:space-between">
                <span class="metric-label">{label}</span>
                <span>{symbol}</span>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-foot">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_class(severity):
    severity = str(severity).lower()

    if severity in ["high", "critical"]:
        return "risk-high"

    if severity == "medium":
        return "risk-medium"

    return "risk-low"


def create_report(question, matches):
    report = {
        "application": "PolicyPath",
        "generated_at": datetime.now().astimezone().isoformat(),
        "question": question,
        "graph_records": matches,
        "notice": (
            "Decision-support report only. Verify the source policy, "
            "evidence and required human approvals."
        ),
    }

    return json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ).encode("utf-8")


# -------------------- CONNECTION ERROR --------------------

if not connected:
    st.markdown(
        """
        <div class="hero">
            <h1>Connection needs attention</h1>
            <p>PolicyPath could not query your FalkorDB graph.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.error(connection_error)

    st.info(
        "Check your existing .env values. The app uses ssl=False "
        "and the graph name policypath."
    )

    st.stop()


# -------------------- COMMAND CENTER --------------------

if page == "Command Center":

    st.markdown(
        """
        <div class="hero">
            <span class="pulse-dot"></span>
            GRAPH CONNECTED
            <h1>Make policy decisions<br>with the full picture.</h1>
            <p>
                Connect policies, controls, risks and accountable owners.
                Start every exception review with evidence and context.
            </p>
            <span class="hero-tag">FalkorDB · Live graph</span>
            <span class="hero-tag">Risk-aware decisions</span>
            <span class="hero-tag">Human approval</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "POLICIES",
            count_nodes(graph, "Policy"),
            "Rules in the graph",
            "◈",
        )

    with col2:
        metric_card(
            "CONTROLS",
            count_nodes(graph, "Control"),
            "Operational safeguards",
            "⌘",
        )

    with col3:
        metric_card(
            "RISKS",
            count_nodes(graph, "Risk"),
            "Mapped exposure areas",
            "△",
        )

    with col4:
        metric_card(
            "RELATIONSHIPS",
            len(relationships),
            "Graph connections",
            "⤳",
        )

    left, right = st.columns(2)

    with left:
        st.markdown(
            '<div class="section-heading">Policy landscape</div>',
            unsafe_allow_html=True,
        )

        if not df.empty:
            chart_data = df.copy()
            chart_data["category"] = chart_data["category"].replace(
                "", "Uncategorised"
            )

            chart_data = chart_data.groupby(
                "category"
            ).size().reset_index(name="count")

            fig = px.pie(
                chart_data,
                names="category",
                values="count",
                hole=0.65,
                color_discrete_sequence=[
                    "#7657ff",
                    "#17b8c8",
                    "#ff7b72",
                    "#ffc857",
                    "#73c7a8",
                ],
            )

            fig.update_layout(
                height=300,
                margin=dict(l=5, r=5, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No policies are available.")

    with right:
        st.markdown(
            '<div class="section-heading">Risk pulse</div>',
            unsafe_allow_html=True,
        )

        if not df.empty:
            risk_data = df.copy()
            risk_data["severity"] = risk_data["severity"].replace(
                "", "Unrated"
            )

            risk_data = risk_data.groupby(
                "severity"
            ).size().reset_index(name="count")

            fig = px.bar(
                risk_data,
                x="severity",
                y="count",
                color="severity",
                color_discrete_map={
                    "Critical": "#b42332",
                    "High": "#ff7b72",
                    "Medium": "#ffc857",
                    "Low": "#48bd91",
                    "Unrated": "#aeb6c6",
                },
            )

            fig.update_layout(
                height=300,
                showlegend=False,
                margin=dict(l=5, r=5, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No risk data is available.")

    st.markdown(
        '<div class="section-heading">Policy overview</div>',
        unsafe_allow_html=True,
    )

    if not df.empty:
        st.dataframe(
            df[
                [
                    "id", "title", "category",
                    "status", "severity", "owner"
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# -------------------- POLICY EXPLORER --------------------

elif page == "Policy Explorer":

    st.markdown(
        '<div class="eyebrow">DISCOVER · FILTER · INSPECT</div>'
        '<h1>Policy Explorer</h1>',
        unsafe_allow_html=True,
    )

    search_col, category_col, status_col = st.columns([2, 1, 1])

    with search_col:
        search = st.text_input(
            "Search policies",
            placeholder="Search title, risk, owner or description",
        )

    with category_col:
        categories = ["All"] + sorted(
            x for x in df["category"].astype(str).unique() if x
        )

        category = st.selectbox("Category", categories)

    with status_col:
        statuses = ["All"] + sorted(
            x for x in df["status"].astype(str).unique() if x
        )

        status = st.selectbox("Status", statuses)

    filtered = df.copy()

    if search:
        mask = filtered.astype(str).apply(
            lambda column: column.str.contains(
                search, case=False, na=False
            )
        ).any(axis=1)

        filtered = filtered[mask]

    if category != "All":
        filtered = filtered[filtered["category"] == category]

    if status != "All":
        filtered = filtered[filtered["status"] == status]

    st.caption(f"{len(filtered)} matching policy records")

    for _, row in filtered.iterrows():

        with st.container(border=True):

            left, right = st.columns([4, 1])

            with left:
                st.subheader(row["title"] or "Untitled policy")
                st.caption(
                    f"{row['id']} · {row['category']} · {row['status']}"
                )
                st.write(row["description"] or "No description recorded.")

            with right:
                st.markdown(
                    f'<span class="{risk_class(row["severity"])}">'
                    f'{row["severity"] or "Unrated"} risk</span>',
                    unsafe_allow_html=True,
                )
                st.caption("OWNER")
                st.write(row["owner"] or "Not linked")

            control_col, risk_col = st.columns(2)

            control_col.markdown(
                f"**Control**  \n{row['control'] or 'Not linked'}"
            )

            risk_col.markdown(
                f"**Related risk**  \n{row['risk'] or 'Not linked'}"
            )


# -------------------- GRAPH EXPLORER --------------------

elif page == "Graph Explorer":

    st.markdown(
        '<div class="eyebrow">CONNECTED KNOWLEDGE</div>'
        '<h1>Graph Explorer</h1>',
        unsafe_allow_html=True,
    )

    node_type = st.selectbox(
        "Choose node type",
        ["All", "Policy", "Control", "Risk", "Owner"],
    )

    cypher = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]-(m)
    """

    if node_type != "All":
        cypher += f"WHERE '{node_type}' IN labels(n) "

    cypher += """
    RETURN labels(n) AS labels,
           coalesce(n.id, '') AS id,
           coalesce(n.title, n.name, '') AS name,
           type(r) AS relationship,
           labels(m) AS connected_labels,
           coalesce(m.title, m.name, '') AS connected_name
    LIMIT 100
    """

    try:
        graph_rows = query_rows(graph, cypher)

        if not graph_rows:
            st.info("No graph nodes found.")
        else:
            nodes = {}
            edges = []

            for row in graph_rows:
                source = str(row.get("name") or row.get("id") or "Unnamed")
                source_labels = row.get("labels") or ["Node"]

                if isinstance(source_labels, list):
                    source_type = ",".join(source_labels)
                else:
                    source_type = str(source_labels)

                nodes[source] = source_type

                target = str(row.get("connected_name") or "")

                if target:
                    target_labels = row.get("connected_labels") or ["Node"]

                    if isinstance(target_labels, list):
                        target_type = ",".join(target_labels)
                    else:
                        target_type = str(target_labels)

                    nodes[target] = target_type

                    edges.append(
                        (
                            source,
                            target,
                            str(row.get("relationship") or "RELATED_TO"),
                        )
                    )

            names = list(nodes.keys())

            positions = {
                name: (
                    math.cos(2 * math.pi * i / max(1, len(names))),
                    math.sin(2 * math.pi * i / max(1, len(names))),
                )
                for i, name in enumerate(names)
            }

            fig = go.Figure()

            for source, target, relation in edges:
                if source in positions and target in positions:
                    x1, y1 = positions[source]
                    x2, y2 = positions[target]

                    fig.add_trace(
                        go.Scatter(
                            x=[x1, x2, None],
                            y=[y1, y2, None],
                            mode="lines",
                            line=dict(color="#cbd1e2", width=2),
                            text=[relation, relation, relation],
                            hoverinfo="text",
                            showlegend=False,
                        )
                    )

            colors = {
                "Policy": "#7657ff",
                "Control": "#17b8c8",
                "Risk": "#ff7b72",
                "Owner": "#ffc857",
            }

            for kind in dict.fromkeys(nodes.values()):
                subset = [
                    name for name in names if nodes[name] == kind
                ]

                fig.add_trace(
                    go.Scatter(
                        x=[positions[name][0] for name in subset],
                        y=[positions[name][1] for name in subset],
                        mode="markers+text",
                        text=subset,
                        textposition="bottom center",
                        marker=dict(
                            size=28,
                            color=colors.get(kind, "#8d98b4"),
                            line=dict(color="white", width=3),
                        ),
                        name=kind,
                    )
                )

            fig.update_layout(
                height=480,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                margin=dict(l=5, r=5, t=20, b=10),
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Inspect graph query results"):
                st.dataframe(
                    pd.DataFrame(graph_rows),
                    use_container_width=True,
                    hide_index=True,
                )

    except Exception as error:
        st.error(f"Graph explorer error: {error}")


# -------------------- RISK HEATMAP --------------------

elif page == "Risk Heatmap":

    st.markdown(
        '<div class="eyebrow">EXPOSURE MAP</div>'
        '<h1>Risk Heatmap</h1>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No policy records are available.")
    else:
        heat = df.copy()

        heat["category"] = heat["category"].replace(
            "", "Uncategorised"
        )

        heat["severity"] = heat["severity"].replace(
            "", "Unrated"
        )

        pivot = heat.pivot_table(
            index="category",
            columns="severity",
            values="id",
            aggfunc="count",
            fill_value=0,
        )

        severity_order = [
            name for name in
            ["Critical", "High", "Medium", "Low", "Unrated"]
            if name in pivot.columns
        ]

        pivot = pivot.reindex(columns=severity_order)

        fig = px.imshow(
            pivot,
            text_auto=True,
            aspect="auto",
            color_continuous_scale=[
                "#e8f8f1",
                "#ffe0a8",
                "#ff9a8d",
                "#b42332",
            ],
            labels={
                "x": "Severity",
                "y": "Policy category",
                "color": "Policy count",
            },
        )

        fig.update_layout(
            height=max(300, 85 * len(pivot)),
            paper_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            '<div class="section-heading">High-risk policies</div>',
            unsafe_allow_html=True,
        )

        attention = df[
            df["severity"].astype(str).str.lower().isin(
                ["high", "critical"]
            )
        ][["id", "title", "category", "severity", "risk", "owner"]]

        if attention.empty:
            st.success("No High or Critical policies are currently mapped.")
        else:
            st.dataframe(
                attention,
                use_container_width=True,
                hide_index=True,
            )


# -------------------- DECISION BRIEF --------------------

elif page == "Decision Brief":

    st.markdown(
        '<div class="eyebrow">EXCEPTION REVIEW WORKSPACE</div>'
        '<h1>Decision Brief</h1>',
        unsafe_allow_html=True,
    )

    st.write(
        "Build a review brief from real graph records. "
        "This tool does not automatically approve exceptions."
    )

    question = st.text_area(
        "What decision are you considering?",
        value=(
            "Can we retain customer support call recordings "
            "for 18 months instead of the standard 90 days?"
        ),
        height=100,
    )

    if not df.empty:
        options = [
            f"{row['id']} — {row['title']}"
            for _, row in df.iterrows()
        ]

        selection = st.selectbox("Policy to review", options)
        selected_id = selection.split(" — ", 1)[0]

        chosen = df[df["id"].astype(str) == selected_id].iloc[0]

    else:
        chosen = None

    if st.button("Generate decision context", type="primary"):

        if not question.strip():
            st.warning("Enter a question first.")

        else:
            tokens = [
                word.lower().strip(".,?!:;()")
                for word in question.split()
                if len(word) > 3
            ]

            scored = []

            for _, row in df.iterrows():
                text = " ".join(
                    str(row.get(column, ""))
                    for column in [
                        "title", "description", "category",
                        "control", "risk", "owner"
                    ]
                ).lower()

                score = sum(token in text for token in tokens)

                if score:
                    scored.append((score, row))

            scored.sort(key=lambda item: item[0], reverse=True)

            matches = [row for _, row in scored[:5]]

            if chosen is not None and all(
                str(row["id"]) != str(chosen["id"])
                for row in matches
            ):
                matches.insert(0, chosen)

            report_rows = []

            for row in matches:
                report_rows.append({
                    column: str(row.get(column, ""))
                    for column in required_columns
                })

            st.session_state["policy_brief"] = {
                "question": question.strip(),
                "matches": report_rows,
            }

    if st.session_state.get("policy_brief"):

        brief = st.session_state["policy_brief"]
        matches = brief["matches"]

        st.markdown(
            '<div class="section-heading">Related graph records</div>',
            unsafe_allow_html=True,
        )

        if matches:
            for item in matches:

                with st.container(border=True):
                    st.subheader(item["title"])
                    st.caption(
                        f"{item['id']} · {item['category']} · "
                        f"{item['status']}"
                    )

                    st.write(item["description"] or "No description recorded.")

                    a, b, c = st.columns(3)

                    a.markdown(
                        f"**Control**  \n{item['control'] or 'Not linked'}"
                    )

                    b.markdown(
                        f"**Related risk**  \n{item['risk'] or 'Not linked'}"
                    )

                    c.markdown(
                        f"**Owner**  \n{item['owner'] or 'Not linked'}"
                    )

        else:
            st.warning(
                "No records matched. This does not mean the action is allowed."
            )

        st.markdown(
            '<div class="section-heading">Approval workflow</div>',
            unsafe_allow_html=True,
        )

        workflow = [
            ("1. Locate governing policy", "Completed" if matches else "Needs review"),
            ("2. Validate evidence and scope", "Human review required"),
            ("3. Risk owner assessment", "Pending"),
            ("4. Policy owner approval", "Pending"),
            ("5. Record exception and expiry", "Pending"),
        ]

        for title, status_text in workflow:
            st.markdown(f"**● {title}**")
            st.caption(status_text)

        st.warning(
            "Human decision required. The current graph includes a "
            "90-day recording-retention policy. Do not treat this report "
            "as approval to extend retention."
        )

        st.download_button(
            "Download decision report",
            data=create_report(brief["question"], matches),
            file_name="policypath_decision_report.json",
            mime="application/json",
        )

        st.caption(
            "The matching method uses keyword overlap. It is not an LLM "
            "or semantic search system."
        )


# -------------------- ASK-POLICY ASSISTANT --------------------

st.sidebar.markdown("---")
st.sidebar.markdown("### Ask PolicyPath")

ask_question = st.sidebar.text_input(
    "Ask about your policies",
    placeholder="Which control handles retention?",
)

if st.sidebar.button("Ask PolicyPath"):

    if not ask_question.strip():
        st.sidebar.warning("Type a question first.")

    else:
        tokens = [
            word.lower().strip(".,?!:;()")
            for word in ask_question.split()
            if len(word) > 3
        ]

        matches = []

        for _, row in df.iterrows():
            text = " ".join(
                str(row.get(column, ""))
                for column in [
                    "title", "description", "category",
                    "control", "risk", "severity", "owner"
                ]
            ).lower()

            score = sum(token in text for token in tokens)

            if score:
                matches.append((score, row))

        matches.sort(key=lambda item: item[0], reverse=True)

        st.session_state["assistant_question"] = ask_question
        st.session_state["assistant_results"] = [
            {
                column: str(row.get(column, ""))
                for column in [
                    "title", "description", "control",
                    "risk", "severity", "owner"
                ]
            }
            for _, row in matches[:3]
        ]

if st.session_state.get("assistant_question"):

    st.sidebar.markdown("**Graph-based results**")
    st.sidebar.caption(st.session_state["assistant_question"])

    results = st.session_state.get("assistant_results", [])

    if not results:
        st.sidebar.info("No matching records found.")

    for item in results:
        st.sidebar.markdown(f"**{item['title']}**")
        st.sidebar.caption(item["description"] or "No description stored.")
        st.sidebar.write(f"Control: {item['control'] or 'Not linked'}")
        st.sidebar.write(f"Risk: {item['risk'] or 'Not linked'}")
        st.sidebar.write(f"Owner: {item['owner'] or 'Not linked'}")

    st.sidebar.caption(
        "Keyword-based lookup only. Verify the source policy and "
        "consult the responsible owner."
    )


# -------------------- FOOTER --------------------

st.markdown(
    """
    <div style="
        text-align:center;
        margin-top:40px;
        padding-top:20px;
        border-top:1px solid #e3e7f0;
        color:#939bad;
        font-size:.75rem;
    ">
        POLICYPATH · DECISION CONTEXT GRAPH · HUMAN-IN-THE-LOOP
    </div>
    """,
    unsafe_allow_html=True,
)
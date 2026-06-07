import streamlit as st
import requests
import time
from pathlib import Path

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Property Triage",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# LOAD CSS FILE
# -----------------------------

#BASE_DIR = Path(__file__).resolve().parent

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

OLLAMA_URL = "http://localhost:11434/api/generate"
N8N_WEBHOOK = "http://localhost:5678/webhook-test/listing"

# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa",
        use_container_width=True
    )

    st.title("🏠 AI Property System")

    st.markdown("### ⚙️ Engine Infrastructure")
    st.success("Ollama Cluster Connected")
    st.success("Webhook Pipeline Active")

    st.divider()
    st.caption("Enterprise Triage Engine v2.4")

# -----------------------------
# HEADER
# -----------------------------
st.title("🏠 AI Property Triage System")

app_mode = st.radio(
    "Workflow Switcher",
    ["Ollama Intelligence", "Listing Submission Pipeline"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

# =========================================================
# WORKFLOW 1 — ASSISTANT
# =========================================================
if app_mode == "Ollama Intelligence":

    st.subheader("💬 Real Estate Intelligence Assistant")

    user_question = st.text_area(
        "Query Console",
        placeholder="e.g., Evaluate commercial portfolio viability vectors in Haifa...",
        key="intel_input"
    )

    if st.button("Run Evaluation 🚀", key="btn_assistant"):

        if not user_question.strip():
            st.warning("Please input a valid analytical request.")

        else:
            prompt = f"""
You are a professional real estate assistant.

Only answer:
- property
- housing
- real estate
- listings
- rentals
- investments

If unrelated, refuse.

Question: {user_question}
"""

            try:
                st.markdown("### 🤖 Synthesizing Context...")
                progress = st.progress(0)

                for i in range(100):
                    time.sleep(0.005)
                    progress.progress(i + 1)

                response = requests.post(
                    OLLAMA_URL,
                    json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60
                )

                response.raise_for_status()
                result = response.json()

                st.success("Context Compiled Successfully.")

                st.markdown("#### 🤖 Generation Output")
                st.write(result.get("response", "Null payload returned."))

            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# =========================================================
# WORKFLOW 2 — LISTING PIPELINE
# =========================================================
elif app_mode == "Listing Submission Pipeline":

    st.subheader("📋 Ingest Property Profile")

    agent_name = st.text_input("Originating Agent / Broker Identity")

    description = st.text_area(
        "Listing Dossier Description",
        height=180,
        placeholder="Provide architectural breakdown, sizing, and pricing structural specifications..."
    )

    image_urls_text = st.text_area(
        "Visual Asset URLs (One per line)"
    )

    if st.button("Publish to Pipeline 🚀", key="btn_submission"):

        if not description.strip():
            st.warning("Core text parameters are empty. Submission rejected.")

        else:
            image_urls = [
                url.strip()
                for url in image_urls_text.split("\n")
                if url.strip()
            ]

            payload = {
                "agent_name": agent_name,
                "description": description,
                "image_urls": image_urls
            }

            try:
                st.markdown("### ⚙️ Routing payload...")
                progress = st.progress(0)

                for i in range(100):
                    time.sleep(0.005)
                    progress.progress(i + 1)

                response = requests.post(
                    N8N_WEBHOOK,
                    json=payload,
                    timeout=60
                )

                response.raise_for_status()

                try:
                    result = response.json()
                except:
                    result = response.text

                st.success("Ingestion Handshake Confirmed.")

                st.json(payload)
                st.write(result)

                if image_urls:
                    st.markdown("### 🖼 Preview")
                    cols = st.columns(min(3, len(image_urls)))

                    for i, url in enumerate(image_urls[:3]):
                        with cols[i]:
                            st.image(url, use_container_width=True)

            except Exception as e:
                st.error(f"Pipeline Failure: {str(e)}")

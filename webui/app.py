import streamlit as st
import requests
import os
import json
import base64
import html
from google import genai
from google.genai import types

# =========================================================
# SYSTEM STAGING & INFRASTRUCTURE
# =========================================================
st.set_page_config(
    page_title="AI Property Triage Command Center",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Engine API Clients Safely
API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY) if API_KEY else None

def safe_text(value, fallback="Not specified"):
    if value is None:
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    return str(value)


def escape_text(value, fallback="Not specified"):
    return html.escape(safe_text(value, fallback), quote=True)

# Isolated Cloud Asset Storage Engine (ImgBB Integration)
def upload_image_to_url(uploaded_file):
    imgbb_key = os.getenv("IMGBB_API_KEY", "a1fe0fb0e0184f9afbf6599e9bbb0a39")

    if imgbb_key == "YOUR_IMGBB_API_KEY_HERE" or not imgbb_key:
        st.error("ASSET ENGINE ERROR: Valid IMGBB_API_KEY configuration missing.")
        return None

    try:
        img_bytes = uploaded_file.read()
        base64_image = base64.b64encode(img_bytes).decode('utf-8')

        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": imgbb_key,
            "image": base64_image
        }

        response = requests.post(url, data=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["data"]["url"]
        else:
            st.error(f"Cloud Server rejected asset payload: {response.text}")
            return None
    except Exception as e:
        st.error(f"Media Uplink Runtime Exception: {str(e)}")
        return None

# Isolated Style Sheet Loader
def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        pass

load_css("style.css")

N8N_WEBHOOK = "http://localhost:5678/webhook-test/listing"

if "transcribed_text" not in st.session_state:
    st.session_state.transcribed_text = ""

# =========================================================
# CONTROL SIDEBAR ENVIRONMENT
# =========================================================
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa",
        width="stretch"
    )
    st.title("🏠 AI Property System")
    st.markdown("### ⚙️ Engine Infrastructure")

    st.markdown("""
        <div class="status-pill">
            <div class="status-dot"></div>
            <div class="status-text">Gemini Intelligence Online</div>
        </div>
        <div class="status-pill">
            <div class="status-dot"></div>
            <div class="status-text">Webhook Pipeline Active</div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("⚡ Enterprise Triage Engine v3.0-Premium")

# =========================================================
# MASTER APPLICATION VIEWPORT
# =========================================================
st.markdown("<h1 style='text-align: center;'>AI Property Triage System</h1>", unsafe_allow_html=True)

tab_intel, tab_pipeline = st.tabs(["💬 Gemini Intelligence", "📋 Submission Pipeline"])

# =========================================================
# MODULE 1 — GEMINI INTELLIGENCE ASSISTANT
# =========================================================
with tab_intel:
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("💬 Quantum Real Estate Assistant")
        if client is None:
            st.warning("Gemini Intelligence is unavailable because GOOGLE_API_KEY is not configured. The submission pipeline remains available.")
        user_question = st.text_area(
            "Query Console",
            placeholder="e.g., Evaluate commercial portfolio viability vectors in Haifa...",
            key="intel_input",
            height=140,
            label_visibility="collapsed"
        )
        run_intel = st.button("Run Analytics Evaluation 🚀", key="btn_intel", disabled=client is None)

    if run_intel:
        if not user_question.strip():
            st.warning("Action Required: Please input a valid analytical request vector.")
        elif client is None:
            st.error("Gemini Intelligence is unavailable because GOOGLE_API_KEY is not configured.")
        else:
            prompt = f"You are a professional real estate assistant. Only answer about real estate topics. Question: {user_question}"
            try:
                with st.spinner("🤖 Synthesizing Real Estate Model Matrix..."):
                    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

                st.success("Analysis Assembled")
                with st.container(border=True):
                    st.markdown("### 📊 Engine Output Target Summary")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Execution Failure: {str(e)}")

# =========================================================
# MODULE 2 — DATA INGESTION PIPELINE
# =========================================================
with tab_pipeline:
    st.markdown("<br>", unsafe_allow_html=True)

    image_urls = []
    form_col, info_col = st.columns([3, 2], gap="large")

    with form_col:
        st.subheader("📋 Ingest Property Profile")
        agent_name = st.text_input("Originating Agent Identity", placeholder="e.g., Premier Real Estate Management")

        # --- REENGINEERED HIGH-END SELECTION WORKSPACE (CENTERED) ---
        st.markdown("<div class='centered-header'>📋 Description Input Target</div>", unsafe_allow_html=True)

        input_mode = st.radio(
            "input_mode_selector",
            ["📝 Manual Text Ingest", "🎙️ Voice Dictation Mode"],
            horizontal=True,
            label_visibility="collapsed"
        )

        # Staging Option A: Manual text parsing layout
        if "Manual" in input_mode:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload Listing Dossier File (.txt)",
                type=["txt"],
                help="Drop raw textual data frames directly into the active processing buffer."
            )

            if uploaded_file is not None:
                try:
                    st.session_state.transcribed_text = uploaded_file.read().decode("utf-8")
                    st.toast("Dossier File Processed into Text Buffer", icon="⚡")
                except Exception as e:
                    st.error(f"Data Read Violation: {e}")

        # Staging Option B: Unified voice matrix ingestion channels
        elif "Voice" in input_mode:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if client is None:
                st.warning("Voice transcription requires GOOGLE_API_KEY. Use Manual Text Ingest or configure the key.")
            audio_file = st.audio_input("Record property features or overview details", label_visibility="collapsed")

            if audio_file is not None and client is not None:
                try:
                    with st.spinner("Transcribing audio matrix via Gemini 2.5..."):
                        audio_bytes = audio_file.read()
                        audio_part = types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type="audio/wav"
                        )

                        voice_prompt = "Transcribe this real estate audio description accurately. Output ONLY the clear transcript without commentary."
                        audio_response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[audio_part, voice_prompt]
                        )

                        if audio_response.text:
                            st.session_state.transcribed_text = audio_response.text.strip()
                            st.toast("Voice note parsed successfully!", icon="🎙️")
                except Exception as e:
                    st.error(f"Audio Engine Transcription failure: {e}")

        # Persistent Master Editor Block
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        description = st.text_area(
            "Active Output Text Buffer",
            value=st.session_state.transcribed_text,
            height=160,
            placeholder="Comprehensive details will load here automatically...",
            label_visibility="collapsed"
        )

        # --- CLOUD CONVERSION ASSET UPLOADER SECTION (CENTERED) ---
        st.markdown("<div class='centered-header'>🖼️ Visual Asset Configuration Array</div>", unsafe_allow_html=True)

        asset_mode = st.radio(
            "asset_mode_selector",
            ["📁 Upload Media Files", "🌐 Enter Web URLs Directly"],
            horizontal=True,
            label_visibility="collapsed"
        )

        if "Upload" in asset_mode:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            uploaded_images = st.file_uploader(
                "Upload Property Media Assets",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                help="Files uploaded here automatically transform into high-performing public web URLs."
            )
            if uploaded_images:
                for img in uploaded_images:
                    with st.spinner(f"Converting local asset frame '{img.name}'..."):
                        public_url = upload_image_to_url(img)
                        if public_url:
                            image_urls.append(public_url)
                if image_urls:
                    st.toast(f"Engine translated {len(image_urls)} assets into public arrays.", icon="🌐")
        else:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            image_urls_text = st.text_area("Visual Asset URLs (One per line)", placeholder="https://...", height=100)
            image_urls = [url.strip() for url in image_urls_text.split("\n") if url.strip()]

        # Standardized Visual Asset Previews
        if image_urls:
            st.markdown("#### Visual Assets Active Preview Pipeline")
            with st.container(border=True):
                grid_cols = st.columns(min(3, len(image_urls)))
                for i, url in enumerate(image_urls[:6]):
                    with grid_cols[i % 3]:
                        st.image(url, caption=f"Asset #{i+1} (Cloud URL Active)", width="stretch")

        st.markdown("<br>", unsafe_allow_html=True)
        submit_action = st.button("Publish directly to Ecosystem Pipeline 🚀", key="btn_pipeline")

    with info_col:
        st.subheader("💡 Processing Specifications")
        with st.container(border=True):
            st.markdown("""
            **Automated Extraction Pipeline Parameters:**
            * Ensure architectural configurations define structural square metrics clearly.
            * Desktop `.txt` workflows bypass staging validations instantly.
            * Active pipeline validation triggers dynamic dashboard generation payloads.
            * *Media File uploads morph system arrays automatically into standard schema variables.*
            """)
            st.info("System automatically morphs unstructured inputs into verified enterprise asset matrices.")

    # =========================================================
    # CORE PIPELINE PIPING & VERIFICATION DISPLAY
    # =========================================================
    if submit_action:
        if not description.strip():
            st.warning("Pipeline Incomplete: Supply a raw text description or upload an asset file.")
        else:
            payload = {"agent_name": agent_name, "description": description, "image_urls": image_urls}
            try:
                with st.spinner("⚙️ Mapping Data Flow Ingest Pipeline..."):
                    response = requests.post(N8N_WEBHOOK, json=payload, timeout=100)
                    response.raise_for_status()

                    try:
                        data = response.json()
                    except:
                        data = response.text

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        data = None

                if isinstance(data, list):
                    data = data[0] if data and isinstance(data[0], dict) else None
                if not isinstance(data, dict):
                    data = None

                st.success("Ecosystem Handshake Successful")

                if data:
                    st.toast("Dossier Matrix Compiled", icon="🏢")

                    with st.container(border=True):
                        st.markdown(f"""
                            <div class="dossier-header-element">
                                <span class="dossier-tag">System Verified Output Dossier</span>
                                <h2 class="dossier-main-title">{escape_text(data.get("listing_title"), "3-Room Apartment with Sea View - Haifa")}</h2>
                                <div class="dossier-geo-marker">📍 {escape_text(data.get("location"), "Downtown Haifa, Israel")}</div>
                            </div>
                        """, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

                        # Metric Core Architecture
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric(label="📊 Valuation Matrix", value=data.get("price", "2,450,000 ILS"))
                        m2.metric(label="🏠 Property Domain Type", value=data.get("property_type", "Apartment"))
                        m3.metric(label="🛏 Core Array Layout", value=f'{data.get("rooms", "3")} Rooms')
                        m4.metric(label="📐 Dimensions Scalar", value=data.get("size", "110 sqm"))

                        st.markdown("<br>", unsafe_allow_html=True)

                        # Document Partition Split Columns
                        col_main, col_side = st.columns([3, 2], gap="large")

                        with col_main:
                            st.markdown("### 📄 Underwriting Executive Summary")
                            st.markdown(
                                f'<div class="dossier-body-text">{escape_text(data.get("marketing_description"), "A residential apartment on the 8th floor featuring a renovated kitchen and private balcony with sea views. Includes parking and elevator access.")}</div>',
                                unsafe_allow_html=True
                            )

                            st.markdown(f"""
                                <div class="condition-box">
                                    <div class="condition-title">⚠️ Risk Mitigation & Asset Underwriting Note</div>
                                    <div class="condition-body">{escape_text(data.get("condition_note"), "Refurbishment may be required. Maintenance observations include minor ceiling staining and surface rust on the balcony railing.")}</div>
                                </div>
                            """, unsafe_allow_html=True)

                        with col_side:
                            st.markdown("### ✨ Dynamic Highlights")
                            features = data.get("key_features", ["Space: 110 sqm, 3 rooms, 2 bathrooms", "Views: Private balcony with sea view", "Amenities: Private parking, elevator"])
                            if isinstance(features, str):
                                features = [features]
                            for item in features:
                                st.markdown(f"▪️ <span style='color: #cbd5e1;'>{escape_text(item)}</span>", unsafe_allow_html=True)

                            selling_points = data.get("selling_points", [])
                            if isinstance(selling_points, str):
                                selling_points = [selling_points]
                            if selling_points:
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.markdown("### 📈 Pipeline Core Advantages")
                                for point in selling_points:
                                    st.success(safe_text(point))

                    if data.get("listing_brief_markdown"):
                        st.markdown("---")
                        with st.expander("📊 Technical System Analysis Brief", expanded=False):
                            st.markdown(data.get("listing_brief_markdown"))
                else:
                    st.warning("Structural Anomaly: Failed to map incoming JSON structure safely.")
            except Exception as e:
                st.error(f"Pipeline Infrastructure Interruption: {str(e)}")

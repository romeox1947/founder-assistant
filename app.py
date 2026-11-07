import streamlit as st
from src.config import get_settings
from src.extractors import crawl_website, fetch_youtube_channel
from src.store import get_store
from src.agent import answer_question, generate_questions
from src.utils import make_source_label

st.set_page_config(page_title="Satvic Intelligence", page_icon="🧠", layout="wide")

settings = get_settings()

# Optional shared-password gate for a private demo deployment.
# Set APP_PASSWORD in Streamlit Cloud secrets before sharing the app.
app_password = settings.get("app_password")
if app_password:
    import hmac
    if not st.session_state.get("authenticated", False):
        st.title("Satvic Intelligence · Private demo")
        with st.form("login_form"):
            entered = st.text_input("Demo password", type="password")
            submitted = st.form_submit_button("Sign in")
        if submitted:
            if hmac.compare_digest(entered, app_password):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

store = get_store(settings)

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {padding: 1.4rem 1.6rem; border-radius: 16px; background: linear-gradient(120deg,#173d31,#28634d); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0; font-size:2.1rem;}
.hero p {color:#e3f0e9; margin:.35rem 0 0 0;}
.small-muted {color: #718078; font-size: .85rem;}
.source-card {padding:.65rem .8rem; border:1px solid rgba(128,128,128,.25); border-radius:10px; margin:.35rem 0;}
</style>
<div class="hero">
<h1>🧠 Satvic Intelligence</h1>
<p>Research the organisation. Understand the context. Ask better questions.</p>
</div>
""", unsafe_allow_html=True)

# Sidebar: data source configuration and personal context
with st.sidebar:
    st.header("Research sources")
    website_url = st.text_input("Website URL", "https://satvicmovement.org/")
    youtube_url = st.text_input("YouTube channel URL", "https://www.youtube.com/@SatvicMovement")
    max_pages = st.slider("Website pages to scan", 1, 50, 15)
    max_videos = st.slider("YouTube videos to scan", 1, 50, 20)
    include_transcripts = st.checkbox("Extract available video transcripts", True)
    st.caption("Respect website terms, robots.txt, YouTube access limits and copyright. Only public content is processed.")
    st.divider()
    st.subheader("Your private context")
    default_notes = (
        "I was selected for the Satvic Movement Founder’s Office role. "
        "Subha previously mentioned that the team needed to launch a Community Guide, and she has since left. "
        "I want to understand the organisation deeply and prepare thoughtful, specific questions before speaking with the team. "
        "The role initially involves supporting multilingual video dubbing and may expand to other Founder’s Office projects."
    )
    notes = st.text_area("Add your discussions, observations and project notes", value=default_notes, height=190)
    if st.button("Save my context", use_container_width=True):
        store.save_note(notes)
        st.success("Personal context saved.")

tabs = st.tabs(["Overview", "Research sources", "Ask the agent", "Question studio", "Knowledge base"])

with tabs[0]:
    docs = store.list_documents(limit=1000)
    website_count = sum(1 for d in docs if d["source_type"] == "website")
    video_count = sum(1 for d in docs if d["source_type"] == "youtube")
    note_count = sum(1 for d in docs if d["source_type"] == "personal_note")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stored sources", len(docs))
    c2.metric("Website pages", website_count)
    c3.metric("YouTube items", video_count)
    c4.metric("Personal notes", note_count)
    st.subheader("Your research workspace")
    st.write("Use **Research sources** to collect public information. Then ask questions grounded in the saved material, or use **Question studio** to prepare for a conversation.")
    st.info("Cloud persistence: configure Supabase in Streamlit secrets. Without it, the app uses local SQLite, which may reset on cloud redeploys or restarts.")
    st.markdown("**Suggested first workflow**")
    st.markdown("1. Scan the official website.  2. Scan the YouTube channel.  3. Save your personal context.  4. Ask about the Community Guide.  5. Generate meeting questions.")

with tabs[1]:
    st.subheader("Collect public information")
    st.write("Website scanning follows same-domain links and stores extracted page text. YouTube scanning discovers recent channel videos and attempts to retrieve public captions.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌐 Scan website", type="primary", use_container_width=True):
            with st.spinner("Crawling website and extracting readable text..."):
                try:
                    results = crawl_website(website_url, max_pages=max_pages)
                    saved = store.upsert_documents(results)
                    st.success(f"Website scan complete: {len(results)} pages extracted, {saved} new/updated records saved.")
                    if not results:
                        st.warning("No readable pages were extracted. Check the URL, site access, or robots restrictions.")
                except Exception as e:
                    st.error(f"Website scan failed: {e}")
    with col2:
        if st.button("▶️ Scan YouTube channel", type="primary", use_container_width=True):
            with st.spinner("Discovering videos and retrieving available transcripts..."):
                try:
                    results, messages = fetch_youtube_channel(
                        youtube_url, max_videos=max_videos, with_transcripts=include_transcripts
                    )
                    saved = store.upsert_documents(results)
                    st.success(f"YouTube scan complete: {len(results)} video records extracted, {saved} new/updated records saved.")
                    for msg in messages[:8]:
                        st.caption(msg)
                    if not results:
                        st.warning("No videos were extracted. YouTube may have rate-limited the request or the channel URL may be unsupported.")
                except Exception as e:
                    st.error(f"YouTube scan failed: {e}")
    st.divider()
    st.caption("Scanning is on-demand, not continuous. Re-scan when you want to refresh the knowledge base.")

with tabs[2]:
    st.subheader("Ask Satvic Intelligence")
    question = st.text_area("Your research question", placeholder="What do we know about Satvic's community initiatives, and what should I clarify about the Community Guide?", height=100, key="qa_question")
    if st.button("Research answer", type="primary", disabled=not question.strip()):
        with st.spinner("Searching saved knowledge and preparing an evidence-backed answer..."):
            result = answer_question(question, store, settings, notes=notes)
        st.markdown(result["answer"])
        if result["sources"]:
            st.markdown("**Sources used**")
            for i, src in enumerate(result["sources"], 1):
                st.markdown(f"{i}. [{src['title'] or src['source_url']}]({src['source_url']}) · `{src['source_type']}`")
        else:
            st.warning("No matching saved sources. Scan the website or YouTube channel first.")

with tabs[3]:
    st.subheader("Personalised question studio")
    topic = st.text_input("Conversation topic", "Community Guide")
    goal = st.text_area("What do you want to achieve in the conversation?", "Understand the original vision, intended audience, current status, and where I could contribute.", height=85)
    person = st.text_input("Who are you speaking with? (optional)", "Founder’s Office team")
    tone = st.selectbox("Question style", ["Curious and thoughtful", "Strategic and analytical", "Practical and execution-focused", "Warm and conversational"])
    count = st.slider("Number of questions", 3, 10, 5)
    if st.button("✨ Generate personalised questions", type="primary"):
        with st.spinner("Using your notes and collected sources to build contextual questions..."):
            result = generate_questions(topic, goal, person, tone, count, store, settings, notes=notes)
        st.markdown(result["intro"])
        for i, q in enumerate(result["questions"], 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {q['question']}**")
                if q.get("why"):
                    st.caption("Why this is personalised: " + q["why"])
                if q.get("follow_up"):
                    st.markdown("**Possible follow-up:** " + q["follow_up"])
        if result.get("sources"):
            st.markdown("**Research references**")
            for src in result["sources"]:
                st.markdown(f"- [{src['title'] or src['source_url']}]({src['source_url']})")

with tabs[4]:
    st.subheader("Saved knowledge base")
    all_docs = store.list_documents(limit=1000)
    filter_type = st.selectbox("Filter sources", ["All", "website", "youtube", "personal_note"])
    shown = all_docs if filter_type == "All" else [d for d in all_docs if d["source_type"] == filter_type]
    st.caption(f"{len(shown)} records")
    for d in shown[:100]:
        with st.expander(f"{d['title'] or d['source_url']} · {d['source_type']}"):
            st.markdown(f"[Open source]({d['source_url']})")
            st.write((d.get("content") or "")[:1800] or "No text content.")
            if st.button("Delete record", key=f"del_{d['id']}"):
                store.delete_document(d["id"])
                st.rerun()

st.caption("Satvic Intelligence is an independent research assistant, not an official Satvic Movement product. Verify important claims with original sources.")

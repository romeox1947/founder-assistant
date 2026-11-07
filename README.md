# Satvic Intelligence

A free-tier, cloud-deployable research assistant that collects public information from a website and YouTube channel, stores it, answers questions with source links, and drafts personalised conversation questions.

## Features

- Same-domain website crawler using Requests, BeautifulSoup and Trafilatura.
- YouTube channel video discovery with yt-dlp.
- Attempts to retrieve publicly available transcripts with youtube-transcript-api.
- Persistent storage through Supabase PostgreSQL.
- SQLite fallback for local development.
- Evidence-grounded Q&A and personalised question generation through Groq's OpenAI-compatible API.
- No-key fallback so extraction and basic question drafting still work.

## 1. Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

Without credentials, the app uses SQLite and the basic fallback question generator.

## 2. Configure persistent cloud storage (Supabase)

1. Create a free project at https://supabase.com/.
2. Open SQL Editor in the Supabase dashboard.
3. Paste and run `supabase_schema.sql`.
4. Open Project Settings > API.
5. Copy the Project URL and the `service_role` key. Treat the service-role key as a password; never commit it.
6. The app uses Supabase whenever both `SUPABASE_URL` and `SUPABASE_KEY` are configured.

## 3. Configure the AI (Groq)

1. Create an account at https://console.groq.com/.
2. Create an API key, subject to the provider's current free-tier availability and rate limits.
3. The app uses the key only on the server side. If no key is set, the app remains usable with a simple fallback.

## 4. Deploy to Streamlit Community Cloud

1. Create a GitHub repository and upload this project.
2. Visit https://share.streamlit.io/ and connect GitHub.
3. Select the repository, branch, and `app.py`.
4. In the app's Settings > Secrets, paste the contents of `.streamlit/secrets.toml.example` with your real values.
5. Set a strong `APP_PASSWORD` in Streamlit secrets before sharing the demo. The app will show a password gate.
6. Deploy.

Important: Streamlit Community Cloud's local disk should be treated as ephemeral. Configure Supabase for persistent cloud storage. Do not commit `secrets.toml`.

## 5. First use

1. Open the app.
2. Check the website and YouTube channel URLs in the sidebar.
3. Click **Scan website**.
4. Click **Scan YouTube channel**.
5. Edit and save **Your private context**. Add your own meeting notes and project information.
6. Use **Ask the agent** or **Question studio**.

Suggested starting question:

> What public information do we have about Satvic's community initiatives, and what should I clarify about the Community Guide before proposing next steps?

## Important limitations and responsible use

- This is an independent research demo, not an official Satvic Movement product.
- Only public pages and publicly available video metadata/captions are attempted. Some pages, videos or transcripts may be inaccessible.
- Website crawling is limited to the supplied domain and a configurable page count. It checks robots.txt and uses a delay between pages, but you must still respect the website's terms and applicable law.
- YouTube extraction can be rate-limited or blocked. The app does not bypass private access, paywalls, DRM or access controls.
- YouTube likes and view counts are not guaranteed to be available in flat channel extraction. This version focuses on titles, URLs, descriptions and transcripts.
- The search layer is lightweight keyword ranking, not semantic vector search. A future version can add embeddings and hybrid retrieval.
- AI answers can be wrong. Review source links and verify important claims. User notes are not public-source evidence.
- Set `APP_PASSWORD` before sharing the hosted app. This is a simple shared-password gate, not individual user accounts or enterprise-grade authentication.
- Do not paste confidential personal, employee, donor, or internal organisational information into a third-party AI service unless you have permission.

## Troubleshooting

**Supabase connection error:** confirm the project URL, service-role key, and that the SQL schema has been run.

**No YouTube videos found:** update yt-dlp (`pip install -U yt-dlp`), check the channel URL, and retry later. YouTube may rate-limit cloud IP addresses.

**No transcript:** the video may not have captions, captions may be disabled, or YouTube may block transcript retrieval. The video metadata can still be stored.

**Groq errors:** verify the key, model availability and current rate limits. The app falls back to a basic response if generation fails.

## Project structure

```text
satvic-intelligence/
├── app.py
├── requirements.txt
├── supabase_schema.sql
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
└── src/
    ├── __init__.py
    ├── agent.py
    ├── config.py
    ├── extractors.py
    ├── store.py
    └── utils.py
```

import os
import streamlit as st

def get_settings():
    def secret(key, default=None):
        try:
            return st.secrets.get(key, default)
        except Exception:
            return os.getenv(key, default)
    return {
        "groq_api_key": secret("GROQ_API_KEY", os.getenv("GROQ_API_KEY")),
        "app_password": secret("APP_PASSWORD", os.getenv("APP_PASSWORD")),
        "groq_model": secret("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "supabase_url": secret("SUPABASE_URL", os.getenv("SUPABASE_URL")),
        "supabase_key": secret("SUPABASE_KEY", os.getenv("SUPABASE_KEY")),
        "database_mode": secret("DATABASE_MODE", "auto"),
    }

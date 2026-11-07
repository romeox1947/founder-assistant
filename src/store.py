import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st
from src.utils import content_hash

DB_PATH = Path("satvic_intelligence.db")

class SQLiteStore:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, source_type TEXT, source_url TEXT UNIQUE,
          title TEXT, content TEXT, metadata TEXT, content_hash TEXT, created_at TEXT
        )""")
        self.conn.commit()

    def upsert_documents(self, docs):
        count = 0
        for d in docs:
            h = content_hash(d.get("content", ""))
            self.conn.execute("""
            INSERT INTO documents(id,source_type,source_url,title,content,metadata,content_hash,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(source_url) DO UPDATE SET
              source_type=excluded.source_type,title=excluded.title,content=excluded.content,
              metadata=excluded.metadata,content_hash=excluded.content_hash,created_at=excluded.created_at
            """, (str(uuid.uuid4()), d["source_type"], d["source_url"], d.get("title",""),
                  d.get("content",""), json.dumps(d.get("metadata",{})), h,
                  datetime.now(timezone.utc).isoformat()))
            count += 1
        self.conn.commit()
        return count

    def save_note(self, note):
        if note.strip():
            self.upsert_documents([{
                "source_type":"personal_note",
                "source_url":"personal-note://founder-office-context",
                "title":"Personal Founder’s Office context",
                "content":note,
                "metadata":{"private":True}
            }])

    def list_documents(self, limit=1000):
        rows = self.conn.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def search(self, query, limit=8):
        docs = self.list_documents(1000)
        terms = [x.lower() for x in query.split() if len(x) > 2]
        scored = []
        for d in docs:
            text = (d.get("title","") + " " + d.get("content","")).lower()
            score = sum(text.count(t) for t in terms)
            if score:
                scored.append((score,d))
        scored.sort(key=lambda x:x[0], reverse=True)
        return [d for _,d in scored[:limit]]

    def delete_document(self, doc_id):
        self.conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        self.conn.commit()

    def _row(self, r):
        d = dict(r)
        try: d["metadata"] = json.loads(d.get("metadata") or "{}")
        except Exception: d["metadata"] = {}
        return d

class SupabaseStore:
    def __init__(self, url, key):
        from supabase import create_client
        self.client = create_client(url, key)

    def upsert_documents(self, docs):
        rows=[]
        for d in docs:
            rows.append({
                "source_type":d["source_type"], "source_url":d["source_url"],
                "title":d.get("title",""), "content":d.get("content",""),
                "metadata":d.get("metadata",{}), "content_hash":content_hash(d.get("content","")),
                "created_at":datetime.now(timezone.utc).isoformat()
            })
        if rows:
            self.client.table("documents").upsert(rows, on_conflict="source_url").execute()
        return len(rows)

    def save_note(self, note):
        if note.strip():
            self.upsert_documents([{"source_type":"personal_note","source_url":"personal-note://founder-office-context",
                "title":"Personal Founder’s Office context","content":note,"metadata":{"private":True}}])

    def list_documents(self, limit=1000):
        response = self.client.table("documents").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data or []

    def search(self, query, limit=8):
        docs = self.list_documents(1000)
        terms=[x.lower() for x in query.split() if len(x)>2]
        scored=[]
        for d in docs:
            text=(d.get("title","")+" "+d.get("content","")).lower()
            score=sum(text.count(t) for t in terms)
            if score: scored.append((score,d))
        scored.sort(key=lambda x:x[0], reverse=True)
        return [d for _,d in scored[:limit]]

    def delete_document(self, doc_id):
        self.client.table("documents").delete().eq("id",doc_id).execute()

def get_store(settings):
    url, key = settings.get("supabase_url"), settings.get("supabase_key")
    if url and key:
        try:
            return SupabaseStore(url,key)
        except Exception as e:
            st.sidebar.warning(f"Supabase connection failed; using local SQLite. Check secrets and SQL setup. ({e})")
    return SQLiteStore()

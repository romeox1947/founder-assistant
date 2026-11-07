import json
from openai import OpenAI

def _llm_client(settings):
    key = settings.get("groq_api_key")
    if not key:
        return None
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

def _retrieve(store, query, notes="", limit=8):
    docs = store.search(query, limit=limit)
    note_doc = next((d for d in store.list_documents(1000) if d.get("source_type")=="personal_note"), None)
    if notes.strip():
        personal = {"source_type":"personal_note","source_url":"user-provided-context://current-session",
                    "title":"User-provided context","content":notes}
        docs = [personal] + [d for d in docs if d.get("source_type")!="personal_note"]
    elif note_doc and all(d.get("source_type")!="personal_note" for d in docs):
        docs = [note_doc] + docs
    return docs[:limit]

def _context_block(docs):
    chunks=[]
    for i,d in enumerate(docs,1):
        chunks.append(f"[SOURCE {i}] Type: {d.get('source_type')}\nTitle: {d.get('title')}\nURL: {d.get('source_url')}\nContent:\n{(d.get('content') or '')[:6500]}")
    return "\n\n".join(chunks)

def answer_question(question, store, settings, notes=""):
    docs = _retrieve(store, question, notes, limit=8)
    sources = [{"title":d.get("title",""),"source_url":d.get("source_url",""),"source_type":d.get("source_type","")} for d in docs if d.get("source_url","").startswith("http")]
    if not docs:
        return {"answer":"I don't have enough collected information to answer that yet. Scan the website and YouTube channel first, then ask again.", "sources":[]}
    client = _llm_client(settings)
    context = _context_block(docs)
    if client:
        try:
            response=client.chat.completions.create(
                model=settings.get("groq_model","llama-3.3-70b-versatile"),
                temperature=0.25,
                messages=[
                    {"role":"system","content":"You are Satvic Intelligence, a careful research assistant. Answer only from supplied sources and user notes. Clearly label user-provided context separately from public-source facts. Never invent a person's statements, intentions, project status, metrics, or dates. If evidence is missing, say so and suggest what to verify. Cite claims inline as [SOURCE 1], [SOURCE 2]."},
                    {"role":"user","content":f"Question: {question}\n\nResearch material:\n{context}\n\nWrite a useful, structured answer and identify uncertainties."}
                ])
            answer=response.choices[0].message.content
        except Exception as e:
            answer=f"AI service error ({e}). Here are the closest saved source excerpts:\n\n"+context[:5000]
    else:
        answer=("**AI API key not configured.** This is a keyword-based preview of the closest stored material.\n\n"
                + "\n\n".join(f"**{d.get('title')}**\n{(d.get('content') or '')[:900]}" for d in docs[:4])
                + "\n\nAdd a free Groq API key in Streamlit secrets to enable generated answers.")
    return {"answer":answer,"sources":sources}

def generate_questions(topic, goal, person, tone, count, store, settings, notes=""):
    query=f"{topic} {goal} {person}"
    docs=_retrieve(store, query, notes, limit=8)
    sources=[{"title":d.get("title",""),"source_url":d.get("source_url","")} for d in docs if d.get("source_url","").startswith("http")]
    if not docs:
        return {"intro":"There is not enough saved research yet. Scan the website and YouTube channel to ground the questions in real information.",
                "questions":[],"sources":[]}
    client=_llm_client(settings)
    context=_context_block(docs)
    if client:
        try:
            response=client.chat.completions.create(
                model=settings.get("groq_model","llama-3.3-70b-versatile"),
                temperature=0.55,
                response_format={"type":"json_object"},
                messages=[
                    {"role":"system","content":"Create personalised, respectful meeting questions. Ground them in the supplied evidence and user notes. Never claim an individual said something unless the notes explicitly say so. Separate verified facts from assumptions. Return valid JSON with keys intro and questions. questions is an array of objects with question, why, follow_up. Make questions specific, open-ended, non-generic, and useful. Include exactly the requested count."},
                    {"role":"user","content":f"Topic: {topic}\nGoal: {goal}\nPerson/audience: {person}\nTone: {tone}\nCount: {count}\n\nContext and sources:\n{context}"}
                ])
            data=json.loads(response.choices[0].message.content)
            qs=data.get("questions",[])[:count]
            return {"intro":data.get("intro","Here are personalised questions based on the available research."),
                    "questions":qs,"sources":sources}
        except Exception:
            pass
    # Useful no-key fallback: build grounded prompts from the highest-ranked snippets.
    qs=[]
    for d in docs[:count]:
        title=d.get("title") or d.get("source_type")
        excerpt=(d.get("content") or "").replace("\n"," ")[:180]
        qs.append({
            "question":f"How does the work or idea described in “{title}” connect to {topic.lower()}, and what would be the most useful next step?",
            "why":f"This is based on the saved material: {excerpt}",
            "follow_up":f"What would success look like, and who would need to be involved?"
        })
    while len(qs)<count:
        qs.append({
            "question":f"What is the intended outcome for {topic}, and what would you want someone in my role to take ownership of first?",
            "why":"This clarifies the objective and your potential contribution without assuming the current status.",
            "follow_up":"What would be a useful first milestone?"
        })
    return {"intro":"These are draft questions based on your saved context and the closest matching research. Add a Groq API key for richer synthesis.",
            "questions":qs,"sources":sources}

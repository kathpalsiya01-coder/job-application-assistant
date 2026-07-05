import os
import json
import re
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# ============================================
# FIX: Load API key — works locally AND on Streamlit Cloud
# ============================================
try:
    import streamlit as st
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
except Exception:
    from dotenv import load_dotenv
    load_dotenv()

# State Schema
class ApplicationState(TypedDict):
    jd_text: str
    resume_text: str
    company_name: str
    role_name: str
    required_skills: List[str]
    responsibilities: List[str]
    candidate_skills: List[str]
    candidate_experience: str
    matching_skills: List[str]
    missing_skills: List[str]
    strong_points: List[str]
    tailored_bullets: List[str]
    cover_letter: str
    application_score: int
    score_feedback: str
    retry_count: int
    final_report: str

def clean_json_response(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text

def parse_llm_json(response_text: str, defaults: dict) -> dict:
    cleaned = clean_json_response(response_text)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        return defaults

# ============================================
# KEY FIX: Create LLM INSIDE each function
# NOT at module level
# ============================================

def extract_jd_info(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    
    prompt = f"""Analyze this job description and return a JSON with:
- company_name: string
- role_name: string  
- required_skills: list of strings (technical skills only)
- responsibilities: list of strings (top 5 key responsibilities)
Job Description: {state.get('jd_text', '')}
Return ONLY valid JSON, no markdown, no explanation."""

    messages = [
        SystemMessage(content="You are an expert job description analyzer. Extract information accurately and return ONLY JSON."),
        HumanMessage(content=prompt)
    ]
    response = llm.invoke(messages)
    defaults = {
        "company_name": "Unknown Company",
        "role_name": "Unknown Role",
        "required_skills": [],
        "responsibilities": []
    }
    parsed = parse_llm_json(response.content, defaults)
    return {
        "company_name": parsed.get("company_name", "Unknown Company"),
        "role_name": parsed.get("role_name", "Unknown Role"),
        "required_skills": parsed.get("required_skills", []),
        "responsibilities": parsed.get("responsibilities", [])
    }

def analyze_resume(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    
    prompt = f"""Analyze this resume and return a JSON with:
- candidate_skills: list of strings (all technical skills found)
- candidate_experience: string (2-3 sentence summary of experience)
Resume: {state.get('resume_text', '')}
Return ONLY valid JSON, no markdown, no explanation."""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    defaults = {
        "candidate_skills": [],
        "candidate_experience": ""
    }
    parsed = parse_llm_json(response.content, defaults)
    return {
        "candidate_skills": parsed.get("candidate_skills", []),
        "candidate_experience": parsed.get("candidate_experience", "")
    }

def gap_analysis(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    
    prompt = f"""Compare these and return JSON:
Required skills: {state.get('required_skills', [])}
Candidate skills: {state.get('candidate_skills', [])}
Return JSON with:
- matching_skills: list (skills present in both)
- missing_skills: list (required but candidate doesn't have)
- strong_points: list of strings (top 3 reasons this candidate is a good fit)
Return ONLY valid JSON."""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    defaults = {
        "matching_skills": [],
        "missing_skills": [],
        "strong_points": []
    }
    parsed = parse_llm_json(response.content, defaults)
    return {
        "matching_skills": parsed.get("matching_skills", []),
        "missing_skills": parsed.get("missing_skills", []),
        "strong_points": parsed.get("strong_points", [])
    }

def generate_bullets(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
    
    retry_count = state.get('retry_count', 0)
    score_feedback = state.get('score_feedback', '')
    role_name = state.get('role_name', 'Unknown Role')
    company_name = state.get('company_name', 'Unknown Company')
    required_skills = state.get('required_skills', [])
    candidate_experience = state.get('candidate_experience', '')
    strong_points = state.get('strong_points', [])

    prefix = ""
    if retry_count > 0:
        prefix = f"Your previous resume bullets scored too low.\nScore feedback: {score_feedback}\n"

    prompt = f"""{prefix}Rewrite stronger resume bullet points for the role of {role_name} at {company_name}.
Use these keywords naturally: {required_skills}
Base them on this experience: {candidate_experience}
Strong points to emphasize: {strong_points}
Return a JSON with:
- tailored_bullets: list of 5 strings (each bullet starts with strong action verb, includes metrics where possible)
Return ONLY valid JSON."""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    defaults = {"tailored_bullets": []}
    parsed = parse_llm_json(response.content, defaults)
    return {
        "tailored_bullets": parsed.get("tailored_bullets", [])
    }

def write_cover_letter(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
    
    prompt = f"""Write a professional, personalized cover letter for:
Role: {state.get('role_name')} at {state.get('company_name')}
Candidate profile:
- Experience: {state.get('candidate_experience')}
- Matching skills: {state.get('matching_skills')}
- Strong points: {state.get('strong_points')}
Requirements:
- 3 paragraphs maximum
- First paragraph: enthusiasm for role + company specific mention
- Second paragraph: most relevant experience + 2 specific skills
- Third paragraph: call to action, professional close
- Tone: professional but warm, confident not arrogant
- Do NOT use generic phrases like 'I am writing to apply'
Return ONLY the cover letter text."""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    return {"cover_letter": response.content.strip()}

def score_application(state: ApplicationState) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)
    
    cover_letter = state.get('cover_letter', '')
    
    prompt = f"""Score this job application from 1-10 and explain why.
Role: {state.get('role_name')} at {state.get('company_name')}
Required skills: {state.get('required_skills')}
Matching skills: {state.get('matching_skills')}
Missing skills: {state.get('missing_skills')}
Resume bullets: {state.get('tailored_bullets')}
Cover letter preview: {cover_letter[:500]}
Return JSON with:
- score: integer 1-10
- feedback: string (2-3 sentences explaining score)
Return ONLY valid JSON."""

    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    defaults = {"score": 7, "feedback": "Unable to parse feedback."}
    parsed = parse_llm_json(response.content, defaults)
    current_retry = state.get('retry_count', 0)
    return {
        "application_score": parsed.get("score", 7),
        "score_feedback": parsed.get("feedback", "Unable to parse feedback."),
        "retry_count": current_retry + 1
    }

def compile_report(state: ApplicationState) -> dict:
    bullets_formatted = "\n".join(
        [f"• {bullet}" for bullet in state.get('tailored_bullets', [])]
    )
    report = f"""=== JOB APPLICATION REPORT ===
Role: {state.get('role_name')} at {state.get('company_name')}
Application Score: {state.get('application_score')}/10

SKILL MATCH ANALYSIS:
✅ Matching Skills: {state.get('matching_skills')}
❌ Missing Skills: {state.get('missing_skills')}
💪 Strong Points: {state.get('strong_points')}

TAILORED RESUME BULLETS:
{bullets_formatted}

COVER LETTER:
{state.get('cover_letter')}

SCORE FEEDBACK:
{state.get('score_feedback')}"""
    return {"final_report": report}

def should_retry(state: ApplicationState) -> str:
    score = state.get("application_score", 0)
    retry_count = state.get("retry_count", 0)
    if score < 7 and retry_count < 2:
        return "retry"
    return "done"

# Graph Assembly
builder = StateGraph(ApplicationState)
builder.add_node("extract_jd_info", extract_jd_info)
builder.add_node("analyze_resume", analyze_resume)
builder.add_node("gap_analysis", gap_analysis)
builder.add_node("generate_bullets", generate_bullets)
builder.add_node("write_cover_letter", write_cover_letter)
builder.add_node("score_application", score_application)
builder.add_node("compile_report", compile_report)

builder.add_edge(START, "extract_jd_info")
builder.add_edge("extract_jd_info", "analyze_resume")
builder.add_edge("analyze_resume", "gap_analysis")
builder.add_edge("gap_analysis", "generate_bullets")
builder.add_edge("generate_bullets", "write_cover_letter")
builder.add_edge("write_cover_letter", "score_application")
builder.add_conditional_edges(
    "score_application",
    should_retry,
    {"retry": "generate_bullets", "done": "compile_report"}
)
builder.add_edge("compile_report", END)

graph = builder.compile()

def run_agent(jd_text: str, resume_text: str) -> ApplicationState:
    initial_state = {
        "jd_text": jd_text,
        "resume_text": resume_text,
        "company_name": "",
        "role_name": "",
        "required_skills": [],
        "responsibilities": [],
        "candidate_skills": [],
        "candidate_experience": "",
        "matching_skills": [],
        "missing_skills": [],
        "strong_points": [],
        "tailored_bullets": [],
        "cover_letter": "",
        "application_score": 0,
        "score_feedback": "",
        "retry_count": 0,
        "final_report": ""
    }
    return graph.invoke(initial_state)
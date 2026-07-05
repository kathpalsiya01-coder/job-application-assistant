import os
import json
import re
from typing import TypedDict, List
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
# Load environment variables
load_dotenv()
# Initialize LLMs
# langchain-groq automatically picks up GROQ_API_KEY from environment variables
llm_3 = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
llm_7 = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
llm_0 = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)
# State Schema definition
class ApplicationState(TypedDict):
    jd_text: str              # raw job description
    resume_text: str          # raw resume text from PDF
    company_name: str         # extracted from JD
    role_name: str            # extracted from JD
    required_skills: List[str] # extracted from JD
    responsibilities: List[str] # extracted from JD
    candidate_skills: List[str] # extracted from resume
    candidate_experience: str # extracted from resume summary
    matching_skills: List[str] # skills in both JD and resume
    missing_skills: List[str] # skills in JD but not resume
    strong_points: List[str]  # candidate's strongest selling points
    tailored_bullets: List[str] # rewritten resume bullet points
    cover_letter: str         # generated cover letter
    application_score: int    # 1-10 score
    score_feedback: str       # why this score, what to improve
    retry_count: int          # for self-correction loop
    final_report: str         # compiled final output
def clean_json_response(text: str) -> str:
    """Helper to clean markdown JSON blocks from LLM output."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
def parse_llm_json(response_text: str, defaults: dict) -> dict:
    """Safely parse LLM string into JSON with fallback defaults."""
    cleaned = clean_json_response(response_text)
    try:
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON parsing error: {e}. Raw response was: {response_text}")
        return defaults
# --- Nodes ---
def extract_jd_info(state: ApplicationState) -> dict:
    """Extract company name, role name, required skills, and key responsibilities from JD."""
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
    
    response = llm_3.invoke(messages)
    
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
    """Extract candidate skills and experience summary from candidate's resume."""
    prompt = f"""Analyze this resume and return a JSON with:
- candidate_skills: list of strings (all technical skills found)
- candidate_experience: string (2-3 sentence summary of experience)
Resume: {state.get('resume_text', '')}
Return ONLY valid JSON, no markdown, no explanation."""
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = llm_3.invoke(messages)
    
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
    """Conduct comparison between required skills and candidate's skills."""
    prompt = f"""Compare these and return JSON:
Required skills: {state.get('required_skills', [])}
Candidate skills: {state.get('candidate_skills', [])}
Return JSON with:
- matching_skills: list (skills present in both)
- missing_skills: list (required but candidate doesn't have)
- strong_points: list of strings (top 3 reasons this candidate is a good fit)
Return ONLY valid JSON."""
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = llm_3.invoke(messages)
    
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
    """Generate or refine 5 high-impact resume bullet points tailored to the job description."""
    retry_count = state.get('retry_count', 0)
    score_feedback = state.get('score_feedback', '')
    role_name = state.get('role_name', 'Unknown Role')
    company_name = state.get('company_name', 'Unknown Company')
    required_skills = state.get('required_skills', [])
    candidate_experience = state.get('candidate_experience', '')
    strong_points = state.get('strong_points', [])
    
    prefix = ""
    if retry_count > 0:
        prefix = f"""Your previous resume bullets scored too low.
Score feedback: {score_feedback}
"""
    prompt = f"""{prefix}Rewrite stronger resume bullet points for the role of {role_name} at {company_name}.
Use these keywords naturally: {required_skills}
Base them on this experience: {candidate_experience}
Strong points to emphasize: {strong_points}
Return a JSON with:
- tailored_bullets: list of 5 strings (each bullet starts with strong action verb, includes metrics where possible, naturally includes JD keywords)
Return ONLY valid JSON."""
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = llm_7.invoke(messages)
    
    defaults = {
        "tailored_bullets": []
    }
    parsed = parse_llm_json(response.content, defaults)
    
    return {
        "tailored_bullets": parsed.get("tailored_bullets", [])
    }
def write_cover_letter(state: ApplicationState) -> dict:
    """Generate a highly targeted professional cover letter."""
    role_name = state.get('role_name', 'Unknown Role')
    company_name = state.get('company_name', 'Unknown Company')
    candidate_experience = state.get('candidate_experience', '')
    matching_skills = state.get('matching_skills', [])
    strong_points = state.get('strong_points', [])
    
    prompt = f"""Write a professional, personalized cover letter for:
Role: {role_name} at {company_name}
Candidate profile:
- Experience: {candidate_experience}
- Matching skills: {matching_skills}
- Strong points: {strong_points}
Requirements:
- 3 paragraphs maximum
- First paragraph: enthusiasm for role + company specific mention
- Second paragraph: most relevant experience + 2 specific skills
- Third paragraph: call to action, professional close
- Tone: professional but warm, confident not arrogant
- Do NOT use generic phrases like 'I am writing to apply'
- Start with something engaging about the role or company
Return ONLY the cover letter text, no subject line, no 'Dear Hiring Manager' header needed."""
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = llm_7.invoke(messages)
    return {
        "cover_letter": response.content.strip()
    }
def score_application(state: ApplicationState) -> dict:
    """Analyze the tailored bullets and cover letter to evaluate application readiness."""
    role_name = state.get('role_name', 'Unknown Role')
    company_name = state.get('company_name', 'Unknown Company')
    required_skills = state.get('required_skills', [])
    matching_skills = state.get('matching_skills', [])
    missing_skills = state.get('missing_skills', [])
    tailored_bullets = state.get('tailored_bullets', [])
    cover_letter = state.get('cover_letter', '')
    
    prompt = f"""Score this job application from 1-10 and explain why.
Role: {role_name} at {company_name}
Required skills: {required_skills}
Matching skills: {matching_skills}  
Missing skills: {missing_skills}
Resume bullets: {tailored_bullets}
Cover letter preview: {cover_letter[:500]}
Return JSON with:
- score: integer 1-10
- feedback: string (2-3 sentences explaining score and specific improvements needed if score < 8)
Scoring criteria:
- 9-10: Excellent match, strong bullets, compelling letter
- 7-8: Good match, minor improvements needed
- 5-6: Moderate match, significant gaps
- Below 5: Poor match
Return ONLY valid JSON."""
    messages = [
        HumanMessage(content=prompt)
    ]
    
    response = llm_0.invoke(messages)
    
    defaults = {
        "score": 7,
        "feedback": "Unable to parse feedback."
    }
    parsed = parse_llm_json(response.content, defaults)
    
    current_retry = state.get('retry_count', 0)
    
    return {
        "application_score": parsed.get("score", 7),
        "score_feedback": parsed.get("feedback", "Unable to parse feedback."),
        "retry_count": current_retry + 1
    }
def compile_report(state: ApplicationState) -> dict:
    """Formats all the extracted and generated results into a plain text output report."""
    role_name = state.get('role_name', 'Unknown Role')
    company_name = state.get('company_name', 'Unknown Company')
    application_score = state.get('application_score', 0)
    matching_skills = state.get('matching_skills', [])
    missing_skills = state.get('missing_skills', [])
    strong_points = state.get('strong_points', [])
    tailored_bullets = state.get('tailored_bullets', [])
    cover_letter = state.get('cover_letter', '')
    score_feedback = state.get('score_feedback', '')
    
    bullets_formatted = "\n".join([f"• {bullet}" for bullet in tailored_bullets])
    
    report = f"""=== JOB APPLICATION REPORT ===
Role: {role_name} at {company_name}
Application Score: {application_score}/10
SKILL MATCH ANALYSIS:
✅ Matching Skills: {matching_skills}
❌ Missing Skills: {missing_skills}
💪 Strong Points: {strong_points}
TAILORED RESUME BULLETS:
{bullets_formatted}
COVER LETTER:
{cover_letter}
SCORE FEEDBACK:
{score_feedback}"""
    
    return {
        "final_report": report
    }
# --- Routing ---
def should_retry(state: ApplicationState) -> str:
    """Conditional routing edge."""
    score = state.get("application_score", 0)
    retry_count = state.get("retry_count", 0)
    
    # Route back to generate_bullets if the score is low and we haven't hit the retry limit
    if score < 7 and retry_count < 2:
        return "retry"
    else:
        return "done"
# --- Graph Assembly ---
builder = StateGraph(ApplicationState)
# Add nodes
builder.add_node("extract_jd_info", extract_jd_info)
builder.add_node("analyze_resume", analyze_resume)
builder.add_node("gap_analysis", gap_analysis)
builder.add_node("generate_bullets", generate_bullets)
builder.add_node("write_cover_letter", write_cover_letter)
builder.add_node("score_application", score_application)
builder.add_node("compile_report", compile_report)
# Build connections
builder.add_edge(START, "extract_jd_info")
builder.add_edge("extract_jd_info", "analyze_resume")
builder.add_edge("analyze_resume", "gap_analysis")
builder.add_edge("gap_analysis", "generate_bullets")
builder.add_edge("generate_bullets", "write_cover_letter")
builder.add_edge("write_cover_letter", "score_application")
# Add the conditional router after scoring
builder.add_conditional_edges(
    "score_application",
    should_retry,
    {
        "retry": "generate_bullets",
        "done": "compile_report"
    }
)
builder.add_edge("compile_report", END)
# Compile graph
graph = builder.compile()
# --- Main Entry Point ---
def run_agent(jd_text: str, resume_text: str) -> ApplicationState:
    """
    Executes the StateGraph agent with the initial user input.
    """
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
    
    final_state = graph.invoke(initial_state)
    return final_state

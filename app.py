import streamlit as st
import os
from dotenv import load_dotenv
# Import utilities and agent logic
from pdf_reader import extract_text_from_pdf
from agent import run_agent
# Load environment variables
load_dotenv()
# Streamlit Page Config
st.set_page_config(
    page_title="🎯 Job Application Assistant",
    layout="wide",
    page_icon="🎯"
)
# Premium UI Styling using Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Application Font Family */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    /* Title Styling */
    .title-wrapper {
        text-align: center;
        padding: 2rem 1.5rem;
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%);
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }
    
    .title-main {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -1px;
    }
    
    .title-sub {
        font-size: 1.2rem;
        color: #94a3b8;
        margin-top: 0.75rem;
        font-weight: 400;
        letter-spacing: 0.5px;
    }
    
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
    }
    
    /* Input Area and Form Styling */
    .stTextArea textarea {
        border-radius: 10px;
        border: 1px solid #cbd5e1;
        font-size: 0.95rem;
    }
    
    /* Button Customization */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: None;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 2rem;
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4);
        transition: all 0.2s ease;
    }
    
    div.stButton > button:first-child:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.5);
    }
</style>
""", unsafe_allow_html=True)
# Initialize Session State
if "result" not in st.session_state:
    st.session_state.result = None
if "processing" not in st.session_state:
    st.session_state.processing = False
# Render Header banner
st.markdown("""
<div class="title-wrapper">
    <h1 class="title-main">🎯 AI Job Application Assistant</h1>
    <p class="title-sub">Upload your resume + paste a job description &rarr; get a complete tailored application package</p>
</div>
""", unsafe_allow_html=True)
# API Key Validation Message
api_key = os.environ.get("GROQ_API_KEY", "")
if not api_key or api_key == "your_key_here":
    st.warning("⚠️ **GROQ_API_KEY is not configured!** Please set your API key in the `.env` file in the project directory (`job_application_assistant/.env`) to run the AI assistant.")
# Main layout split
col_input, col_result = st.columns([0.45, 0.55], gap="large")
with col_input:
    st.markdown("### 📋 Your Inputs")
    
    uploaded_file = st.file_uploader(
        "Upload your Resume (PDF)", 
        type=["pdf"],
        help="Upload a standard PDF resume containing your education, skills, and work experience."
    )
    
    jd_text = st.text_area(
        "Paste Job Description",
        height=300,
        placeholder="Paste the full job description here...",
        help="Paste the job description including responsibilities, requirements, and information about the hiring company."
    )
    
    # Submit button disabled unless both PDF and JD are present
    submit_disabled = not (uploaded_file and jd_text.strip()) or not api_key or api_key == "your_key_here"
    
    generate_btn = st.button(
        "🚀 Generate My Application",
        type="primary",
        disabled=submit_disabled,
        use_container_width=True
    )
    
    if generate_btn:
        st.session_state.processing = True
        st.session_state.result = None
        
        with st.spinner("🤖 Agent is analyzing and generating your application..."):
            try:
                # 1. Extract text from the uploaded PDF
                resume_text = extract_text_from_pdf(uploaded_file)
                
                if not resume_text:
                    st.error("❌ Failed to extract text from the uploaded PDF. Please ensure it is a text-readable PDF.")
                    st.session_state.processing = False
                else:
                    # 2. Run the LangGraph agent
                    result_state = run_agent(jd_text, resume_text)
                    st.session_state.result = result_state
            except Exception as e:
                st.error(f"❌ An error occurred during agent execution: {str(e)}")
                st.session_state.processing = False
            else:
                st.session_state.processing = False
                st.rerun()
with col_result:
    st.markdown("### 🔍 Generated Package")
    
    if st.session_state.result is None:
        st.info("Upload your resume and paste a job description on the left to get started.")
    else:
        res = st.session_state.result
        
        # Fetch data fields safely
        score = res.get("application_score", 0)
        company_name = res.get("company_name", "Unknown Company")
        role_name = res.get("role_name", "Unknown Role")
        matching_skills = res.get("matching_skills", [])
        missing_skills = res.get("missing_skills", [])
        strong_points = res.get("strong_points", [])
        tailored_bullets = res.get("tailored_bullets", [])
        cover_letter = res.get("cover_letter", "")
        score_feedback = res.get("score_feedback", "")
        final_report = res.get("final_report", "")
        
        # Display Success Banner
        st.success("✅ Application package ready!")
        
        # Display Metric
        st.metric(label="Application Readiness Score", value=f"{score}/10")
        
        # Tabs for result categories
        tab_gap, tab_bullets, tab_letter, tab_report = st.tabs([
            "📊 Gap Analysis", 
            "📝 Resume Bullets", 
            "✉️ Cover Letter", 
            "📄 Full Report"
        ])
        
        # Tab 1: Gap Analysis
        with tab_gap:
            col_match, col_miss, col_strong = st.columns(3)
            
            with col_match:
                st.markdown("#### ✅ Matching Skills")
                if matching_skills:
                    for skill in matching_skills:
                        st.success(skill)
                else:
                    st.caption("No matching skills detected.")
                    
            with col_miss:
                st.markdown("#### ❌ Missing Skills")
                if missing_skills:
                    for skill in missing_skills:
                        st.error(skill)
                else:
                    st.caption("No missing skills detected!")
                    
            with col_strong:
                st.markdown("#### 💪 Strong Points")
                if strong_points:
                    for point in strong_points:
                        st.markdown(f"- {point}")
                else:
                    st.caption("No specific strong points identified.")
            
            st.markdown("---")
            st.info(f"**Score Feedback:** {score_feedback}")
            
        # Tab 2: Resume Bullets
        with tab_bullets:
            st.markdown(f"#### Tailored Resume Bullets for **{role_name}** at **{company_name}**")
            if tailored_bullets:
                for bullet in tailored_bullets:
                    st.markdown(f"• {bullet}")
            else:
                st.write("No custom bullets generated.")
            st.caption("💡 *Copy these directly into your resume's experience section.*")
            
        # Tab 3: Cover Letter
        with tab_letter:
            st.markdown("#### Tailored Cover Letter")
            st.text_area(
                "Cover Letter Preview", 
                value=cover_letter, 
                height=400, 
                disabled=True, 
                label_visibility="collapsed"
            )
            st.download_button(
                label="📥 Download Cover Letter (.txt)",
                data=cover_letter,
                file_name=f"Cover_Letter_{company_name.replace(' ', '_')}_{role_name.replace(' ', '_')}.txt",
                mime="text/plain"
            )
            
        # Tab 4: Full Report
        with tab_report:
            st.markdown("#### Full Application Analysis Report")
            st.text_area(
                "Report Preview", 
                value=final_report, 
                height=500, 
                disabled=True, 
                label_visibility="collapsed"
            )
            st.download_button(
                label="📥 Download Full Report (.txt)",
                data=final_report,
                file_name=f"Job_Application_Report_{company_name.replace(' ', '_')}_{role_name.replace(' ', '_')}.txt",
                mime="text/plain"
            )
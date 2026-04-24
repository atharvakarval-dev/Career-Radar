import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys
import re

# Add parent directory to path so jobspy can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobspy import scrape_jobs, scrape_smart_fresher_jobs, format_hunt_results

# Set page config
st.set_page_config(
    page_title="JobSpy Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #2E51F8;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1a3cb3;
        color: white;
        transform: translateY(-2px);
    }
    .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #2E51F8, #8A2BE2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔍 JobSpy Dashboard")
st.markdown("Automated high-performance job scraping platform.")

with st.sidebar:
    st.header("⚙️ Scrape Settings")
    
    strategy = st.selectbox("Strategy", ["Default", "Smart Fresher Hunt"], index=0, help="Smart Fresher Hunt will automatically test multiple keyword combinations to find hidden fresher jobs.")
    
    search_term = st.text_input("Search Term", value="software engineer fresher OR junior developer")
    
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Location", value="India")
    with col2:
        country_indeed = st.text_input("Country (Indeed)", value="India")
    
    col3, col4 = st.columns(2)
    with col3:
        results_wanted = st.number_input("Results Wanted", min_value=1, max_value=1000, value=50)
    with col4:
        hours_old = st.number_input("Hours Old", min_value=1, max_value=720, value=72)
        
    col5, col6 = st.columns(2)
    with col5:
        job_type = st.selectbox("Job Type", ["any", "fulltime", "parttime", "internship", "contract"])
    with col6:
        is_remote = st.checkbox("Remote Only", value=False)
        
    all_sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter", "google", "naukri", "internshala", "foundit", "shine", "timesjobs"]
    sites = st.multiselect("Job Sites", all_sites, default=["indeed", "linkedin"])
    
    start_scrape = st.button("🚀 Start Scraping", use_container_width=True)

# Main area
if start_scrape:
    if not sites:
        st.error("Please select at least one job site.")
    else:
        with st.status("Scraping jobs... this might take a few minutes.", expanded=True) as status:
            st.write(f"Targeting {len(sites)} sites for '{search_term}'...")
            try:
                if strategy == "Smart Fresher Hunt":
                    st.write("Running smart fresher hunt (combining multiple keywords)...")
                    jobs = scrape_smart_fresher_jobs(
                        top_n_combinations=5,
                        location=location,
                        site_rotation=sites,
                        country_indeed=country_indeed,
                        results_wanted_per_combo=results_wanted,
                        preferred_days_old=hours_old // 24 if hours_old else 7,
                        verbose=0
                    )
                    st.write("Formatting results...")
                    jobs = format_hunt_results(jobs)
                else:
                    st.write("Running default scrape...")
                    jobs = scrape_jobs(
                        site_name=sites,
                        search_term=search_term,
                        location=location,
                        results_wanted=results_wanted,
                        hours_old=hours_old,
                        country_indeed=country_indeed,
                        job_type=job_type if job_type != "any" else None,
                        is_remote=is_remote,
                    )
                status.update(label=f"Scrape complete! Found {len(jobs)} jobs.", state="complete", expanded=False)
                
                st.session_state["jobs_df"] = jobs
                st.session_state["last_scrape"] = datetime.now()
            except Exception as e:
                status.update(label=f"Scrape failed: {str(e)}", state="error", expanded=True)

if "jobs_df" in st.session_state and st.session_state["jobs_df"] is not None:
    df = st.session_state["jobs_df"]
    
    if df.empty:
        st.warning("No jobs found with the current criteria.")
    else:
        # Metrics Row
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Jobs Found", len(df))
        m2.metric("Platforms Successfully Scraped", len(df['site'].unique()) if 'site' in df.columns else (len(df['found_on_platforms'].unique()) if 'found_on_platforms' in df.columns else 1))
        m3.metric("Last Updated", st.session_state['last_scrape'].strftime('%H:%M:%S'))

        st.divider()
        
        # Filters
        st.markdown("### 📊 Filter Results")
        
        f1, f2 = st.columns([3, 1])
        with f1:
            text_filter = st.text_input("🔎 Quick Filter (Search across all columns):", placeholder="e.g. Python, remote, bangalore")
        with f2:
            st.write("") # spacing
            st.write("") # spacing
            fresher_only = st.checkbox("🎓 Fresher Roles Only", help="Strictly filter titles and descriptions for fresher/entry-level keywords.")
            
        display_df = df.copy()
        
        if text_filter:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(text_filter, case=False, na=False)).any(axis=1)
            display_df = display_df[mask]
            
        if fresher_only:
            text_columns = [col for col in ("title", "description", "experience_range", "skills", "job_title", "description_full") if col in display_df.columns]
            if text_columns:
                fresher_pattern = r"intern|junior|fresher|entry|associate|trainee|graduate|new grad|0-1|0-2"
                searchable = display_df[text_columns].fillna("").astype(str).agg(" ".join, axis=1)
                display_df = display_df[searchable.str.contains(fresher_pattern, case=False, na=False)]
                
        # Make job urls clickable if they exist
        if 'job_url' in display_df.columns:
            st.dataframe(
                display_df,
                use_container_width=True,
                height=600,
                column_config={
                    "job_url": st.column_config.LinkColumn("Job Link"),
                    "description": st.column_config.TextColumn("Description", width="large")
                }
            )
        else:
            st.dataframe(display_df, use_container_width=True, height=600)
        
        # Download
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Filtered Results as CSV",
            data=csv,
            file_name="jobspy_results.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
else:
    st.info("👈 Configure your settings in the sidebar and click 'Start Scraping' to begin.")

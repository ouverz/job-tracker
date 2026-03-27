from urllib.parse import urlencode

# Maps job-title keywords to related peer LinkedIn titles
PEER_TITLE_MAP = {
    "data engineer": ["Data Engineer", "Analytics Engineer", "DataOps"],
    "analytics engineer": ["Analytics Engineer", "Data Engineer", "dbt"],
    "ml engineer": ["ML Engineer", "MLOps", "Machine Learning Engineer"],
    "machine learning": ["Machine Learning Engineer", "ML Engineer", "MLOps"],
    "data scientist": ["Data Scientist", "ML Engineer", "Research Scientist"],
    "data analyst": ["Data Analyst", "Analytics Engineer", "Business Analyst"],
    "software engineer": ["Software Engineer", "Backend Engineer", "Full Stack Engineer"],
    "backend engineer": ["Backend Engineer", "Software Engineer", "Platform Engineer"],
    "frontend engineer": ["Frontend Engineer", "UI Engineer", "Full Stack Engineer"],
    "devops": ["DevOps Engineer", "Platform Engineer", "SRE"],
    "platform engineer": ["Platform Engineer", "DevOps Engineer", "Infrastructure Engineer"],
}

MANAGER_TITLES = '"Head of Data" OR "Director" OR "Engineering Manager" OR "VP of Engineering" OR "VP Engineering"'
RECRUITER_TITLES = '"Recruiter" OR "Talent Acquisition" OR "Technical Recruiter"'


def _infer_peer_titles(job_title: str) -> str:
    lower = job_title.lower()
    for keyword, titles in PEER_TITLE_MAP.items():
        if keyword in lower:
            return " OR ".join(f'"{t}"' for t in titles)
    # Fallback: use the job title itself
    return f'"{job_title}"'


def get_search_links(company: str, job_title: str) -> list[dict]:
    company_q = f'"{company}"'

    links = [
        {
            "label": "Hiring Managers",
            "type": "managers",
            "url": "https://www.google.com/search?" + urlencode({
                "q": f"site:linkedin.com/in {company_q} {MANAGER_TITLES}"
            }),
        },
        {
            "label": "Team Members",
            "type": "peers",
            "url": "https://www.google.com/search?" + urlencode({
                "q": f"site:linkedin.com/in {company_q} {_infer_peer_titles(job_title)}"
            }),
        },
        {
            "label": "Recruiters",
            "type": "recruiters",
            "url": "https://www.google.com/search?" + urlencode({
                "q": f"site:linkedin.com/in {company_q} {RECRUITER_TITLES}"
            }),
        },
    ]
    return links

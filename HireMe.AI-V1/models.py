from pydantic import BaseModel
from typing import List, Dict, Optional

class WorkItem(BaseModel):
    job_title: str
    company: str
    start_date: str
    end_date: str
    bullets: List[str] = []

class EducationItem(BaseModel):
    degree: str
    school: str
    start_date: str
    end_date: str
    details: List[str] = []

class ProjectItem(BaseModel):
    project_name: str
    bullets: List[str] = []

class CertificationItem(BaseModel):
    name: str

class AwardItem(BaseModel):
    title: str
    year: str
    description: str = ""

class Contact(BaseModel):
    email: str
    phone: str
    website: str = ""

class CoverLetterPreferences(BaseModel):
    recipient_name: str = "Hiring Manager"
    opening_style: str = "professional"   # optional control
    tone: str = "confident"
    length: str = "medium"

class CandidateProfile(BaseModel):
    name: str
    contact: Contact
    summary: str = ""

    work_experience: List[WorkItem] = []
    education: List[EducationItem] = []

    skills: Dict[str, List[str]] = {
        "technical": [],
        "tools": [],
        "soft_skills": []
    }

    projects: List[ProjectItem] = []
    certifications: List[CertificationItem] = []
    awards_and_achievements: List[AwardItem] = []

    cover_letter_preferences: CoverLetterPreferences = CoverLetterPreferences()

class JobPosting(BaseModel):
    job_title: str = ""
    company_name: str = ""
    job_description: str

import sys
import json
from pathlib import Path

# Absolute paths based on this script's location
root_dir = Path(__file__).parent
backend_dir = root_dir / 'backend'
sys.path.insert(0, str(backend_dir))

from app.utils.docx_reader import read_docx
from app.services.jd_parser import JDParser

def parse_challenge_jd(file_path: Path):
    print(f"Reading {file_path}...")
    raw_text = read_docx(str(file_path))
    
    if not raw_text:
        print("Failed to read docx or file is empty.")
        return
        
    print(f"Loaded {len(raw_text)} characters. Initializing AI Parser...")
    parser = JDParser()
    
    print("Parsing structural requirements...")
    parsed = parser.parse(raw_text)
    
    # Check for production ML requirements heuristically
    prod_ml = False
    ml_skills = {"docker", "kubernetes", "mlops", "mlflow", "deployment", "aws", "gcp", "azure", "production"}
    for skill in parsed.all_skill_names:
        if skill.lower() in ml_skills:
            prod_ml = True
            break
            
    if "production" in raw_text.lower() and "machine learning" in raw_text.lower():
        prod_ml = True
    
    # Map to the exact schema requested by the user
    jd_requirements = {
        "must_have_skills": parsed.must_have_skill_names,
        "nice_to_have_skills": parsed.nice_to_have_skill_names,
        "preferred_skills": parsed.nice_to_have_skill_names,  # alias
        "required_experience_min": parsed.experience.minimum,
        "required_experience_max": parsed.experience.maximum,
        "required_industries": parsed.required_industries,
        "seniority_level": parsed.seniority.value,
        "leadership_requirements": {
            "requires_management": parsed.leadership_signals.requires_management,
            "technical_lead": parsed.leadership_signals.technical_lead,
            "signals": parsed.leadership_signals.signals_found
        },
        "startup_requirements": {
            "is_startup": parsed.startup_signals.is_startup,
            "fast_paced": parsed.startup_signals.fast_paced_mentioned,
            "signals": parsed.startup_signals.signals_found
        },
        "production_ml_requirements": prod_ml,
        "negative_signals": [ns.signal for ns in parsed.negative_signals],
        "location_requirements": {
            "city": parsed.preferred_location.city,
            "country": parsed.preferred_location.country
        },
        "work_mode_requirements": parsed.work_mode.value
    }
    
    out_path = root_dir / "jd_requirements_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(jd_requirements, f, indent=2)
        
    print(f"Successfully exported JDRequirements object to {out_path}!")
    
if __name__ == "__main__":
    target_docx = root_dir / "job_description.docx"
    parse_challenge_jd(target_docx)

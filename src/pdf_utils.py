import base64
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent.parent / "Documents"

QUESTIONNAIRE_KEYWORDS = {"questionnaire", "form", "intake"}

def get_patient_names() -> list[str]:
    if not DOCUMENTS_DIR.exists():
        return []
    return sorted(
        d.name for d in DOCUMENTS_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.pdf"))
    )

def classify_document(path: Path) -> str:
    name = path.stem.lower()
    if any(kw in name for kw in QUESTIONNAIRE_KEYWORDS):
        return "questionnaire"
    return "medical"

def get_patient_documents(patient_name: str) -> dict:
    folder = DOCUMENTS_DIR / patient_name
    if not folder.exists():
        return {"questionnaire": None, "medical": []}

    questionnaire = None
    medical = []

    for pdf in sorted(folder.glob("*.pdf")):
        if classify_document(pdf) == "questionnaire":
            questionnaire = pdf
        else:
            medical.append(pdf)

    return {"questionnaire": questionnaire, "medical": medical}

def pdf_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")
import base64
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent.parent / "Documents"


def get_patient_files() -> dict[str, Path]:
    patients = {}
    if not DOCUMENTS_DIR.exists():
        return patients
    for pdf in sorted(DOCUMENTS_DIR.rglob("*.pdf")):
        label = f"{pdf.parent.name} — {pdf.stem}"
        patients[label] = pdf
    return patients


def pdf_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")
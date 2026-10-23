import os, shutil, subprocess, tempfile, threading
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

MAX_BYTES = 25 * 1024 * 1024
MIME = {"pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

# Anything LibreOffice can open becomes a PDF with the real layout engine.
OFFICE_IN = {"doc", "docx", "odt", "rtf", "txt",          # documents
             "ppt", "pptx", "odp",                        # slides
             "xls", "xlsx", "ods", "csv"}                 # spreadsheets

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
                   allow_methods=["POST", "GET"], allow_headers=["*"])
# LibreOffice is heavy; Render's free plan only has 512 MB, so default to 1 job at a time.
slots = threading.Semaphore(int(os.getenv("MAX_JOBS", "1")))


def run(cmd, timeout=120, env=None):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors="ignore")[-300:])


def office_to_pdf(src: Path, work: Path) -> Path:
    # Fresh profile + HOME per job so parallel/previous runs never clash or hang.
    env = {**os.environ, "HOME": str(work)}
    run(["soffice", f"-env:UserInstallation=file://{work}/lo-profile", "--headless",
         "--norestore", "--convert-to", "pdf", "--outdir", str(work), str(src)], env=env)
    out = work / (src.stem + ".pdf")
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("LibreOffice produced no output (file may be corrupt or password-protected)")
    return out


def pdf_to_docx(src: Path, work: Path) -> Path:
    import fitz  # PyMuPDF, installed with pdf2docx
    with fitz.open(src) as doc:
        scanned = not any(p.get_text().strip() for p in doc)
    if scanned:  # image-only PDF: add a text layer first
        ocr = work / "ocr.pdf"
        run(["ocrmypdf", "--skip-text", "--deskew", str(src), str(ocr)], timeout=240)
        src = ocr
    from pdf2docx import Converter
    out = work / (src.stem + ".docx")
    cv = Converter(str(src))
    try:
        cv.convert(str(out))
    finally:
        cv.close()
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/convert")
def convert(to: str, file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if to == "pdf" and ext in OFFICE_IN:
        job = office_to_pdf
    elif to == "docx" and ext == "pdf":
        job = pdf_to_docx
    else:
        raise HTTPException(400, f".{ext or '?'} -> .{to} is not supported")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (25 MB max)")

    work = Path(tempfile.mkdtemp(prefix="job-"))
    src = work / f"in.{ext}"
    src.write_bytes(data)
    try:
        with slots:
            out = job(src, work)
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(500, f"Conversion failed: {e}")
    # Result is streamed back, then the whole job folder is deleted.
    return FileResponse(out, media_type=MIME[to],
                        background=BackgroundTask(shutil.rmtree, work, ignore_errors=True))

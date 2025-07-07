from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
import shutil, os, requests, json
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# --- Config ---
COLAB_URL = "https://9c5f-34-145-65-140.ngrok-free.app/process"  # Replace with your actual Colab endpoint
UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- App Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
frontend = Jinja2Templates(directory="frontend")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return frontend.TemplateResponse("index.html", {"request": {}})


# --- Main Route ---
@app.post("/process")
async def process(
    files: List[UploadFile] = File(...),
    fields: str = Form(...)
):
    parsed_fields = json.loads(fields)
    field_list = [f.replace("_", " ").title() for f in parsed_fields]
    prompt = f"Extract the following fields from the invoice: {', '.join(field_list)}."

    results = []
    os.makedirs("temp", exist_ok=True)

    for file in files:
        temp_path = f"temp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with open(temp_path, "rb") as f:
            try:
                response = requests.post(
                    COLAB_URL,
                    files={"file": f},
                    data={"prompt": prompt},
                    timeout=60
                )
                response.raise_for_status()
                result_data = response.json()
            except Exception as e:
                result_data = {
                    "fileName": file.filename,
                    "error": str(e),
                    "promptUsed": prompt
                }

        os.remove(temp_path)
        results.append(result_data)

    return JSONResponse(content=results)


from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import uvicorn, nest_asyncio

app = FastAPI()

@app.post("/process")
async def process(file: UploadFile = File(...), prompt: str = Form(...)):
    contents = await file.read()

    # Replace with your actual model inference logic
    return {
        "fileName": file.filename,
        "promptUsed": prompt,
        "extractedFields": {
            "vendor_name": "XYZ Corp",
            "invoice_number": "INV-2024-001",
            "total_amount": "149.50"
        },
        "rawResponse": {"status": "mocked"}
    }

# Expose with ngrok
public_url = ngrok.connect(8000) # type: ignore
print("🔗 Your public Colab endpoint:", public_url)

nest_asyncio.apply()
uvicorn.run(app, port=8000)
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

COLAB_TEST_URL = "https://484c-34-106-104-79.ngrok-free.app/test-prompt"  # 👈 Replace this with Colab URL

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/send-message")
def send_message(prompt: str = Form(...)):
    try:
        res = requests.post(COLAB_TEST_URL, data={"prompt": prompt})
        return res.json()
    except Exception as e:
        return {"error": str(e)}

import requests

from fastapi.responses import HTMLResponse

@app.get("/test-prompt", response_class=HTMLResponse)
def form():
    return """
        <form action="/send-message" method="post">
            <input name="prompt" value="Hello Colab">
            <button type="submit">Send</button>
        </form>
    """

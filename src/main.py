from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from src.agent import answer_question

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask", response_class=PlainTextResponse)
def ask(request: QuestionRequest) -> str:
    return answer_question(request.question)
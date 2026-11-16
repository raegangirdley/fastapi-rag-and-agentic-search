from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from agent import answer_question

EMBEDDING_MODEL = "nomic-embed-text"

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask", response_class=PlainTextResponse)
def ask(request: QuestionRequest) -> str:
    return answer_question(request.question)
import ollama

EMBEDDING_MODEL = "nomic-embed-text"
LANGUAGE_MODEL = "llama3.1:8b"

def embed_text(text: str) -> list[float]:
    response = ollama.embed(model=EMBEDDING_MODEL, input=text)
    return response["embeddings"][0]

def call_model(messages, tools):
    response = ollama.chat(
        model=LANGUAGE_MODEL,
        messages=messages,
        tools=tools
    )
    return response

response = call_model(
    messages=[
        {
            'role': 'user',
            'content': 'Explain how an API works in two short sentences.',
        },
    ],
    tools=[]
)

print(response['message']['content'])
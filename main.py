import ollama

def call_model(messages, tools):
    response = ollama.chat(
        model='llama3.1:8b',
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
from fastapi import FastAPI
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from sentences import generate_sentence  # Import the function


app = FastAPI()
# Add this after creating the FastAPI app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
client = OpenAI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/sentence")
async def get_sentence():

    messageData = generate_sentence()

    return messageData


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


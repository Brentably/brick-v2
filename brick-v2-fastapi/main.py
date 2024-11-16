from fastapi import FastAPI
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware


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

    completion = client.chat.completions.create(
        model="o1-mini",
        messages=[
            {
                "role": "user",
                "content": "Give a simple sentence in German. Don't say anything else, just the German part."
            }
        ]
    )

    print(completion.choices[0].message)
    return completion.choices[0].message


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


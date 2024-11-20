import json
from fastapi import FastAPI, Body
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from sentences import MessageData, generate_sentence  # Import the function


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

@app.post('/sentence_result')
def sentence_result(body: dict = Body(...)):
    sentence_data = MessageData(**body["sentenceData"])
    user_translation:str = body["userTranslation"]
    is_correct: bool = body["isCorrect"]
    print("Received sentence data:", body)
    
    print(sentence_data)
    
    flattened_root_words = [root_word for item in sentence_data.data for root_word in item.root_words]
    
    with open("db.json", "r+") as db_file:
        db_data = json.load(db_file)
        user_data = db_data.get("user", {})
        words_data = user_data.get("words", [])
        
        for token in sentence_data.data:
            root_words = token.root_words
            for root_word in root_words:
                if root_word in words_data:
                    words_data[root_word]["total_attempts"] += 1
                    if is_correct:
                        words_data[root_word]["correct_attempts"] += 1
                    words_data[root_word]["proficiency"] = words_data[root_word]["correct_attempts"] / words_data[root_word]["total_attempts"]
                else:
                    words_data[root_word] = {
                        "correct_attempts": 1 if is_correct else 0,
                        "total_attempts": 1,
                        "proficiency": 1 if is_correct else 0,
                    }
                    
        
        # Write the updated data back to the file
        db_file.seek(0)
        json.dump(db_data, db_file, indent=4)
        db_file.truncate()
    
    # Process your data here
    
    return {"message": "Data received successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


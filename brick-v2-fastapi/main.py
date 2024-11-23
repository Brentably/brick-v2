import json
from fastapi import FastAPI, Body
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentences import MessageData, ResultMessageData, generate_sentence  # Import the function
from cards import calc_total_proficiency
from fsrs import Card, Rating, FSRS

fsrs = FSRS()

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

class SentenceResult(BaseModel):
    sentence_data: ResultMessageData
    user_translation: str
    is_correct: bool
    english_translation: str

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/sentence")
async def get_sentence():

    messageData = generate_sentence()

    return messageData


@app.get("/proficiency")
async def get_proficiency():
    proficiency = calc_total_proficiency()
    return {"proficiency": proficiency}

def store_sentence_result(sentence_result: SentenceResult):
    # Load or create sentence results history
    try:
        with open("sentence_results.json", "r") as f:
            sentence_results = json.load(f)
    except FileNotFoundError:
        # Create initial file structure if it doesn't exist
        sentence_results = []
        with open("sentence_results.json", "w") as f:
            json.dump(sentence_results, f, indent=4)
            
    try:
        with open("incorrect_sentence_results.json", "r") as f:
            incorrect_results = json.load(f)
    except FileNotFoundError:
        incorrect_results = []
        with open("incorrect_sentence_results.json", "w") as f:
            json.dump(incorrect_results, f, indent=4)
    
    # Create result object
    result = {
        "sentence": sentence_result.sentence_data.message,
        "clicked_words": [token.token for token in sentence_result.sentence_data.data if token.isClicked],
        "english_translation": sentence_result.english_translation,
        "user_translation": sentence_result.user_translation,
        "is_correct": sentence_result.is_correct,
    }

    # Add to all results
    sentence_results.append(result)
    
    # If incorrect, also add to incorrect results
    if not sentence_result.is_correct:
        incorrect_results.append(result)

    # Save updated results to both files
    with open("sentence_results.json", "w") as f:
        json.dump(sentence_results, f, indent=4)
        
    with open("incorrect_sentence_results.json", "w") as f:
        json.dump(incorrect_results, f, indent=4)

@app.post('/sentence_result')
def sentence_result(body: dict = Body(...)):
    sentence_data = ResultMessageData(**body["sentenceData"])
    user_translation:str = body["userTranslation"]
    is_correct: bool = body["isCorrect"]
    english_translation: str = body["englishTranslation"]
    
    sentence_result = SentenceResult(sentence_data=sentence_data, user_translation=user_translation, is_correct=is_correct, english_translation=english_translation)
    store_sentence_result(sentence_result)
    
    print("Received sentence data:", body)
    
    print(sentence_data)
    
    flattened_root_words = [root_word for item in sentence_data.data for root_word in item.root_words]
    not_clicked_tokens_count = sum(1 for token in sentence_data.data if not token.isClicked)
    print(f"Number of tokens not clicked: {not_clicked_tokens_count}")
    not_clicked_token_weight = 1 / not_clicked_tokens_count
    print(f"not_clicked_token_weight: {not_clicked_token_weight}")
    with open("db.json", "r+") as db_file:
        db_data = json.load(db_file)
        user_data = db_data.get("user", {})
        words_data = user_data.get("words", [])
        
        for token in sentence_data.data:
            root_words = token.root_words
            for root_word in root_words:
                if root_word in words_data:
                    print(f"root_word: {root_word} in words_data")
                    card = Card.from_dict(words_data[root_word])
                else:
                    print(f"root_word: {root_word} not in words_data, creating new card")
                    card = Card()
                    
                if token.isClicked:
                    card, _ = fsrs.review_card(card, Rating.Again)
                elif is_correct and not token.isClicked:
                    card, _ = fsrs.review_card(card, Rating.Good, weight=not_clicked_token_weight)
                elif not is_correct:
                    card, _ = fsrs.review_card(card, Rating.Again, weight=not_clicked_token_weight)
                else:
                    raise Exception("Unknown case")
                
                words_data[root_word] = card.to_dict()

        # Write the updated data back to the file
        db_file.seek(0)
        json.dump(db_data, db_file, indent=4)
        db_file.truncate()
    
    # Process your data here
    
    return {"message": "Data received successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


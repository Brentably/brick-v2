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
    word_validations: dict[str, bool]
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
            

    # Create result object
    result = {
        "sentence": sentence_result.sentence_data.message,
        "clicked_words": [token.token for token in sentence_result.sentence_data.data if token.isClicked],
        "focus_words": sentence_result.sentence_data.focus_words,
        "english_translation": sentence_result.english_translation,
        "user_translation": sentence_result.user_translation,
        "word_validations": sentence_result.word_validations,
    }

    # Add to all results
    sentence_results.append(result)
    
    # Save updated results to both files
    with open("sentence_results.json", "w") as f:
        json.dump(sentence_results, f, indent=4)
        


@app.post('/sentence_result')
def sentence_result(body: dict = Body(...)):
    sentence_data = ResultMessageData(**body["sentenceData"])
    user_translation:str = body["userTranslation"]
    word_validations: dict[str, bool] = body["wordValidations"]
    english_translation: str = body["englishTranslation"]
    
    sentence_result = SentenceResult(sentence_data=sentence_data, user_translation=user_translation, word_validations=word_validations, english_translation=english_translation)
    store_sentence_result(sentence_result)
    
    print("Received sentence data:", body)
    
    print(sentence_data)
    
    
    # not_clicked_tokens_count = sum(1 for token in sentence_data.data if not token.isClicked)
    # print(f"Number of tokens not clicked: {not_clicked_tokens_count}")
    # not_clicked_token_weight = 1 / not_clicked_tokens_count
    # print(f"not_clicked_token_weight: {not_clicked_token_weight}")\
    
    with open("db.json", "r+") as db_file:
        db_data = json.load(db_file)
        user_data = db_data.get("user", {})
        words_data = user_data.get("words", [])
        
        for word, is_correct in sentence_result.word_validations.items():
            if word in words_data:
                card = Card.from_dict(words_data[word])
            else:
                card = Card()

            if is_correct:
                card, _ = fsrs.review_card(card, Rating.Good)
                print(f"Reviewed card for {word} with rating Good")
            else:
                card, _ = fsrs.review_card(card, Rating.Again)
                print(f"Reviewed card for {word} with rating Again")
            
                
            words_data[word] = card.to_dict()

        # Write the updated data back to the file
        db_file.seek(0)
        json.dump(db_data, db_file, indent=4)
        db_file.truncate()
    
    # Process your data here
    
    return {"message": "Data received successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


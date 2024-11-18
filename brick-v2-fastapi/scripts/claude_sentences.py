import json
import random
from pprint import pprint
from typing import TypedDict 

import openai
import spacy
from pydantic import BaseModel
from spacy import tokens
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')



# must use build constraint when install spacy
# must install numpy<2
def create_system_prompt(focus_word: str, language: str = 'German') -> str:
    wordList = load_word_list()
    wordList = '\n'.join(wordList)
    return f"""
    You are an expert in the {language} language. You are creative, playful, witty. Your job is to help the learner learn by generating whimsical practice sentences that meet the specified requirements. You will be given a word list, and asked to only generate 
    Only use words based on the following word list: 
    {wordList}

    It can be different versions of each of these words, including different case, plurality, gender, or conjugation.
    For instance, "das" or "dem" would count as a version of "der". 
    If "Sie" is on the list, you could use "Ihnen".
    If "sein" is on the list, you could use "bin" or "ist".
    If "Berg" is on the list, you could use "Bergen".
    If "Haus" is on the list, you could use "Hause".
    If "verstecken" is on the list, you could use "Verstecke".
    If "essen" is on the list, you could use "aß".
    If "unterer" is on the list, you could use "untere".
    If "nächster" is on the list, you could use "nächste".
    If "dieser" is on the list, you could use "dies".
    

    But *ONLY* use words and versions of words from this list. DO NOT use any other words. Let me reiterate, do NOT, use any other words.
    
    Additionally, your main requirement is to use the following word: {focus_word}. Create a great example sentence with this focus word in context in order for the user to get a good grasp on how it might be used.
    You are a native speaker, and you actually don't know English. Make sure that your <answer> always contains only German.
    
    Before you reply, consider the word list and how you might structure your reply given your limited vocabulary. Write out this thinking within <thinking> tags.
    Always reply in this XML format:
    ```
    <thinking></thinking>
    <answer></answer>
    ```
    """




# Constants and Configuration
GERMAN_MODEL = 'de_dep_news_trf'
WORD_DATA_FILE = '5009_word_and_scraped_cd.json'
LOOKUP_TABLE_FILE = './5009_cd_to_word_lookup.json'

# Data Models
class TokenizeRequest(BaseModel):
    input_str: str
    language: str
    
class ValidationResult(TypedDict, total=False):
    is_valid: bool
    reason: str  # Optional because total=False
    invalid_words: list[str]  # Optional because total=False

# Initialize clients and models
client = openai.OpenAI()
nlp_de = spacy.load(GERMAN_MODEL)

# Data loading functions
def load_word_list():
    with open(WORD_DATA_FILE) as f:
        data = json.load(f)
    return [word_obj['word'] for word_obj in data][:2000]

def load_lookup_table():
    with open(LOOKUP_TABLE_FILE, "r") as file:
        return json.load(file)
lookup_table: dict[str, list[str]] = load_lookup_table()

# Helper functions
# Get all potential roots from the look up table based on the list of tokens
def get_roots(token: tokens.Token) -> list[str]:
    text = token.text
    if text.startswith("Lieblings"):
        text = text[len("Lieblings"):]
        
    final = []
    if text in lookup_table:
        final.extend(lookup_table[text])
        
    if text.lower() in lookup_table:
        final.extend(lookup_table[text.lower()])
        
    if len(final) == 0:
        # raise Exception(f"{token.text} not in lookup table")
        print(f"{token.text} not in lookup table")
    
    return list(set(final))
  
  

#goal here is to do whaever logic we need to do for getting claude's actual answer (not COT or w/e)
def process_claude_response(resp: str):
    # Extract text between <answer> tags using string manipulation
    # Could use XML parser but response is simple enough that string search is sufficient
    start_tag = "<answer>"
    end_tag = "</answer>"
    
    start_idx = resp.find(start_tag)
    if start_idx == -1:
        raise ValueError("Could not find opening <answer> tag in Claude response")
        
    end_idx = resp.find(end_tag)
    
    # If no end tag found, use entire remaining string after start tag
    if end_idx == -1:
        answer = resp[start_idx + len(start_tag):].strip()
    else:
        answer = resp[start_idx + len(start_tag):end_idx].strip()
    
    return answer
  

# process a normal message => split it into tokens and determine what root words it traces back to.
def find_root_words(body: TokenizeRequest): 
    input_str, language = body.input_str, body.language
    if language == 'German':
        nlp = nlp_de
    else:
        raise ValueError("language not allowed")
    doc = nlp(input_str)

    tokens_list: list[dict] = []
    # idx is used as a unique identifier for words. 
    # svp's will have one unique identifier. 
    # punctuation/other non-word tokens will have None/null id value.

    # pprint(doc.to_json())
    for token in doc:
        # if it's compound, give it the same id as its root
        # compound verbs will link to the same id, for instance stehe and auf will both have the id of stehe
        # if token.dep_ == "compound:prt":
        is_svp = False
        if token.dep_ == "svp":
            is_svp = True
            id = token.head.idx
            root_words = [token.text + lemma for lemma in get_roots(token.head)]
            # print(f"spv lemmas: {root_words}")
            # set token head's lemmas to lemmas of current (spv) token
            for t in tokens_list:
                # should only match tokens head
                if t['id'] == id:
                    t['root_words'] = root_words
                    t['is_svp'] = True
            
        elif token.dep_ != 'punct' and token.pos_ != 'PUNCT' and token.pos_ != 'SPACE':
            id = token.idx
            root_words = get_roots(token) 
        # tokens w/ no id value are punctuation
        else: 
            id = None
            root_words = []
        
        tokens_list.append({
            "token": token.text,
            "token_ws": token.whitespace_,
            "id": id,
            "root_words": root_words,
            "is_svp": is_svp
        })
  
    # pprint(tokens_list)
    return {"tokens": tokens_list}

def validate_message(root_words: list[list[str]], focus_word: str, words_list: list[str]) -> ValidationResult:
    # Validate that at least one of the random words is used
    found = any(focus_word in root_word_list for root_word_list in root_words)
    if not found:
        return {"is_valid": False, "reason": "focus_word missing"}

    # Validate that all root words are in the words list

    for root_word_list in root_words:
        if not root_word_list:
            continue
        words_not_in_list = [word for word in root_word_list if word not in words_list]
    if words_not_in_list:
        return {"is_valid": False, "reason": "words not on word_list found", "invalid_words": words_not_in_list}
      
    return {"is_valid": True}


def generate_with_retries(words_list, focus_word, max_tries=5, attempts=0, messages=None) -> tuple[str, dict[str, list[dict]]]:
  from rich import print
  print(f"[red]Attempt #{attempts} to generate valid sentence...[/red]")
  
  if attempts >= max_tries:
    raise Exception(f"Failed to generate valid sentence after {max_tries} attempts")

  if messages is None:
    messages = [
            {"role": "user", "content": f"Generate a sentence using only words from the list and the focus word: {focus_word}."}
        ]
  message_block = anthropic.Anthropic(api_key=CLAUDE_API_KEY).messages.create(
      model="claude-3-5-sonnet-20241022",
      max_tokens=1024,
      system=create_system_prompt(focus_word=focus_word),
      messages=messages
  )
  
  preprocessed_message = message_block.content[0].text
  
  messages.append({"role": "assistant", "content": preprocessed_message})
  
  # print("pre-processed message:\n")
  # print(preprocessed_message)
  
  message = process_claude_response(preprocessed_message)

  pprint("message:\n")
  pprint(message)

  # Process and validate the generated message
  data = find_root_words(TokenizeRequest(input_str=message, language="German"))
  root_words = [token['root_words'] for token in data['tokens']]
  
  pprint('root words:')
  print(root_words)

  result = validate_message(root_words, focus_word, words_list)
  
  if result["is_valid"]:
    return [message, data]
  else:
    if result["reason"] == "words not on word_list found":
        messages.append({"role": "user", "content": f"Unfortunately, you used: {result['invalid_words']} which are not on the list"})
    generate_with_retries(words_list=words_list, focus_word=focus_word, attempts=attempts+1, messages=messages)

def main():
    # Load data
    words_list = load_word_list()
    focus_word = random.choice(words_list)
    print(focus_word)
    
    # Generate sentence using OpenAI
    [message, data] = generate_with_retries(words_list, focus_word)
    



if __name__ == "__main__":
    main()
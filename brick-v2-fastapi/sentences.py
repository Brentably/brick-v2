from datetime import datetime, timezone
import json
import random
from pprint import pprint
from typing import Any, Optional, TypedDict 
from rich import print
import openai
import spacy
from pydantic import BaseModel
from spacy import tokens
import os
from dotenv import load_dotenv
import anthropic
from fsrs import Card, FSRS
fsrs = FSRS()

load_dotenv()
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')



# must use build constraint when install spacy
# must install numpy<2
def create_system_prompt(focus_word: str, word_list: str, language: str = 'German') -> str:

    wordList = '\n'.join(word_list)
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
    
    Additionally, your main requirement is to use the focus word specified. Create a great example sentence with this focus word in context in order for the user to get a good grasp on how it might be used.
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

class TokenInfo(BaseModel):
    token: str
    token_ws: str
    id: Optional[int]
    root_words: list[str]
    is_svp: bool
    full_svp_word: Optional[str]
    
class ResultTokenInfo(TokenInfo):
    isClicked: Optional[bool] = False
    translationLoading: Optional[bool] = False
    translationInContext: Optional[str] = None
    

class MessageData(BaseModel):
    message: str
    data: list[TokenInfo]
    
class ResultMessageData(MessageData):
    message: str
    data: list[ResultTokenInfo]

class ValidationResult(BaseModel):
    is_valid: bool
    reason: Optional[str] = None  # Now using Optional for clarity
    invalid_words: Optional[list[TokenInfo]] = None
    messageData: Optional[MessageData] = None

# Initialize clients and models
client = openai.OpenAI()
nlp_de = spacy.load(GERMAN_MODEL)

# Data loading functions
def load_full_word_list():
    with open(WORD_DATA_FILE) as f:
        data = json.load(f)
    return [word_obj['word'] for word_obj in data]

full_word_list: list[str] = load_full_word_list()



# currently all allowed words are in all tracked words (rounded down to nearest 25 to save on tokens)
# ideally in the future, we'd only allow words that they know well
def load_allowed_word_list():
    with open("db.json", "r") as db_file:
        db_data = json.load(db_file)
        num_words = len(db_data["user"]["words"])
        # Round down to nearest 25
        rounded_num = 25 * (num_words // 25)
        # Get that many words from full word list
        return full_word_list[:rounded_num]

def load_lookup_table():
    with open(LOOKUP_TABLE_FILE, "r") as file:
        return json.load(file)
full_lookup_table: dict[str, list[str]] = load_lookup_table()


def get_focus_word(): 
    with open("db.json", "r") as db_file:
        db_data = json.load(db_file)
        words_data = db_data.get("user", {}).get("words", {})
        # Sort words by due
        sorted_words = sorted(words_data.items(), key=lambda x: x[1]['due'])
        
        print('sorted words')
        print(sorted_words[:10])
        
        # Choose the word with the soonest due date
        if datetime.fromisoformat(sorted_words[0][1]["due"]) < datetime.now(timezone.utc):
            return sorted_words[0][0]
        else:
            # or the next word in the full list
            for word in full_word_list:
                if word not in words_data:
                    return word
            raise Exception('couldnt find focus word')
            
    
        
    

# Helper functions
# Get all potential roots from the look up table based on the list of tokens
def get_roots(token: tokens.Token) -> list[str]:
    text = token.text
    if text.startswith("Lieblings"):
        text = text[len("Lieblings"):]
        
    final = []
    if text in full_lookup_table:
        final.extend(full_lookup_table[text])
        
    if text.lower() in full_lookup_table:
        final.extend(full_lookup_table[text.lower()])
        
    if text.capitalize() in full_lookup_table:
        final.extend(full_lookup_table[text.capitalize()])
        
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
        raise ValueError(f"Could not find opening <answer> tag in Claude response: \n {resp}")
        
    end_idx = resp.find(end_tag)
    
    # If no end tag found, use entire remaining string after start tag
    if end_idx == -1:
        answer = resp[start_idx + len(start_tag):].strip()
    else:
        answer = resp[start_idx + len(start_tag):end_idx].strip()
    
    return answer
  

# process a normal message => split it into tokens and determine what root words it traces back to.
def analyze_and_add_roots(input_str, language): 
    if language == 'German':
        nlp = nlp_de
    else:
        raise ValueError("language not allowed")
    doc = nlp(input_str)

    tokens_list: list[TokenInfo] = []
    # idx is used as a unique identifier for words. 
    # svp's will have one unique identifier. 
    # punctuation/other non-word tokens will have None/null id value.

    # pprint(doc.to_json())
    for token in doc:
        # if it's compound, give it the same id as its root
        # compound verbs will link to the same id, for instance stehe and auf will both have the id of stehe
        # if token.dep_ == "compound:prt":
        is_svp = False
        full_svp_word = None
        if token.dep_ == "svp":
            is_svp = True
            id = token.head.idx
            
            full_svp_word = token.text + token.head.text
            print(token)
            print(token.head)
            
            
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
            "is_svp": is_svp,
            "full_svp_word": full_svp_word if full_svp_word else None
        })
  
    # pprint(tokens_list)
    return tokens_list

def process_and_validate_message(preprocessed_message: str, focus_word: str, word_list: list[str]) -> ValidationResult:
    message = process_claude_response(preprocessed_message)

    pprint("message:\n")
    pprint(message)
    invalid_words: list[TokenInfo] = []
    # Process and validate the generated message
    tokens_list = analyze_and_add_roots(input_str=message, language="German")
    for token in tokens_list:
      # if token isn't punctuation
      if token["id"] is not None:
        # either there are no root words
        if len(token["root_words"]) == 0:
          print(f'couldnt identify roots for: {token["token"]}')
          invalid_words.append(token)
        else: 
          # make sure that some word in token["root_words"] is in the word_list, else add the token to invalid words
          if any(root_word in word_list for root_word in token["root_words"]):
            continue
          else:
            print(f'no root word of {token["token"]} found in word list')
            print(token)
            invalid_words.append(token)
    # print('data:\n')
    # pprint(tokens_list)
    
    root_words = [token["root_words"] for token in tokens_list]
    
    # pprint('root words:')
    # print(root_words)
    
    # Validate that all root words are in the words list
    # the below doesn't work because the
    if invalid_words:
        print("invalid words found: ")
        pprint(invalid_words)
        return ValidationResult(is_valid=False, reason="words not on word_list found", invalid_words=invalid_words)
    
    # Validate that at least one of the random words is used
    found = any(focus_word in root_word_list for root_word_list in root_words)
    if not found:
        return ValidationResult(is_valid=False, reason="focus_word missing")

      
    return ValidationResult(is_valid=True, messageData=MessageData(message=message, data=tokens_list))


def generate_with_retries(word_list, focus_word, max_tries=5, attempts=0, messages=None) -> MessageData:
  print(f"[red]Attempt #{attempts} to generate valid sentence...[/red]")
  
  if attempts >= max_tries:
    raise Exception(f"Failed to generate valid sentence after {max_tries} attempts")

  if messages is None:
    messages = [
            {"role": "user", 
             "content": [{
                "type": "text",
                "text": f"Generate a sentence using only words from the list and the focus word: {focus_word}.",
                "cache_control": {"type": "ephemeral"}
          }]}
        ]
    
  print("messages to claude: ")
  print(messages)
  message_block = anthropic.Anthropic(api_key=CLAUDE_API_KEY).beta.prompt_caching.messages.create(
      model="claude-3-5-sonnet-20241022", 
      max_tokens=1024,
      temperature=1,
      system=[{
        "text": create_system_prompt(focus_word=focus_word, word_list=word_list),
        "type": "text",
        "cache_control": {"type": "ephemeral"}
        }],
      messages=messages,
      extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
  )
  
#   print(message_block)
  
  # handle edge case
  if len(message_block.content) == 0:
    raise Exception(f"message_block has no content. See: {message_block}")
    # print("[red] message_block.content is None. see:  [/red]")
    # print(message_block)
    # return generate_with_retries(word_list=word_list, focus_word=focus_word, attempts=attempts+1, messages=messages)
  
  preprocessed_message = message_block.content[0].text
  
  messages.append({"role": "assistant", "content": preprocessed_message})
  
  # print("pre-processed message:\n")
  # print(preprocessed_message)
  


  result = process_and_validate_message(preprocessed_message, focus_word, word_list)
  
  if result.is_valid:
    return result.messageData
  else:
    if result.reason == "words not on word_list found":
        with open('invalid_word_counts.json', 'r+') as f:
          counts = json.loads(f.read() or '{}')
          counts.update({invalid_word.full_svp_word if invalid_word.is_svp else invalid_word.token: counts.get(invalid_word.full_svp_word if invalid_word.full_svp_word else invalid_word.token, 0) + 1 for invalid_word in result.invalid_words})
          f.seek(0); json.dump(counts, f, indent=2); f.truncate()
        add_svp_message = any(invalid_word.is_svp for invalid_word in result.invalid_words)
        messages.append({"role": "user", "content": f"Unfortunately, you used: {', '.join([invalid_word.full_svp_word if invalid_word.full_svp_word else invalid_word.token for invalid_word in result.invalid_words])} which are not on the list. {'If the word you were assigned is also a separable prefix, make sure to use it in a context that it is not a separable prefix.' if add_svp_message else ''} "})
    elif result.reason == "focus_word missing":
      messages.append({"role": "user", "content": f"Unfortunately, the focus word was missing. Make sure to use {focus_word} in the response!"})
    else:
      raise Exception(f"An unaccounted for reason occurred: {result.reason}")
    
    return generate_with_retries(word_list=word_list, focus_word=focus_word, attempts=attempts+1, messages=messages)

def generate_sentence():
    # Load data
    focus_word = get_focus_word()
    word_list = load_allowed_word_list()
    word_list.append(focus_word)
    print(focus_word)
    
    # Generate sentence using OpenAI
    messageData = generate_with_retries(word_list, focus_word)
    print("[blue]final message: [/blue]")
    print(messageData.message)
    return messageData

if __name__ == "__main__":
    generate_sentence()

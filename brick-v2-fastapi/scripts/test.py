import openai
from pydantic import BaseModel
from spacy import tokens
import json
from pprint import pprint 
import spacy
import random

# must use build constrainst when install spacy
# must install numpy<2

with open('5009_word_and_scraped_cd.json') as f:
    data = json.load(f)

class TokenizeRequest(BaseModel):
    input_str: str
    language: str

client = openai.OpenAI()

nlp_de = spacy.load('de_dep_news_trf')


def load_lookup_table():
    with open("./5009_cd_to_word_lookup.json", "r") as file:
        return json.load(file)

lookup_table: dict[str, list[str]] = load_lookup_table()

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

def process_message(body: TokenizeRequest): 
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
        
        tokens_list.append({"token": token.text, "token_ws": token.whitespace_, "id": id, "root_words": root_words, "is_svp": is_svp})
  
    # pprint(tokens_list)
    return {"tokens": tokens_list}


words_list = [word_obj['word'] for word_obj in data][:2000]

random_ten_words = random.sample(words_list, 10)




print(random_ten_words)



completion = client.chat.completions.create(
    model="o1-mini",
    messages=[
        {
            "role": "user",
            "content": (
                "Give a simple sentence in German. "
                "Use only words from this list: "
                "{}\n"
                "Additionally, incorporate one of the following 10 words: "
                "{}\n"
                "Don't say anything else, just the German part. Only use words from this list. Try to make it as vibrant as possible so that somebody might be able to tell what the words are from context. The sentence should be as long as possible and provide as much context as possible. That being said, it must make sense."
            ).format('\n'.join(words_list), ', '.join(random_ten_words))
        }
    ]
)

message = completion.choices[0].message.content

pprint(f"message: {message}")

data = process_message(TokenizeRequest(input_str=message, language="German"))

root_words:list[list[str]] = [token['root_words'] for token in data['tokens']]

pprint('root words:')
print(root_words)


root_words_flat = [item for sublist in root_words for item in sublist]
found = any(word in root_words_flat for word in random_ten_words)
if not found:
    raise Exception(f"None of the words in {random_ten_words} found in root words list.")



for root_word_list in root_words:
    if not root_word_list:
        continue
    found = any(root_word in words_list for root_word in root_word_list)
    if not found:
        raise Exception(f"None of the root words in {root_word_list} found in words list.")
import random
from fsrs import FSRS, Card, Rating, State
from datetime import datetime, timedelta, timezone
from sentences import load_full_word_list
import json

# HOW TO BUILD from FSRS:
# git clone py-fsrs whatever it is,
# cd py-fsrs
# pip install -e .
# and now you've built!

# Create FSRS instance
fsrs = FSRS()

def create_new_review_card_multiple_times(times=5):
    card = Card()
    review_date = datetime.now(timezone.utc)
    for _ in range(times):
        fuzzy_weight = random.uniform(0.5, 1.5)
        print(fuzzy_weight)
        card, rl = fsrs.review_card(card, Rating.Good, now=review_date, weight=fuzzy_weight)
        review_date = card.due + timedelta(days=1)
    return card


# a quick average of the estimated retrivability of all words
def calc_total_proficiency():
    proficiency_sum = 0
    due_cards_count = 0
    full_word_list = load_full_word_list()
    count = 0 
    for word in full_word_list:
        with open("db.json", "r") as db_file:
            db_data = json.load(db_file).get("user", {}).get("words", {})
            if word in db_data:
                count += 1
                card = Card.from_dict(db_data[word])
                retrivability = fsrs.approximate_retrievability(card)
                proficiency_sum += retrivability
                if card.due <= datetime.now(timezone.utc):
                    due_cards_count += 1
    print(f"count: {count} / {len(full_word_list)}")
    print(f"Due cards count: {due_cards_count}")
    return float((proficiency_sum / len(full_word_list)).real)
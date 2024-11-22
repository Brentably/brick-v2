from sre_parse import State
from fsrs import FSRS, Card, Rating

# HOW TO BUILD from FSRS:
# git clone py-fsrs whatever it is,
# cd py-fsrs
# pip install -e .
# and now you've built!

# Create FSRS instance
fsrs = FSRS()

card = Card(due=datetime.now(timezone.utc)+timedelta(days=365), state=State.Review)

from datetime import datetime, timedelta, timezone
print(datetime.now(timezone.utc))

print(card.due)
# Now you can use fsrs.review_card()
card, _ = fsrs.review_card(card, Rating.Good)

print(card.due)

card, _ = fsrs.review_card(card, Rating.Good, 0.15)
card2, _ = fsrs.review_card(card, Rating.Good, 0.15, datetime.now(timezone.utc) + timedelta(days=1))

print(card.due)
print(card2.due)

print(card.due)
print(card2.due)
# TODO: do some tests to see how this performs in some different scenarios
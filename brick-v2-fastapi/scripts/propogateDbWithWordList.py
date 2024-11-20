import json

# Load words from the word list file
with open("5009_word_and_scraped_cd.json", "r") as word_list_file:
    word_list = json.load(word_list_file)

# We only need the first 1000 words
words_to_add = word_list[:1000]

# Load the current database
with open("./db.json", "r+") as db_file:
    db_data = json.load(db_file)
    words_data = db_data.get("user", {}).get("words", {})

    # Add new words with correct_attempts: 1 and total_attempts: 1
    for word_entry in words_to_add:
        word = word_entry.get("word")
        if word and word not in words_data:
            words_data[word] = {
                "correct_attempts": 10,
                "total_attempts": 10,
                "proficiency": 1.0  # Assuming first attempt is always correct
            }

    # Update the database
    db_file.seek(0)
    json.dump(db_data, db_file, indent=4)
    db_file.truncate()


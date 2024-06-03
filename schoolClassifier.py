from fuzzywuzzy import fuzz

from data import UNIVERSITIES

"""
Function that returns a predicted school matching school and the similarity in percentage
"""
def classify_school(school):
    # Pre-Processing
    school = school.lower()
    school = school.replace("university of ", "")
    school = school.replace("university", "")
    school = school.strip()

    best_similarity = 0
    best_match = "none"

    for university in UNIVERSITIES:
        synonyms = UNIVERSITIES[university]     # Synonyms of university name
        synonyms.append(university)             # Full university name will be the last element in synonym list

        # Find the best match
        for synonym in synonyms:
            score = fuzz.ratio(school, synonym.lower())

            if score > best_similarity:
                best_match = synonyms[-1]
                best_similarity = score

    return best_match, best_similarity
"""
Function that generates tags as a list based on the schools and programs given
"""
def generate_tags(school, program):
    tags = []

    # SPECIAL CASES
    if program == 'cs/bba':
        tags = ['cs/bba', 'waterloo', 'laurier']

    elif program == 'dev degree':
        tags = ['dev degree', 'computer science', school]

    # Check if any special cases were used
    if not tags:
        tags.extend([program, school])

    return tags
"""
Docstring for src.miminions.utils.gen
"""
from faker import Faker

def generate_random_name(word_count: int = 2) -> str:
    """Generate a random name with the specified number of words."""
    fake = Faker()
    return '-'.join(fake.words(nb=word_count))

def generate_random_description(sentence_count: int = 3) -> str:
    """Generate a random description with the specified number of sentences."""
    fake = Faker()
    return ' '.join(fake.sentences(nb=sentence_count))
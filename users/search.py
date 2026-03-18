"""This file implements the user search algorithm"""

import math
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from Sodia.settings import DEBUG
from .models import User

from interactions.models import UserInfo

# +---------------------+
# | ALGORITHM OVERVIEW: |
# +---------------------+
#
# 1) go through all users and score each one on the query - user score is sum of word scores for all word on the query
# 2) for each word on the query, its score is the maximum score to get by matching with all user info fields
# 3) for each user info field, a query word is scored maximum of its match with every word on the field
#    or match of a sequence of words starting at that every possible position
# 4) after every user is given a score, apply softmax to the scores and return results with the highest probabilities
#

# +---------------------+
# | CONSTANTS (WIGHTS): |
# +---------------------+

MAX_TOKENS = 10  # max number of tokens in a query / user info field
MAX_TOKEN_LENGTH = 30

WORDS_SIMILARITY_EXPONENT = 5  # exponent power for the word similarity ratio
WORD_LENGTH_BONUS = 1.09  # exponent base for the bonus for matching a longer word

SENTENCE_LENGTH_BONUS = 1.5  # multiplier for a match of a sequence of words

# weights of user info fields:
USERNAME_WEIGHT = 10
DISPLAY_NAME_WEIGHT = 7
FULL_NAME_WEIGHT = 7
DESCRIPTION_WEIGHT = 3
HOUSE_WEIGHT = 5
BOARDING_TYPE_WEIGHT = 3
COUNTRY_NAME_WEIGHT = 2
COUNTRY_CODE_WEIGHT = 1
GENDER_WEIGHT = 1

USER_SCORE_EXPONENT = 1 / 2.5  # exponent power for the final user score
USER_SCORE_THRESHOLD = 1 / 3  # minimum score threshold value to include user in softmax calculation

MAX_RESULTS = 50

PROBABILITY_THRESHOLD = 1 / 20  # minimum probability threshold to include user in result


def parse(s: str) -> list[str]:
    """split a string into a list of tokens, where each token is of lowercase English letters, digits, or -_. chars.
    Tokens are at most MAX_TOKEN_LENGTH chars long, and the number of tokens is at most MAX_TOKENS"""
    # find all tokens using a regular expression
    return re.findall(fr"[\w.\-_]{{1,{MAX_TOKEN_LENGTH}}}", s.lower())[:MAX_TOKENS]


def score_words(word_1: str, word_2: str, /) -> float:
    """return a similarity score between two words (tokens)"""
    ratio = SequenceMatcher(None, word_1, word_2, autojunk=False).ratio()
    return ratio ** WORDS_SIMILARITY_EXPONENT * WORD_LENGTH_BONUS ** (min(len(word_1), len(word_2)) - 1)


@dataclass
class WordScore:
    """class to store a word and its score"""
    word: str
    score: float = 0


def score_on_string(query: list[WordScore], s: str, weight: int = 1):
    """give each word in the query a score based on how relevant (i.e. similar) it is to the string s.
    Given scores are multiplied by weight"""
    string = parse(s)  # split the string into tokens
    # precalculate and cache word similarity scores for each pair of words (expensive calculation)
    matrix = [
        [
            score_words(q.word, token)
            for q in query
        ]
        for token in string
    ]
    for q_start in range(len(query)):
        # for every word in the query
        for s_start in range(len(string)):
            # for every word in the string
            prefix_score = weight
            # for every possible length of a sequence stating at q_start and s_start
            for i in range(min(
                    len(query) - q_start,
                    len(string) - s_start
            )):
                prefix_score *= matrix[s_start + i][q_start + i]  # multiply score by how well words match
                # update max score for the starting query word
                query[q_start].score = max(query[q_start].score, prefix_score)
                prefix_score *= SENTENCE_LENGTH_BONUS  # multiply score by the length bonus


def score_user(user_info: UserInfo, query: list[str]) -> float:
    """give user a score based on a query"""
    # make WordScore objects to store max relevance scores for each word of the query
    q = [WordScore(word) for word in query]
    # score query on the available user info fields with different weights:
    score_on_string(q, user_info.username, USERNAME_WEIGHT)
    score_on_string(q, user_info.display_name, DISPLAY_NAME_WEIGHT)
    full_name = " ".join(filter(lambda x: x, [user_info.first_name, user_info.last_name]))
    if full_name: score_on_string(q, full_name, FULL_NAME_WEIGHT)
    if user_info.description: score_on_string(q, user_info.description, DESCRIPTION_WEIGHT)
    if user_info.house: score_on_string(q, user_info.house.name, HOUSE_WEIGHT)
    if user_info.boarding_type: score_on_string(q, user_info.boarding_type.name, BOARDING_TYPE_WEIGHT)
    if user_info.country:
        score_on_string(q, user_info.country.name, COUNTRY_NAME_WEIGHT)
        score_on_string(q, user_info.country.code, COUNTRY_CODE_WEIGHT)
    if user_info.gender: score_on_string(q, user_info.gender, GENDER_WEIGHT)

    # return the sum of all query words' scores (with score exponent applied)
    return sum([word.score for word in q]) ** USER_SCORE_EXPONENT


@dataclass
class UserScore:
    """class to store a user's info object, score, exponent value, and probability"""
    info: UserInfo
    score: float = None
    exp: float = None
    probability: float = None


def debug_output(score, query, mean):
    """output a result of scoring for debugging purposes"""
    print(f"{query}: {score.info.user}: {score.score:.2f} ({(100 * (score.probability - mean)):.2f}%)")
    return score.info


def search(query: str, requesting_user: User) -> list[UserInfo]:
    """search for users and return a list of their info objects"""
    if DEBUG and query == "*":
        # debug/testing feature active only when DEBUG=True
        # return all users if query is "*"
        return [user.info(requesting_user) for user in User.objects.activated().order_by("id")[:MAX_RESULTS]]

    parsed = parse(query)
    results = []
    max_score = 0
    for user in User.objects.activated():  # search through all activated users
        score = UserScore(user.info(requesting_user))  # make a UserScore record
        score.score = score_user(score.info, parsed)  # score the user
        if score.score < USER_SCORE_THRESHOLD:
            continue  # ignore user if score is under the threshold
        max_score = max(max_score, score.score)
        results.append(score)

    # softmax:
    total = 0
    for score in results:
        score.exp = math.exp(score.score - max_score)  # offset by -max_score to prevent overflow
        total += score.exp

    if not total:  # division by zero guard
        return []

    for score in results:
        score.probability = score.exp / total

    mean = 1 / len(results)  # mean probability

    return ([
        score.info  # return user info objects
        for score in sorted(
            filter(
                # filter out records below threshold relative to mean probability
                lambda x: x.probability - mean > PROBABILITY_THRESHOLD,
                results
            ),
            key=lambda x: x.probability,  # sort by probability
            reverse=True)  # descending
    ])[:MAX_RESULTS]  # limit to max results

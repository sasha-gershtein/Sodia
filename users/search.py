import math
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from .models import User

from interactions.models import UserInfo

MAX_TOKENS = 10

WORDS_SIMILARITY_EXPONENT = 5
WORD_LENGTH_BONUS = 1.09

SENTENCE_LENGTH_BONUS = 1.5

USERNAME_WEIGHT = 10
DISPLAY_NAME_WEIGHT = 7
FULL_NAME_WEIGHT = 7
DESCRIPTION_WEIGHT = 3
HOUSE_WEIGHT = 5
BOARDING_TYPE_WEIGHT = 3
COUNTRY_NAME_WEIGHT = 2
COUNTRY_CODE_WEIGHT = 1
GENDER_WEIGHT = 1

USER_SCORE_EXPONENT = 1 / 2.5
USER_SCORE_THRESHOLD = 1 / 3

MAX_RESULTS = 50

PROBABILITY_THRESHOLD = 1 / 20


def parse(s: str) -> list[str]:
    return re.findall(r"[\w.\-_]{1,30}", s.lower())[:MAX_TOKENS]


def score_words(word_1: str, word_2: str, /) -> float:
    ratio = SequenceMatcher(None, word_1, word_2, autojunk=False).ratio()
    return ratio ** WORDS_SIMILARITY_EXPONENT * WORD_LENGTH_BONUS ** (min(len(word_1), len(word_2)) - 1)


@dataclass
class WordScore:
    word: str
    score: float = 0


def score_on_string(query: list[WordScore], s: str, weight: int = 1):
    string = parse(s)
    matrix = [
        [
            score_words(q.word, token)
            for q in query
        ]
        for token in string
    ]
    for q_start in range(len(query)):
        for s_start in range(len(string)):
            prefix = weight
            for i in range(min(
                    len(query) - q_start,
                    len(string) - s_start
            )):
                prefix *= matrix[s_start + i][q_start + i]
                query[q_start].score = max(query[q_start].score, prefix)
                prefix *= SENTENCE_LENGTH_BONUS


def score_user(user_info: UserInfo, query: list[str]) -> float:
    q = [WordScore(word) for word in query]
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

    return sum([word.score for word in q])


@dataclass
class UserScore:
    info: UserInfo
    score: float = None
    exp: float = None
    probability: float = None


def debug_output(score, query, mean):
    print(f"{query}: {score.info.user}: {score.score:.2f} ({(100 * (score.probability - mean)):.2f}%)")
    return score.info


def search(query: str, requesting_user: User) -> list[UserInfo]:
    if query == "*":
        return [user.info(requesting_user) for user in User.objects.activated().order_by("id")[:MAX_RESULTS]]

    parsed = parse(query)
    results = []
    max_score = 0
    for user in User.objects.activated():
        score = UserScore(user.info(requesting_user))
        score.score = score_user(score.info, parsed) ** USER_SCORE_EXPONENT
        if score.score < USER_SCORE_THRESHOLD:
            continue
        max_score = max(max_score, score.score)
        results.append(score)

    total = 0  # softmax
    for score in results:
        score.exp = math.exp(score.score - max_score)
        total += score.exp

    if not total:
        return []

    for score in results:
        score.probability = score.exp / total

    mean = 1 / len(results)

    return ([
        score.info
        for score in sorted(
            filter(
                lambda x: x.probability - mean > PROBABILITY_THRESHOLD,
                results
            ),
            key=lambda x: x.probability,
            reverse=True)
    ])[:MAX_RESULTS]

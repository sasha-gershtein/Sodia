import math
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from .models import User

from interactions.models import UserInfo


def parse(s: str) -> list[str]:
    return re.findall(r"[\w.\-_]+", s.lower())


def score_words(word_1: str, word_2: str, /) -> float:
    ratio = SequenceMatcher(None, word_1, word_2, autojunk=False).ratio()
    return ratio ** 5 * 1.04 ** (len(word_1) + len(word_2) - 2)


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
                prefix *= 1.5


def score_user(user_info: UserInfo, query: list[str]) -> float:
    q = [WordScore(word) for word in query]
    score_on_string(q, user_info.username, 10)
    score_on_string(q, user_info.display_name, 7)
    full_name = " ".join(filter(lambda x: x, [user_info.first_name, user_info.last_name]))
    if full_name: score_on_string(q, full_name, 7)
    if user_info.description: score_on_string(q, user_info.description, 3)
    if user_info.house: score_on_string(q, user_info.house.name, 5)
    if user_info.boarding_type: score_on_string(q, user_info.boarding_type.name, 3)
    if user_info.country:
        score_on_string(q, user_info.country.name, 2)
        score_on_string(q, user_info.country.code, 1)
    if user_info.gender: score_on_string(q, user_info.gender, 1)

    return sum([word.score for word in q])


@dataclass
class UserScore:
    user: User
    score: float = None
    exp: float = None
    probability: float = None


def search(query: str, requesting_user: User) -> list[User]:
    if query == "*":
        return list(User.objects.activated().order_by("id"))

    parsed = parse(query)
    results = []
    max_score = 0
    for user in User.objects.activated():
        score = UserScore(user)
        score.score = score_user(user.info(requesting_user), parsed)
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

    return [
        score.user
        for score in sorted(
            filter(
                lambda x: x.probability - mean > .1,
                results
            ),
            key=lambda x: x.probability,
            reverse=True)
    ]

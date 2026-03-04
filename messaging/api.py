from api.decorators import api_login_required
from api.errors import BadRequestError

from users.models import User


@api_login_required
def get_dialogues(_request, user: User, _data):
    return [
        dialogue.interlocutor.info(user).partial
        for dialogue in user.get_dialogues()
    ]


@api_login_required
def get_dialogue_messages(_request, user: User, data):
    interlocutor = User.objects.get_user_by_data(data)
    if user == interlocutor:
        raise BadRequestError("Cannot have a dialogue with yourself", reason="SELF_DIALOGUE")
    if not isinstance(start := data.get("start", 0), int):
        raise BadRequestError("Start must be an integer")
    if not isinstance(n := data.get("n", 10), int):
        raise BadRequestError("n must be an integer")
    return [
        message.info
        for message in user.get_dialogue_messages(interlocutor, start, n)
    ]


@api_login_required
def mark_read(_request, user: User, data):
    interlocutor = User.objects.get_user_by_data(data)
    if user == interlocutor:
        raise BadRequestError("Cannot have a dialogue with yourself", reason="SELF_DIALOGUE")
    user.mark_dialogue_read(interlocutor)


@api_login_required
def send_message(_request, user: User, data):
    if not isinstance(content := data.get("content"), str):
        raise BadRequestError("Content is required")
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        raise BadRequestError("Cannot send a message to yourself", reason="SELF_MESSAGE")
    return user.send_message(recipient, content)

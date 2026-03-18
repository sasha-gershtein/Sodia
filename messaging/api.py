"""This file defines API views that handle API requests related to the "messaging" app and its models"""

from api.decorators import api_login_required
from api.errors import BadRequestError
from users.middleware import SessionData

from users.models import User


@api_login_required
def get_dialogues(_request, user: User, _data):
    """fetch list of user's dialogues"""
    return [
        dialogue.interlocutor.info(user).partial  # return interlocutor's partial info
        for dialogue in user.get_dialogues()  # for every dialogue
    ]


@api_login_required
def get_dialogue_messages(_request, user: User, data):
    """get messages in a dialogue in a specified ids range.
    messages are returned in reverse order of their position in the dialogue.
    the first message returned is with id strictly smaller than start (start should be the last fetched id)
    if start is 0, the first message returned is the last message sent in the dialogue
    n is the number of messages returned"""
    interlocutor = User.objects.get_user_by_data(data)
    if user == interlocutor:
        raise BadRequestError("Cannot have a dialogue with yourself", reason="SELF_DIALOGUE")
    if not isinstance(start := data.get("start", 0), int):  # start = 0 by default
        raise BadRequestError("Start must be an integer")
    if not isinstance(n := data.get("n", 10), int):  # n is 10 by default
        raise BadRequestError("n must be an integer")
    return [
        message.info  # return message info
        for message in user.get_dialogue_messages(interlocutor, start, n)  # for every fetched message
    ]


@api_login_required
def mark_read(_request, user: User, data):
    """mark all messages in a dialogue as read"""
    interlocutor = User.objects.get_user_by_data(data)
    if user == interlocutor:
        raise BadRequestError("Cannot have a dialogue with yourself", reason="SELF_DIALOGUE")
    user.mark_dialogue_read(interlocutor)  # mark dialogue as read


@api_login_required
def send_message(request, user: User, data):
    """send a message"""
    if not isinstance(content := data.get("content"), str):
        # content is missing or of wrong type
        raise BadRequestError("Content is required", reason="CONTENT_MISSING")
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        # attempt to send message to self
        raise BadRequestError("Cannot send a message to yourself", reason="SELF_MESSAGE")
    content = content.strip()  # remove trailing whitespace
    if not content:
        # message is whitespace-only
        raise BadRequestError("Message is empty", reason="EMPTY_MESSAGE")
    if len(content) > 4096:
        raise BadRequestError("Message is too long", reason="MESSAGE_TOO_LONG")
    session_data: SessionData = request.session_data
    # send a message (exclude request's session from session update) and return message info
    return user.send_message(recipient, content, exclude_session=session_data.session).info

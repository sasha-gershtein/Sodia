from api.decorators import api_login_required
from api.errors import BadRequestError, NotFoundError, ForbiddenError, ConflictError

from users.models import User

from interactions.models import FriendRequest, Block


@api_login_required
def send_friend_request(_request, user: User, data):
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        raise BadRequestError("Cannot send a friend request to yourself", reason="SELF_FRIEND_REQUEST")
    if not user.is_friend_request_sendable_to(recipient):
        raise ConflictError(f"Could not send a friend request. Please try refreshing the page",
                            reason="FRIEND_REQUEST_NOT_SENDABLE")
    user.send_friend_request_to(recipient)
    return recipient.info(user).partial


@api_login_required
def respond_to_friend_request(_request, user: User, data):
    sender = User.objects.get_user_by_data(data)
    if not "accept" in data:
        raise BadRequestError("Must provide 'accept' parameter")
    try:
        if data["accept"]:
            user.accept_friend_request_from(sender)
        else:
            user.deny_friend_request_from(sender)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend request does not exist")
    return sender.info(user).partial


@api_login_required
def withdraw_friend_request(_request, user: User, data):
    recipient = User.objects.get_user_by_data(data)
    try:
        user.withdraw_friend_request_to(recipient)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend request does not exist")
    return recipient.info(user).partial


@api_login_required
def remove_friend(_request, user: User, data):
    friend = User.objects.get_user_by_data(data)
    try:
        user.remove_friend(friend)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend does not exist")
    return friend.info(user).partial


@api_login_required
def get_friends(_request, user: User, data):
    user_info = User.objects.get_user_by_data(data).info(user)  # validates and raises appropriate exceptions
    if not user_info.friends_visible:
        raise ForbiddenError("Friends list is not visible", reason="FRIENDS_LIST_HIDDEN")
    return [
        friend.info(user).partial
        for friend in user_info.friends
    ]


@api_login_required
def block(_request, user: User, data):
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        raise BadRequestError("Cannot block yourself", reason="SELF_BLOCK")
    if user.is_blocking(recipient):
        raise ConflictError("Already blocking", reason="REPEATED_BLOCK")
    user.block(recipient)
    return recipient.info(user).partial


@api_login_required
def unblock(_request, user: User, data):
    recipient = User.objects.get_user_by_data(data)
    try:
        user.unblock(recipient)
    except Block.DoesNotExist:
        raise NotFoundError("Block does not exist")
    return recipient.info(user).partial

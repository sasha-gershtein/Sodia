from api.decorators import api_login_required
from api.errors import BadRequestError, NotFoundError, ForbiddenError

from users.models import User

from interactions.models import FriendRequest, UserInfo


@api_login_required
def send_friend_request(_request, user, data):
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        raise BadRequestError("Cannot send a friend request to yourself", reason="SELF_FRIEND_REQUEST")
    FriendRequest.objects.send_request(user, recipient, is_api=True)
    return recipient.info(user).partial


@api_login_required
def respond_to_friend_request(_request, user, data):
    sender = User.objects.get_user_by_data(data)
    if not "accept" in data:
        raise BadRequestError("Must provide 'accept' parameter")
    try:
        if data["accept"]:
            FriendRequest.objects.accept_request(sender, user)
        else:
            FriendRequest.objects.deny_request(sender, user)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend request does not exist")
    return sender.info(user).partial


@api_login_required
def withdraw_friend_request(_request, user, data):
    recipient = User.objects.get_user_by_data(data)
    try:
        FriendRequest.objects.withdraw_request(user, recipient)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend request does not exist")
    return recipient.info(user).partial


@api_login_required
def remove_friend(_request, user, data):
    friend = User.objects.get_user_by_data(data)
    try:
        FriendRequest.objects.remove_friend(user, friend)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend does not exist")
    return friend.info(user).partial


@api_login_required
def get_friends(_request, user, data):
    user_data = UserInfo(
        User.objects.get_user_by_data(data),  # validates and raises appropriate exceptions
        user
    )
    if not user_data.friends_visible:
        raise ForbiddenError("Friends list is not visible", reason="FRIENDS_LIST_HIDDEN")
    return [
        friend.info(user).partial
        for friend in user_data.friends
    ]


@api_login_required
def block(_request, _user, data):
    User.objects.get_user_by_data(data)
    raise NotImplementedError


@api_login_required
def unblock(_request, _user, data):
    User.objects.get_user_by_data(data)
    raise NotImplementedError

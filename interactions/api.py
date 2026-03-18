"""This file defines API views that handle API requests related to the "interactions" app and its models"""

from api.decorators import api_login_required
from api.errors import BadRequestError, NotFoundError, ForbiddenError, ConflictError

from users.models import User

from .models import FriendRequest, Block


@api_login_required
def send_friend_request(_request, user: User, data):
    """send a friend request to another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        # attempt to send a friend request to self
        raise BadRequestError("Cannot send a friend request to yourself", reason="SELF_FRIEND_REQUEST")
    if not user.is_friend_request_sendable_to(recipient):
        # a friend request cannot be currently sent between users
        raise ConflictError(f"Could not send a friend request. Please try refreshing the page",
                            reason="FRIEND_REQUEST_NOT_SENDABLE")
    user.send_friend_request_to(recipient)  # send request
    return recipient.info(user).partial  # return user info with the updated relation status


@api_login_required
def respond_to_friend_request(_request, user: User, data):
    """respond to a friend request from another user.
    accept: bool parameter is passed to specify if request is accepted"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    sender = User.objects.get_user_by_data(data)
    if not isinstance(accept := data.get("accept"), bool):
        raise BadRequestError("Must provide 'accept' parameter")
    try:
        if accept:
            user.accept_friend_request_from(sender)  # accept request
        else:
            user.deny_friend_request_from(sender)  # deny request
    except FriendRequest.DoesNotExist:
        # a pending friend request from specified sender does not exist
        # for example, if it has already been accepted
        raise NotFoundError("Friend request does not exist")
    return sender.info(user).partial  # return user info with the updated relation status


@api_login_required
def withdraw_friend_request(_request, user: User, data):
    """withdraw a friend request sent to another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    recipient = User.objects.get_user_by_data(data)
    try:
        user.withdraw_friend_request_to(recipient)
    except FriendRequest.DoesNotExist:
        raise NotFoundError("Friend request does not exist")
    return recipient.info(user).partial  # return user info with the updated relation status


@api_login_required
def remove_friend(_request, user: User, data):
    """remove a friend connection"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    friend = User.objects.get_user_by_data(data)
    try:
        user.remove_friend(friend)  # remove friend
    except FriendRequest.DoesNotExist:
        # users are not friends in the first place
        raise NotFoundError("Friend does not exist")
    return friend.info(user).partial  # return user info with the updated relation status


@api_login_required
def get_friends(_request, user: User, data):
    """get a list of another user's friends"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    user_info = User.objects.get_user_by_data(data).info(user)
    if not user_info.friends_visible:
        # user doesn't have access to the friends list
        raise ForbiddenError("Friends list is not visible", reason="FRIENDS_LIST_HIDDEN")
    return [
        friend.info(user).partial  # return partial info of every friend
        for friend in user_info.friends
    ]


@api_login_required
def block(_request, user: User, data):
    """block another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    recipient = User.objects.get_user_by_data(data)
    if user == recipient:
        raise BadRequestError("Cannot block yourself", reason="SELF_BLOCK")
    if user.is_blocking(recipient):
        raise ConflictError("Already blocking", reason="REPEATED_BLOCK")
    user.block(recipient)
    return recipient.info(user).partial  # return user info with the updated relation status


@api_login_required
def unblock(_request, user: User, data):
    """unblock another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    recipient = User.objects.get_user_by_data(data)
    try:
        user.unblock(recipient)
    except Block.DoesNotExist:
        raise NotFoundError("Block does not exist")
    return recipient.info(user).partial  # return user info with the updated relation status

"""This file defines the view to handle API request to fetch session updates"""

from api.decorators import api_login_required
from updates.models import Update
from users.middleware import SessionData
from users.models import User


@api_login_required
def get_updates(request, _user: User, _data):
    """fetch and clear all updates for the current session"""
    session_data: SessionData = request.session_data
    return Update.objects.get_updates(session=session_data.session)

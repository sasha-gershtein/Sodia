"""This file defines the Update model (db table) and its manager"""

from django.db import models, transaction

from users.models import Session, User


class UpdateManager(models.Manager):
    """manager for the Update model"""
    MAX_UPDATES = 100  # max number of updates that can be stored for a single session

    @transaction.atomic
    def create_update_for_session(self, message, session: Session):
        """create a new update for a session, where message is its handler name and content tuple"""
        # lock session row to prevent race condition errors
        # only lock the Session row, not the related User
        session = Session.objects.select_for_update(of=["self"]).get(pk=session.pk)
        next_id = session.next_update_id
        if next_id < 0:  # max updates already reached, new updates are not stored
            return
        if next_id >= self.MAX_UPDATES:
            # max updates reached
            self.filter(session=session).delete()  # delete all updates for this session
            session.next_update_id = -1  # mark session as overflowed
            session.save()
            return

        # create an update with next id
        session.next_update_id = next_id + 1
        session.save()
        return self.create(
            session=session,
            id_in_session=next_id,
            message=message,
        )

    def create_updates_for_user(self, handler: str, msg, user: User, exclude: Session | None = None):
        """create an update for every session of a user, except for the exclude session if specified
        msg is the content of the update that will be passed to a registered handler identified by handler"""
        message = handler, msg
        sessions = Session.objects.filter(user=user)  # get sessions of the user
        for session in sessions if exclude is None else sessions.exclude(pk=exclude.pk):  # exclude if necessary
            self.create_update_for_session(message, session)

    @transaction.atomic
    def get_updates(self, session: Session):
        """get and clear updates for a session - returned in JSON serializable format"""
        # lock session row to prevent race condition errors
        # only lock the Session row, not the related User
        session = Session.objects.select_for_update(of=["self"]).get(pk=session.pk)
        next_id = session.next_update_id
        session.next_update_id = 0  # clear counter
        session.save()
        if next_id < 0:
            # if overflowed, return command to refresh
            return {"root": ["REFRESH"]}
        data = {}  # build data as {"handler1": [update1, update2], "handler2": [...], ...}
        updates = self.filter(session=session).order_by("id_in_session")
        for update in updates:
            handler, msg = update.message
            data.setdefault(handler, [])
            data[handler].append(msg)
        updates.delete()
        return data


class Update(models.Model):
    """model to store updates for a session"""
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    id_in_session = models.IntegerField()
    message = models.JSONField()

    objects = UpdateManager()

    class Meta:
        constraints = [
            # add a unique constraint on id in session (enforced on db level and automatically adds a search index)
            models.UniqueConstraint(fields=["session", "id_in_session"], name="unique_session_update"),
        ]

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} {self.id_in_session} of {self.session}>"

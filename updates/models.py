from django.db import models, transaction

from users.models import Session, User


class UpdateManager(models.Manager):
    MAX_UPDATES = 100

    @transaction.atomic
    def create_update_for_session(self, message, session: Session):
        session = Session.objects.select_for_update(of=["self"]).get(pk=session.pk)
        next_id = session.next_update_id
        if next_id < 0:
            return
        if next_id >= self.MAX_UPDATES:
            self.filter(session=session).delete()
            session.next_update_id = -1
            session.save()
            return

        session.next_update_id = next_id + 1
        session.save()
        return self.create(
            session=session,
            id_in_session=next_id,
            message=message,
        )

    def create_updates_for_user(self, handler: str, msg, user: User, exclude: Session | None = None):
        message = handler, msg
        sessions = Session.objects.filter(user=user)
        for session in sessions if exclude is None else sessions.exclude(pk=exclude.pk):
            self.create_update_for_session(message, session)

    @transaction.atomic
    def get_updates(self, session: Session):
        session = Session.objects.select_for_update(of=["self"]).get(pk=session.pk)
        next_id = session.next_update_id
        session.next_update_id = 0
        session.save()
        if next_id < 0:
            return {"root": ["REFRESH"]}
        data = {}
        updates = self.filter(session=session).order_by('id_in_session')
        for update in updates:
            handler, msg = update.message
            data.setdefault(handler, [])
            data[handler].append(msg)
        updates.delete()
        return data


class Update(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    id_in_session = models.IntegerField(default=0)
    message = models.JSONField()

    objects = UpdateManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'id_in_session'], name='unique_session_update'),
        ]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id_in_session} of {self.session}>"

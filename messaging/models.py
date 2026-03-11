from dataclasses import dataclass
from datetime import datetime

from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone

from updates.models import Update
from users.models import User, Session


class DialogueManager(models.Manager):
    def get_readonly_dialogue(self, user: User, interlocutor: User):
        try:
            dialogue = self.get(user=user, interlocutor=interlocutor)
            return ReadOnlyDialogue(
                user=dialogue.user,
                interlocutor=dialogue.interlocutor,
                pk=dialogue.pk,
                unread_messages_count=dialogue.unread_messages_count,
                last_message_id=dialogue.last_message_id,
                can_message_back=dialogue.can_message_back,
            )
        except self.model.DoesNotExist:
            return ReadOnlyDialogue(
                user=user,
                interlocutor=interlocutor,
            )

    def get_dialogue(self, user: User, interlocutor: User):
        if user == interlocutor:
            raise ValueError("Cannot have a dialogue with yourself")
        return self.get(user=user, interlocutor=interlocutor)

    def get_locked_dialogue(self, user: User, interlocutor: User):
        if user == interlocutor:
            raise ValueError("Cannot have a dialogue with yourself")
        dialogue, created = self.select_for_update().get_or_create(user=user, interlocutor=interlocutor)
        if created:
            dialogue = self.select_for_update().get(pk=dialogue.pk)
        return dialogue

    @transaction.atomic
    def get_locked_inverse_pair(self, user: User, interlocutor: User):
        if user.id > interlocutor.id:
            inverse, dialogue = self.get_locked_inverse_pair(interlocutor, user)
            return dialogue, inverse

        dialogue = self.get_locked_dialogue(user, interlocutor)
        inverse = self.get_locked_dialogue(interlocutor, user)
        return dialogue, inverse

    def get_unread_messages_count(self, user: User, interlocutor: User):
        return self.get_readonly_dialogue(user, interlocutor).unread_messages_count

    @transaction.atomic
    def send_message(self, sender: User, recipient: User, content: str, *, exclude_session: Session | None = None):
        if not recipient.info(sender).can_message:
            raise ValueError(f"Cannot send message from {sender} to {recipient}")
        dialogue, inverse = self.get_locked_inverse_pair(sender, recipient)
        Message.objects.create_message(sender, inverse, content)
        return Message.objects.create_message(sender, dialogue, content, exclude_session=exclude_session)

    @transaction.atomic
    def reset_can_message_back(self, user_1, user_2, /):
        reset = (
            self.get_readonly_dialogue(user_1, user_2).can_message_back,
            self.get_readonly_dialogue(user_2, user_1).can_message_back,
        )
        if any(reset):
            dialogue, inverse = self.get_locked_inverse_pair(user_1, user_2)
            if dialogue.can_message_back:
                dialogue.can_message_back = False
                dialogue.save()
            if inverse.can_message_back:
                inverse.can_message_back = False
                inverse.save()


@dataclass
class ReadOnlyDialogue:
    user: User
    interlocutor: User
    pk: int | None = None
    unread_messages_count: int = 0
    last_message_id: int = 0
    last_message_sent_at: datetime | None = None
    can_message_back: bool = False


class Dialogue(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dialogues")
    interlocutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    unread_messages_count = models.IntegerField(default=0)
    last_message_id = models.IntegerField(default=0)
    last_message_sent_at = models.DateTimeField(default=timezone.now)
    can_message_back = models.BooleanField(default=False)

    objects = DialogueManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "interlocutor"],
                name="unique_dialogue",
            ),
            models.CheckConstraint(
                condition=~Q(user=F("interlocutor")),
                name="prevent_self_dialogue",
            ),
        ]

    def get_messages(self, start=0, n=10):
        return Message.objects.get_dialogue_messages(self, start, n)

    def mark_read(self):
        self.unread_messages_count = 0
        self.save()


class MessageManager(models.Manager):
    @transaction.atomic
    def create_message(self, sender: User, dialogue: Dialogue, content: str, *, exclude_session: Session | None = None):
        update = {
            "last_message_sent_at": timezone.now(),
            "last_message_id": F("last_message_id") + 1,
        }
        is_own = sender == dialogue.user
        if not is_own:
            update["unread_messages_count"] = F("unread_messages_count") + 1
            update["can_message_back"] = True
        Dialogue.objects.filter(pk=dialogue.pk).update(**update)
        dialogue.refresh_from_db()

        obj = self.create(
            dialogue=dialogue,
            id_in_dialogue=dialogue.last_message_id,
            content=content,
            is_own=is_own,
        )

        msg = obj.info
        msg["interlocutor"] = dialogue.interlocutor.info(dialogue.user).partial
        print(msg)
        Update.objects.create_updates_for_user("messaging.new", msg, dialogue.user, exclude_session)

        return obj

    def get_dialogue_messages(self, dialogue: Dialogue | ReadOnlyDialogue, start: int = 0, n: int = 10):
        if dialogue.pk is None:
            return self.none()
        if start <= 0:
            start = dialogue.last_message_id + start + 1
        return self.filter(
            dialogue_id=dialogue.pk,
            id_in_dialogue__lt=start
        ).order_by("-id_in_dialogue")[:n]


class Message(models.Model):
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE)
    id_in_dialogue = models.IntegerField()
    content = models.TextField(max_length=4096)
    is_own = models.BooleanField()
    sent_at = models.DateTimeField(auto_now_add=True)

    objects = MessageManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dialogue", "id_in_dialogue"],
                name="unique_dialogue_message",
            ),
        ]

    @property
    def info(self):
        return {
            "id": self.id_in_dialogue,
            "content": self.content,
            "is_own": self.is_own,
            "sent_at": self.sent_at.timestamp(),
        }

"""This file defines models (db tables) for app "messaging", their methods, and model managers to handle models"""

from dataclasses import dataclass
from datetime import datetime

from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone

from updates.models import Update
from users.models import User, Session


class DialogueManager(models.Manager):
    """manager for Dialogue model"""

    def get_dialogue(self, user: User, interlocutor: User):
        """get an unlocked dialogue row, raise self.model.DoesNotExist if row doesn't exist.
        Returned value has to be updated carefully to avoid race condition errors"""
        if user == interlocutor:
            raise ValueError("Cannot have a dialogue with yourself")
        return self.get(user=user, interlocutor=interlocutor)

    def get_readonly_dialogue(self, user: User, interlocutor: User) -> "ReadOnlyDialogue":
        """get a ReadOnlyDialogue dataclass instance with dialogue info.
        If dialogue doesn't exist, return an empty default object.
        This data should never be used to update values in db because it is prone to race condition errors"""
        try:
            dialogue = self.get_dialogue(user, interlocutor)
            # dialogue is found, return the dataclass instance
            return ReadOnlyDialogue(
                user=dialogue.user,
                interlocutor=dialogue.interlocutor,
                pk=dialogue.pk,
                unread_messages_count=dialogue.unread_messages_count,
                last_message_id=dialogue.last_message_id,
                can_message_back=dialogue.can_message_back,
            )
        except self.model.DoesNotExist:
            # dialogue doesn't exist, return empty default value
            return ReadOnlyDialogue(
                user=user,
                interlocutor=interlocutor,
            )

    def get_locked_dialogue(self, user: User, interlocutor: User):
        """get a dialogue between user and interlocutor, and create new if it doesn't exist.
        Locks dialogue with SELECT FOR UPDATE, so has to be called from within a transaction"""
        if user == interlocutor:
            raise ValueError("Cannot have a dialogue with yourself")
        dialogue, created = self.select_for_update().get_or_create(user=user, interlocutor=interlocutor)
        if created:
            # if a new row is created, it isn't locked at creation, so select and lock again
            dialogue = self.select_for_update().get(pk=dialogue.pk)
        return dialogue

    @transaction.atomic
    def get_locked_inverse_pair(self, user: User, interlocutor: User):
        """get a pair of dialogues between two users: [user -> interlocutor] and [interlocutor -> user].
        Locks returned dialogues with SELECT FOR UPDATE"""
        # a potential deadlock could happen if two processes call (u1, u2) and (u2, u1) respectively
        # both processes first lock their first dialogue (u1 -> u2 and u2 -> u1 respectively)
        # and are left in a deadlock waiting for the other dialogue to be released (which it never will be)
        # to avoid this, always lock dialogues in a deterministic order, starting with (lower id -> higher id)
        if user.id > interlocutor.id:
            # order is wrong, return same dialogues but locked in the opposite order
            inverse, dialogue = self.get_locked_inverse_pair(interlocutor, user)
            return dialogue, inverse

        dialogue = self.get_locked_dialogue(user, interlocutor)  # lock and get user -> interlocutor
        inverse = self.get_locked_dialogue(interlocutor, user)  # lock and get interlocutor -> user
        return dialogue, inverse

    def get_unread_messages_count(self, user: User, interlocutor: User):
        """get the count of unread messages received by user from interlocutor"""
        return self.get_readonly_dialogue(user, interlocutor).unread_messages_count

    @transaction.atomic
    def send_message(self, sender: User, recipient: User, content: str, *, exclude_session: Session | None = None):
        """send a message from sender to recipient with specified content.
        Session updates are issued to all sessions of both users except for exclude_session (of sender) if specified."""
        if not recipient.info(sender).can_message:
            # cannot message
            raise ValueError(f"Cannot send message from {sender} to {recipient}")
        dialogue, inverse = self.get_locked_inverse_pair(sender, recipient)
        # create messages in both dialogues
        Message.objects.create_message(sender, inverse, content)
        return Message.objects.create_message(sender, dialogue, content, exclude_session=exclude_session)

    @transaction.atomic
    def reset_can_message_back(self, user_1, user_2, /):
        """reset flags marking that either of the two users has messaged each other, permitting other to message back"""
        reset = (  # check if either dialogue needs resetting without locking rows
            self.get_readonly_dialogue(user_1, user_2).can_message_back,
            self.get_readonly_dialogue(user_2, user_1).can_message_back,
        )
        if any(reset):
            # at least one needs resetting, so lock dialogue pair
            dialogue, inverse = self.get_locked_inverse_pair(user_1, user_2)
            if dialogue.can_message_back:
                # reset dialogue
                dialogue.can_message_back = False
                dialogue.save()
            if inverse.can_message_back:
                # reset inverse
                inverse.can_message_back = False
                inverse.save()


@dataclass
class ReadOnlyDialogue:
    """read-only dataclass with Dialogue info.
    Resembles the model but is not liked to db and thus safe to use in race condition"""
    user: User
    interlocutor: User
    pk: int | None = None
    unread_messages_count: int = 0
    last_message_id: int = 0
    last_message_sent_at: datetime | None = None
    can_message_back: bool = False


class Dialogue(models.Model):
    """model to store dialogue info"""
    # user to whom the dialogue belongs
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dialogues")
    # the other users in the dialogue
    interlocutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    unread_messages_count = models.IntegerField(default=0)  # count of unread messages received from interlocutor
    last_message_id = models.IntegerField(default=0)  # id in dialogue of last message sent in this dialogue
    last_message_sent_at = models.DateTimeField(default=timezone.now)  # time of last message for sorting
    # flag marking that user can reply in this dialogue because interlocutor has messaged user first
    can_message_back = models.BooleanField(default=False)

    objects = DialogueManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(  # unique request per ordered pair [user, interlocutor] (enforced on db level)
                fields=["user", "interlocutor"],  # unique constraint automatically adds a search index
                name="unique_dialogue",
            ),
            models.CheckConstraint(
                condition=~Q(user=F("interlocutor")),  # check that user != interlocutor (enforced on db level)
                name="prevent_self_dialogue",
            ),
        ]

    def get_messages(self, start=0, n=10):
        """get messages in the dialogue in a specified ids range.
        messages are returned in reverse order of their position in the dialogue.
        the first message returned is with id strictly smaller than start (start should be the last fetched id)
        if start is 0, the first message returned is the last message sent in the dialogue
        n is the number of messages returned"""
        return Message.objects.get_dialogue_messages(self, start, n)

    @transaction.atomic
    def mark_read(self):
        """mark all messages in dialogue as read"""
        user = User.objects.select_for_update(of=["self"]).get(pk=self.user.pk)  # lock user row (do not lock related)
        # decrease total unread messages count of user by the count of unread messages in this dialogue
        user.unread_messages_count -= self.unread_messages_count
        user.save()
        self.unread_messages_count = 0  # reset counter in dialogue
        self.save()


class MessageManager(models.Manager):
    @transaction.atomic
    def create_message(self, sender: User, dialogue: Dialogue, content: str, *, exclude_session: Session | None = None):
        """create a new message in a dialogue sent by sender with specified content.
        Session updates are issued to all sessions of dialogue.user except for exclude_session if specified."""
        update = {  # dialogue's fields to update atomically
            "last_message_sent_at": timezone.now(),
            "last_message_id": F("last_message_id") + 1,  # tread-safe increment (implemented by db) to avoid RMW error
        }
        is_own = sender == dialogue.user
        if not is_own:
            # increment unread messages count of user (thread-safe to avoid RMW)
            User.objects.filter(pk=dialogue.user.pk).update(unread_messages_count=F("unread_messages_count") + 1)
            # increment unread messages count of dialogue (thread-safe to avoid RMW)
            update["unread_messages_count"] = F("unread_messages_count") + 1
            update["can_message_back"] = True  # user has been messaged, so user can message back
        Dialogue.objects.filter(pk=dialogue.pk).update(**update)  # update specified fields atomically
        dialogue.refresh_from_db()  # refreshed model's values from db row

        obj = self.create(  # create message
            dialogue=dialogue,
            id_in_dialogue=dialogue.last_message_id,
            content=content,
            is_own=is_own,
        )

        # issue session updates
        msg = obj.info
        msg["interlocutor"] = dialogue.interlocutor.info(dialogue.user).partial
        Update.objects.create_updates_for_user("messaging.new", msg, dialogue.user, exclude_session)

        return obj  # return created message

    def get_dialogue_messages(self, dialogue: Dialogue | ReadOnlyDialogue, start: int = 0, n: int = 10):
        """get messages in the dialogue in a specified ids range.
        messages are returned in reverse order of their position in the dialogue.
        the first message returned is with id strictly smaller than start (start should be the last fetched id)
        if start is 0, the first message returned is the last message sent in the dialogue
        n is the number of messages returned"""
        if dialogue.pk is None:
            # this is an empty ReadOnlyDialogue, real dialogue doesn't exist
            return self.none()  # return an empty query set
        if start <= 0:
            # start counts from last
            start = dialogue.last_message_id + start + 1
        return self.filter(
            dialogue_id=dialogue.pk,
            id_in_dialogue__lt=start,  # id in dialogue < start
        ).order_by("-id_in_dialogue")[:n]  # sort in reverse chronological order


class Message(models.Model):
    """model to store messages"""
    dialogue = models.ForeignKey(Dialogue, on_delete=models.CASCADE)
    id_in_dialogue = models.IntegerField()  # order of this message in its dialogue, not globally unique
    content = models.TextField(max_length=4096)  # content of the message
    is_own = models.BooleanField()  # True if message sent by user in the dialogue, False if by interlocutor
    sent_at = models.DateTimeField(auto_now_add=True)

    objects = MessageManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(  # unique message id in dialogue (enforced on db level)
                fields=["dialogue", "id_in_dialogue"],  # unique constraint automatically adds a search index
                name="unique_dialogue_message",
            ),
        ]

    @property
    def info(self):
        """return JSON serializable message info"""
        return {
            "id": self.id_in_dialogue,
            "content": self.content,
            "is_own": self.is_own,
            "sent_at": self.sent_at.timestamp(),
        }

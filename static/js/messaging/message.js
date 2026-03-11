import {api, processError} from "../api/api.js";
import {formatTimestamp, page_loading} from "../api/ui.js";
import {PushOnlyDeque} from "../deque.js";
import {Updates} from "../updates/updates.js";

const no_selected_dialogue = document.getElementById("no-selected-dialogue");
const dialogue_title = document.getElementById("dialogue-title");
const message_input_field = document.getElementById("message-input-field");
const messages_area = document.getElementById("messages-area");
const message_sentinel = document.getElementById("message-sentinel");
const message_input_form = document.getElementById("message-input-form");

function adjustMessageInputFieldHeight() {
    message_input_field.style.height = "auto";
    message_input_field.style.height = message_input_field.scrollHeight + "px";
}

function setInputValue(value) {
    message_input_field.value = value;
    adjustMessageInputFieldHeight();
}

message_input_field.addEventListener("input", adjustMessageInputFieldHeight);

class Message {
    constructor(message_info) {
        this.info = message_info;

        this.element = document.createElement("div");
        this.element.classList.add("message");
        // noinspection JSUnresolvedReference
        if (message_info.is_own) this.element.classList.add("own");
        this.sent_at = document.createElement("div");
        this.sent_at.classList.add("sent-at");
        this.sent_at.innerText = formatTimestamp(message_info.sent_at);
        this.content = document.createElement("div");
        this.content.classList.add("message-content");
        this.content.innerText = message_info.content;

        this.element.append(this.sent_at, this.content);
    }
}

class Dialogue {
    static check_sentinel_interval_id = null;
    static loading_controller = null;

    static get loading() {
        return !!Dialogue.loading_controller && !Dialogue.loading_controller.signal.aborted;
    }

    messages = new PushOnlyDeque();
    draft = "";
    all_messages_loaded = false;

    constructor(user_info) {
        this.info = user_info;

        this.element = document.createElement("label");
        this.element.classList.add("dialogue");
        this.input = document.createElement("input");
        this.input.type = "radio";
        this.input.name = "dialogue";
        this.name = document.createElement("span");
        // noinspection JSUnresolvedReference
        this.name.innerText = user_info.display_name;
        this.name.classList.add("name");
        this.counter = document.createElement("span");
        // noinspection JSUnresolvedReference
        this.counter.innerText = user_info.unread_messages_count || "";
        this.counter.classList.add("unread-messages-counter");
        this.element.append(this.input, this.name, this.counter);
        this.element.append(this.counter);

        this.input_controller = new AbortController();
        const params = {
            signal: this.input_controller.signal
        };

        this.input.addEventListener("input", this.onSelect.bind(this), params);

        DialogueList.element.prepend(this.element);
    }

    get unread_messages_count() {
        return this.info.unread_messages_count;
    }

    set unread_messages_count(value) {
        this.info.unread_messages_count = value;
        this.counter.innerText = value || "";
    }

    abort_input() {
        this.input_controller.abort();
    }

    saveDraft() {
        this.draft = message_input_field.value;
        setInputValue();
    }

    deselect(all = true) {
        if (all) {
            history.pushState({}, "", "/message/");
            document.title = "Messaging — Sodia";
            DialogueList.selected = null;
            this.input.checked = false;
            no_selected_dialogue.hidden = false;
        }
        this.saveDraft();
        Dialogue.loading_controller?.abort();
    }

    select() {
        this.input.checked = true;
        void this.onSelect();
    }

    onSelect() {
        DialogueList.selected?.deselect(false);
        DialogueList.selected = this;
        history.pushState({}, "", `/message/${this.info.username}/`); // TODO: go back on navigation
        // noinspection JSUnresolvedReference
        document.title = `${this.info.display_name} — Sodia Messaging`;

        no_selected_dialogue.hidden = true;
        // noinspection JSUnresolvedReference
        dialogue_title.innerText = this.info.display_name;
        // noinspection JSUnresolvedReference
        if (this.info.is_activated) dialogue_title.href = `/profile/${this.info.username}/`;
        void this.markRead();

        // noinspection JSUnresolvedReference
        if (!this.info.can_message) {
            message_input_field.disabled = true;
            message_input_form.classList.add("cannot-message");
            setInputValue("You cannot message this person");
        } else {
            message_input_field.disabled = false;
            message_input_form.classList.remove("cannot-message");
            setInputValue(this.draft);
            message_input_field.focus();
        }

        messages_area.replaceChildren(message_sentinel);
        const fragment = document.createDocumentFragment();
        for (const message of this.messages) {
            // noinspection JSUnresolvedReference
            fragment.append(message.element);
        }
        messages_area.insertBefore(fragment, message_sentinel);
        this.loadMessagesIfNeeded();
    }

    async markRead() {
        try {
            await api("/api/messaging/mark-read/", {id: this.info.id}, {attempts: 5});
            this.unread_messages_count = 0;
        } catch (err) {
            processError(err);
        }
    }

    addMessage(message_info, fragment = null, old = false) {
        let message = new Message(message_info);
        if (!old) this.float();
        if (DialogueList.selected !== this) {
            if (!old) this.unread_messages_count++;
            return;
        }
        if (old) {
            if (fragment) fragment.append(message.element);
            else messages_area.insertBefore(message.element, message_sentinel);
            this.messages.pushBack(message);
        } else {
            if (fragment) fragment.prepend(message);
            else messages_area.prepend(message.element);
            this.messages.pushFront(message);
            void this.markRead();
        }
        return message;
    }

    async loadMessages() {
        if (Dialogue.loading || this.all_messages_loaded || DialogueList.selected !== this) return;
        Dialogue.loading_controller = new AbortController();
        const n = 10;
        try {
            const response = await api("/api/messaging/load-dialogue/",
                {
                    id: this.info.id,
                    start: this.messages.back?.info.id ?? 0,
                    n,
                },
                {
                    attempts: 20,
                    signal: Dialogue.loading_controller.signal,
                });
            const fragment = document.createDocumentFragment();
            response.forEach((message_info) => this.addMessage(message_info, fragment, true));
            if (DialogueList.selected === this) messages_area.insertBefore(fragment, message_sentinel);
            if (response.length < n) this.all_messages_loaded = true;
        } catch (err) {
            processError(err);
        } finally {
            if (DialogueList.selected === this) Dialogue.loading_controller = null;
        }
        this.loadMessagesIfNeeded();
    }

    loadMessagesIfNeeded() {
        if (Dialogue.loading || this.all_messages_loaded || DialogueList.selected !== this) return;
        if (message_sentinel.getBoundingClientRect().bottom > messages_area.getBoundingClientRect().top - 550)
            void this.loadMessages();
    }

    float() {
        DialogueList.element.prepend(this.element);
    }

    async sendMessage() {
        if (message_input_field.disabled) return;
        const content = message_input_field.value.trim();
        if (!content) return;
        message_input_field.disabled = true;
        let message;
        try {
            message = await api("/api/messaging/send-message/", {
                id: this.info.id,
                content,
            }, {attempts: 1});
        } catch (err) {
            processError(err);
            return;
        } finally {
            message_input_field.disabled = false;
        }
        setInputValue("");
        message_input_field.focus();
        this.addMessage(message);
        this.float();
    }
}


// noinspection JSCheckFunctionSignatures
const messages_area_observer = new IntersectionObserver(
    (entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting) {
                clearInterval(Dialogue.check_sentinel_interval_id);
                continue;
            }
            void DialogueList.selected?.loadMessages();
            Dialogue.check_sentinel_interval_id = setInterval(() => {
                if (DialogueList.selected?.all_messages_loaded) {
                    clearInterval(Dialogue.check_sentinel_interval_id);
                    return;
                }
                DialogueList.selected?.loadMessagesIfNeeded();
            }, 250);
        }
    },
    {
        root: messages_area,
        rootMargin: "500px 0px 0px 0px",
        delay: 500,
    });
messages_area_observer.observe(message_sentinel);

class DialogueList {
    static element = document.getElementById("dialogue-list");
    static dialogues = {};
    static selected = null;

    static addDialogue(user_info) {
        return this.dialogues[user_info.id] = new Dialogue(user_info);
    }

    static deselect() {
        this.selected?.deselect();
    }
}

document.addEventListener("keydown", (e) => {
    if (["input", "textarea", "select", "button"].includes(e.target.tagName.toLowerCase())
        || e.target.isContentEditable) return;
    if ((e.ctrlKey && !["a", "Enter"].includes(e.key)) || e.altKey || e.metaKey) return;
    if (e.key === "Tab" || e.key.startsWith("Arrow")) return;
    if (e.key === "Escape") {
        DialogueList.deselect();
        return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
        void DialogueList.selected?.sendMessage();
        return;
    }
    if (DialogueList.selected !== null) message_input_field.focus();
});

message_input_field.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        DialogueList.deselect();
        e.stopPropagation();
        return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void DialogueList.selected?.sendMessage();
    }
});

message_input_form.addEventListener("invalid", (e) => e.preventDefault(), {capture: true});

message_input_form.addEventListener("submit", (e) => {
    e.preventDefault();
    void DialogueList.selected?.sendMessage();
});

const list = window.location.pathname.split("/");
const username = list[list.findIndex(e => e === "message") + 1] || null;

async function load() {
    let dialogues;
    try {
        dialogues = await api("/api/messaging/get-dialogues/", {}, {attempts: 100});
    } catch (err) {
        processError(err);
        return;
    }
    let username_found = false;
    dialogues.forEach(user_info => {
        const dialogue = DialogueList.addDialogue(user_info);
        if (user_info.username === username) {
            username_found = true;
            dialogue.select();
        }
    });
    if (username && !username_found) {
        let user_info;
        try {
            user_info = await api("/api/users/partial-info/", {username}, {attempts: 100});
        } catch (err) {
            processError(err);
            return;
        }
        DialogueList.addDialogue(user_info).select();
    }
}

page_loading.show();
load().then(() => page_loading.hide());

Updates.register("messaging.new", msg => {
    // noinspection JSUnresolvedReference
    const interlocutor = msg.interlocutor;
    if (!DialogueList.dialogues[interlocutor.id]) DialogueList.addDialogue(interlocutor);
    else DialogueList.dialogues[interlocutor.id].addMessage(msg);
});
import {api, processError} from "../api/api.js";
import {formatTimestamp, page_loading} from "../api/ui.js";
import {PushOnlyDeque} from "../deque.js";
import {Updates} from "../updates/updates.js";

// select HTML elements
const no_selected_dialogue = document.getElementById("no-selected-dialogue");
const dialogue_title = document.getElementById("dialogue-title");
const message_input_field = document.getElementById("message-input-field");
const messages_area = document.getElementById("messages-area");
const message_sentinel = document.getElementById("message-sentinel");
const message_input_form = document.getElementById("message-input-form");

function adjustMessageInputFieldHeight() {
    // make sure the textarea field is tall enough to contain all text, but is not taller than necessary
    // if height set by this function is greater than max-height, a scroll bar appears automatically
    message_input_field.style.height = "auto"; // reset height for field to shrink if necessary
    message_input_field.style.height = message_input_field.scrollHeight + "px"; // set height to necessary height
}

function setInputValue(value) {
    // set value of the message input field and adjust its height
    message_input_field.value = value;
    adjustMessageInputFieldHeight();
}

// keep message input field's height adjusted to its input length
message_input_field.addEventListener("input", adjustMessageInputFieldHeight);

class Message {
    // class to store message info and create HTML element
    constructor(message_info) {
        this.info = message_info;

        // create HTML element
        this.element = document.createElement("div");
        this.element.classList.add("message");
        // noinspection JSUnresolvedReference
        if (message_info.is_own) this.element.classList.add("own");
        this.sent_at = document.createElement("div");
        this.sent_at.classList.add("sent-at");
        this.sent_at.innerText = formatTimestamp(message_info.sent_at); // add formatted timestamp
        this.content = document.createElement("div");
        this.content.classList.add("message-content");
        this.content.innerText = message_info.content;

        this.element.append(this.sent_at, this.content);
    }
}

class Dialogue {
    // class to store dialogue info and manage message loading and display messages

    // static members:
    static check_sentinel_interval_id = null;
    static loading_controller = null;

    static get loading() {
        // return true if any dialogue is loading messages and request has not been aborted
        return !!Dialogue.loading_controller && !Dialogue.loading_controller.signal.aborted;
    }

    messages = new PushOnlyDeque();
    draft = ""; // store draft saved in the dialogue
    all_messages_loaded = false;

    constructor(user_info) {
        // create a dialogue
        this.info = user_info;

        // create HTML element
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

        // listen for selection
        this.input.addEventListener("input", () => this.onSelect(), params);

        DialogueList.element.prepend(this.element); // add to the top
    }

    get unread_messages_count() {
        // return the number of unread messages in the dialogue
        return this.info.unread_messages_count;
    }

    set unread_messages_count(value) {
        // change the number of unread message in the dialogue
        this.info.unread_messages_count = value;
        this.counter.innerText = value || ""; // hide notification if 0
    }

    // noinspection JSUnusedGlobalSymbols
    abort_input() {
        // remove event listener on selection
        this.input_controller.abort();
    }

    saveDraft() {
        // save draft for this dialogue
        this.draft = message_input_field.value;
        setInputValue(""); // clear input field
    }

    deselect(options) {
        // deselect this dialogue
        if (DialogueList.selected !== this) return; // already not selected
        const { // unpack parameters
            all = true, // deselect all dialogues and clean up if true
            push_state = true, // push browser history state
        } = options;
        if (all) {
            // if push_state, change url in place without reloading the page
            if (push_state) history.pushState({}, "", "/message/");
            document.title = "Messaging — Sodia"; // set document title
            DialogueList.selected = null;
            this.input.checked = false; // uncheck radio input for this dialogue
            no_selected_dialogue.hidden = false; // show message "no dialogue selected"
        }
        this.saveDraft(); // save current dialogue's draft
        Dialogue.loading_controller?.abort(); // if loading messages, abort request
    }

    select(push_state = true) {
        // select dialogue
        this.input.checked = true; // check radio input for this dialogue
        void this.onSelect(push_state); // call selection callback
    }

    onSelect(push_state = true) {
        // handle dialogue selection
        DialogueList.selected?.deselect({all: false}); // deselect currently selected dialogue if exists
        DialogueList.selected = this;
        // if push_state, change url in place without reloading the page
        if (push_state) history.pushState({}, "", `/message/${this.info.username}/`);
        // noinspection JSUnresolvedReference
        document.title = `${this.info.display_name} — Sodia Messaging`; // update document title

        no_selected_dialogue.hidden = true; // hide message "no dialogue selected"
        // noinspection JSUnresolvedReference
        dialogue_title.innerText = this.info.display_name; // show user's name in the selected dialogue's title
        // make dialogue title be a link leading to user's profile
        // noinspection JSUnresolvedReference
        if (this.info.is_activated) dialogue_title.href = `/profile/${this.info.username}/`;
        if (this.unread_messages_count) void this.markRead(); // mark all messages in dialogue as read

        // noinspection JSUnresolvedReference
        if (!this.info.can_message) {
            // message history is visible, but can't send more messages
            message_input_field.disabled = true;
            message_input_form.classList.add("cannot-message");
            setInputValue("You cannot message this person");
        } else {
            // can message
            message_input_field.disabled = false;
            message_input_form.classList.remove("cannot-message");
            setInputValue(this.draft); // load draft
            message_input_field.focus(); // focus on the input field
        }

        messages_area.replaceChildren(message_sentinel); // remove all messages
        const fragment = document.createDocumentFragment(); // create a fragment for optimised insertion
        for (const message of this.messages) { // iterate over PushOnlyDeque
            // noinspection JSUnresolvedReference
            fragment.append(message.element);
        }
        messages_area.insertBefore(fragment, message_sentinel); // display messages
        this.loadMessagesIfNeeded(); // if sentinel is visible and not all messages loaded, load more
    }

    async markRead() {
        // mark dialogue as read
        try {
            await api("/api/messaging/mark-read/", {id: this.info.id}, {attempts: 5});
            this.unread_messages_count = 0; // reset counter
        } catch (err) {
            processError(err); // display request errors
        }
    }

    addMessage(message_info, fragment = null, old = false) {
        // add a message to the dialogue
        const selected = DialogueList.selected === this;
        let message = new Message(message_info);
        if (!old) this.float(); // new message, so move dialogue to the top of the list
        // if dialogue isn't selected and message is new, increment unread messages counter
        if (!selected && !old) this.unread_messages_count++;
        if (old) {
            // old message, so added to the *end* of the container (order is reversed with flex-direction)
            this.messages.pushBack(message); // store message
            if (!selected) return; // if dialogue not selected, nothing to display
            if (fragment) fragment.append(message.element); // using a fragment, so append there
            else messages_area.insertBefore(message.element, message_sentinel); // otherwise put before sentinel
        } else {
            // new message, so added to the *beginning* of the container (order is reversed with flex-direction)
            this.messages.pushFront(message);
            if (!selected) return; // if dialogue not selected, nothing to display
            if (fragment) fragment.prepend(message); // using a fragment, so append there
            else messages_area.prepend(message.element); // otherwise put in the beginning of messages container
            void this.markRead(); // mark dialogue as read immediately
        }
        return message; // return the added message
    }

    async loadMessages() {
        // load and display dialogue messages
        // if already loading, all messages are loaded, or this dialogue isn't selected, return
        if (Dialogue.loading || this.all_messages_loaded || DialogueList.selected !== this) return;
        Dialogue.loading_controller = new AbortController(); // set concurrent loading guard
        const n = 10; // load 10 messages
        try {
            const response = await api("/api/messaging/load-dialogue/",
                {
                    id: this.info.id,
                    start: this.messages.back?.info.id ?? 0, // start from last loaded id or 0 if none loaded yet
                    n,
                },
                {
                    attempts: 20,
                    signal: Dialogue.loading_controller.signal, // signal to abort loading on deselection
                });
            // use a document fragment to optimise messages insertion
            const fragment = document.createDocumentFragment();
            response.forEach(message_info => this.addMessage(message_info, fragment, true)); // add old messages
            if (DialogueList.selected === this) messages_area.insertBefore(fragment, message_sentinel); // show fragment
            // if server returned fewer than messages than expected, then all messages must be loaded
            if (response.length < n) this.all_messages_loaded = true;
        } catch (err) {
            processError(err); // display request errors
        } finally {
            // clear concurrent loading guard if the guard is own
            if (DialogueList.selected === this) Dialogue.loading_controller = null;
        }
        this.loadMessagesIfNeeded(); // load more if sentinel is visible
    }

    loadMessagesIfNeeded() {
        // check if sentinel is visible, and load messages if not all messages are loaded
        // if already loading, all messages are loaded, or this dialogue isn't selected, return
        if (Dialogue.loading || this.all_messages_loaded || DialogueList.selected !== this) return;
        if (message_sentinel.getBoundingClientRect().bottom > messages_area.getBoundingClientRect().top - 550)
            void this.loadMessages(); // sentinel is close to viewport, so load more
    }

    float() {
        // move dialogue to the top of the list
        DialogueList.element.prepend(this.element); // automatically removes the old DOM node
    }

    async sendMessage() {
        // send the message in the message input field
        // do not send if dialogue is not selected or cannot send message
        if (DialogueList.selected !== this || message_input_field.disabled) return;
        const content = message_input_field.value.trim(); // trim whitespace
        if (!content) return; // if message is empty (whitespace-only), don't send
        message_input_field.disabled = true; // disable while sending (concurrent submission guard)
        let message;
        try {
            // send message
            message = await api("/api/messaging/send-message/", {
                id: this.info.id,
                content,
            }, {attempts: 1}); // only use one attempt to avoid the risk of sending one message multiple times
        } catch (err) {
            processError(err); // display request errors
            return;
        } finally {
            message_input_field.disabled = false; // clear concurrent submission guard
        }
        setInputValue(""); // clear message input field
        message_input_field.focus(); // focus on the message input field
        this.addMessage(message); // display the newly sent message in the dialogue
        this.float(); // move the dialogue to the top of the list
    }
}


// register callback handler for sentinel coming close to viewport to potentially load more messages
// noinspection JSCheckFunctionSignatures
const messages_area_observer = new IntersectionObserver(
    entries => {
        for (const entry of entries) {
            if (!entry.isIntersecting) {
                // sentinel is leaving viewport proximity, so clear sentinel monitoring interval
                clearInterval(Dialogue.check_sentinel_interval_id);
                continue; // move on to next entry
            }
            // sentinel is entering viewport proximity
            void DialogueList.selected?.loadMessages(); // load more messages
            Dialogue.check_sentinel_interval_id = setInterval(() => { // start monitoring sentinel
                if (DialogueList.selected?.all_messages_loaded) {
                    // loaded all, so stop monitoring
                    // otherwise can run monitoring forever, which is not ideal performance
                    clearInterval(Dialogue.check_sentinel_interval_id);
                    return;
                }
                DialogueList.selected?.loadMessagesIfNeeded(); // check sentinel proximity and load messages
            }, 250);
        }
    },
    {
        root: messages_area,
        rootMargin: "500px 0px 0px 0px", // trigger when sentinel is within 500px to the top from viewport
        delay: 500, // optimise performance by not updating too often
    });
messages_area_observer.observe(message_sentinel); // observe sentinel

class DialogueList {
    // static class for managing list of dialogues

    // define members
    static element = document.getElementById("dialogue-list");
    static dialogues = {};
    static selected = null;

    static addDialogue(user_info) {
        // add a new dialogue to the list
        return this.dialogues[user_info.id] = new Dialogue(user_info);
    }

    static deselect(push_state = true) {
        // deselect all dialogues
        this.selected?.deselect({push_state});
    }
}

// listen for keydown events to deselect dialogues on Escape,
// autofocus on message input field on typing, and send messages on Enter
document.addEventListener("keydown", e => {
    if (["textarea", "select", "button"].includes(e.target.tagName.toLowerCase())
        || e.target.isContentEditable) return; // typing in an input field
    // or typing in an input field which isn't a radio
    // (radio inputs are used for dialogue selection, they shouldn't prevent autofocusing on message input field)
    if (e.target.tagName.toLowerCase() === "input" && e.target.type !== "radio") return;
    // hotkeys other than ctrl+a and ctrl+Enter shouldn't trigger autofocus
    if ((e.ctrlKey && !["a", "Enter"].includes(e.key)) || e.altKey || e.metaKey) return;
    if (e.key === "Tab" || e.key.startsWith("Arrow")) return; // page navigation with keyboard
    // deselect all dialogues on Escape
    if (e.key === "Escape") {
        DialogueList.deselect();
        return;
    }
    // send message on Enter (but not Shift+Enter, which creates a new line)
    if (e.key === "Enter" && !e.shiftKey) {
        void DialogueList.selected?.sendMessage();
        return;
    }
    // autofocus on the input field when user starts typing
    if (DialogueList.selected !== null) message_input_field.focus();
});

// listen to keydown events within message input field to deselect dialogue on Escape and send message on Enter
message_input_field.addEventListener("keydown", e => {
    // deselect all dialogues on Escape
    if (e.key === "Escape") {
        DialogueList.deselect();
        e.stopPropagation(); // do not trigger global listener
        return;
    }
    // send message on Enter (but not Shift+Enter, which creates a new line)
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault(); // do not create a new line
        e.stopPropagation(); // do not trigger global listener
        void DialogueList.selected?.sendMessage();
    }
});

// prevent showing error message on invalid form submission (when message is empty)
message_input_form.addEventListener("invalid", e => e.preventDefault(), {capture: true});

// prevent browser from submitting form, but send message to dialogue
message_input_form.addEventListener("submit", e => {
    e.preventDefault(); // do not submit form
    void DialogueList.selected?.sendMessage();
});

function get_url_username() {
    // extract username from url
    const list = location.pathname.split("/");
    return list[list.findIndex(e => e === "message") + 1] || null;
}

async function load() {
    // load the page
    let dialogues;
    try {
        // load dialogues
        dialogues = await api("/api/messaging/get-dialogues/", {}, {attempts: 100});
    } catch (err) {
        processError(err); // display request errors
        return;
    }
    const username = get_url_username();
    let username_found = false;
    dialogues.forEach(user_info => {
        // add dialogue to the top of list (server returns dialogues with last messages in reverse chronological order)
        const dialogue = DialogueList.addDialogue(user_info);
        if (user_info.username === username) {
            // if url is for a specific dialogue, select it
            username_found = true;
            dialogue.select(false);
        }
    });
    if (username && !username_found) {
        // dialogue that url is for is not found, so create a virtual dialogue
        let user_info;
        try {
            // load interlocutor's info
            user_info = await api("/api/users/partial-info/", {username}, {attempts: 100});
        } catch (err) {
            processError(err); // display request errors
            return;
        }
        DialogueList.addDialogue(user_info).select(); // add virtual dialogue to the list
    }
    // register a callback handler for updates for new messages
    Updates.register("messaging.new", msg => {
        // noinspection JSUnresolvedReference
        const interlocutor = msg.interlocutor;
        // create a new dialogue if doesn't exist
        if (!DialogueList.dialogues[interlocutor.id]) DialogueList.addDialogue(interlocutor);
        else DialogueList.dialogues[interlocutor.id].addMessage(msg);
    });
}

page_loading.show(); // show "loading..." message
load().then(() => page_loading.hide()); // load the page and then hide "loading..." message

// listen for browser history navigation events
addEventListener("popstate", () => {
    const username = get_url_username(); // new requested username
    if (!username) {
        DialogueList.deselect(false); // deselect all dialogues without pushing history state
        return;
    }
    for (const dialogue of Object.values(DialogueList.dialogues)) {
        if (dialogue.info.username === username) {
            dialogue.select(false); // select dialogue without pushing history state
            return;
        }
    }
    location.reload(); // dialogue isn't found, so reload the page (shouldn't happen)
});
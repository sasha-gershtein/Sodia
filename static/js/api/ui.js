// noinspection JSUnusedGlobalSymbols

import {api, processError} from "./api.js";

// +----------------+
// | INFO MESSAGES: |
// +----------------+

const info_box = document.getElementById("info-box"); // container for info messages

export class InfoMessage {
    // info message controller (add / remove / events)
    constructor(message, level, timeout = 10000) {
        this.message = message;
        if (level !== "info" && level !== "warning" && level !== "error" && level !== "success") {
            throw TypeError(`level should be "info", "warning", "error", or "success", not "${level}"`)
        }
        // create and display element
        this.level = level;
        this.element = document.createElement("div");
        this.element.classList.add("info-message");
        this.element.classList.add(this.level);
        this.element.innerHTML = this.message;
        info_box.append(this.element);
        this.displayed = true;
        // listen for clicks and remove
        this.element.addEventListener("click", () => this.remove());
        // remove after timeout if positive (otherwise keep indefinitely until manually removed)
        if (timeout >= 0) setTimeout(() => this.remove(), timeout);
    }

    remove() {
        if (!this.displayed) return; // already removed
        this.element.remove();
        this.displayed = false;
    }
}

// define functions for each message level
export function displayInfo(message, timeout = 10000) {
    return new InfoMessage(message, "info", timeout)
}

export function displayWarning(message, timeout = 10000) {
    return new InfoMessage(message, "warning", timeout)
}

export function displayError(message, timeout = 10000) {
    return new InfoMessage(message, "error", timeout)
}

export function displaySuccess(message, timeout = 10000) {
    return new InfoMessage(message, "success", timeout)
}

// +----------+
// | BUTTONS: |
// +----------+

export class Button {
    // class to attach a callback to a button element or create new
    constructor(options = {}) {
        let { // unpack parameters
            id = null, // button id
            label = null, // text on a button
            callback = () => null, // callback on button press
            classes = [], // classes to add to the button
            create = true, // if false and id is set, will first try to get an existing DOM element
            // otherwise creates new
        } = options;

        if (!create && id) this.button = document.getElementById(id); // try to find an existing button by id
        if (!this.button) {
            // create a new button element
            this.button = document.createElement("button");
            this.button.type = "button";
            if (id) this.button.id = id;
        }
        if (label) this.button.innerText = label;

        this.callback = callback.bind(this); // bind callback to this Button
        classes.forEach(cls => this.button.classList.add(cls)); // add classes

        this.controller = new AbortController(); // controller to remove event listener if needed
        const params = {
            signal: this.controller.signal
        };
        // listen to button presses
        this.button.addEventListener("click", e => this.onClick(e), params);
    }

    abort() {
        // remove event listener
        this.controller.abort();
    }

    appendTo(element) {
        // append button to the end of a container
        element.append(this.button);
    }

    onClick(e) {
        // run callback
        return this.callback(e);
    }

    get disabled() {
        // getter (shorthand for this.button.disabled)
        return this.button.disabled;
    }

    set disabled(value) {
        // setter (shorthand for this.button.disabled)
        this.button.disabled = value;
    }
}

export class LinkButton extends Button {
    // button that works like a link, i.e. redirects to another page
    constructor(options = {}) {
        let { // unpack parameters
            url, // url to redirect to
        } = options;

        options.callback = () => location.href = this.url; // set callback to redirect to url
        super(options);

        this.url = url;
    }
}

export class APIButton extends Button {
    // button that makes an API request on press
    constructor(options = {}) {
        let { // unpack parameters
            url, // url of the API endpoint
            payload = {}, // payload to be sent
            callback = () => null, // callback to be called on success
            success_message = "Success!", // message to be displayed on success
        } = options;

        options.callback = e => this.APICallback(e); // set callback to make an API request
        super(options);

        this.url = url;
        this.payload = payload;
        this.success_message = success_message;
        this.success_callback = callback.bind(this); // bind callback to this APIButton
    }

    async APICallback() {
        // make an API request
        if (this.disabled) return false; // ignore if button is disable
        try {
            this.disabled = true; // disable while loading (set concurrent loading guard)
            // only make one attempt in case the request performs an action which is dangerous to repeat
            this.result = await api(this.url, this.payload, {attempts: 1});
            this.onSuccess(); // call success callback
        } catch (err) {
            // process request error
            return this.onError(err);
        } finally {
            this.disabled = false; // clear concurrent loading guard
        }
    }

    onSuccess() {
        if (this.result.redirect) location.href = this.result.redirect.location; // redirect if required
        if (this.success_message) displaySuccess(this.success_message, 3000); // show a success message if set
        this.success_callback(this.result); // call custom success callback
    }

    onError(err) {
        processError(err); // display request errors
    }
}

export function makeContextMenu(buttons, id = null, classes = [], tag = "div", create = true) {
    // make an element for a hideable context menu and populate with buttons
    let menu = null;
    let wrapper = null;
    if (!create && id) menu = document.getElementById(id); // try to find an existing DOM element
    if (!menu) {
        // create new menu and wrapper
        wrapper = document.createElement("div");
        if (id) wrapper.id = id + "-wrapper";
        wrapper.classList.add("context-menu-wrapper");
        menu = document.createElement(tag);
        if (id) menu.id = id;
        wrapper.append(menu);
    }
    menu.classList.add("context-menu");
    classes.forEach(cls => menu.classList.add(cls)); // add custom classes
    buttons.forEach(button => button.appendTo(menu)); // inset buttons into the menu
    return {menu, wrapper};
}

export class ContextMenuButton extends Button {
    // button to control a context menu (show / hide)
    constructor(options = {}) {
        let { // unpack parameters
            menu, // menu element to show / hide
            hide_on_buttons = true, // hide context menu when a button inside is clicked
            callback = () => null, // custom callback on press
        } = options;

        options.callback = e => this.onClick(e);
        super(options);

        this.success_callback = callback.bind(this); // bind callback to this ContextMenuButton
        this.menu = menu;
        // if menu doesn't have id, generate use own id + "-menu", or generate a random id
        if (!this.menu.id) this.menu.id = (this.id ?? `id-${Math.ceil(Math.random() * 1e5)}`) + "-menu";
        // set accessibility attribute for screen-readers
        this.button.setAttribute("aria-controls", this.menu.id);
        this.expanded = false; // set false to add "aria-expanded" accessibility attribute
        this.hide_on_buttons = hide_on_buttons;

        const params = {
            signal: this.controller.signal,
        };
        // listen for clicks away from the menu and "Escape" clicks to hide the menu
        document.addEventListener("click", e => this.pageClickHandler(e), params);
        document.addEventListener("keydown", e => this.keydownHandler(e), params);
    }

    get expanded() {
        // return true if context menu is displayed
        return !this.menu.hidden;
    }

    set expanded(value) {
        // show / hide context menu
        this.menu.hidden = !value; // show / hide element
        // set accessibility attribute for screen-readers
        this.button.setAttribute("aria-expanded", (!!value).toString());
    }

    toggle() {
        // toggle visibility: show if hidden, hide if shown
        this.expanded = !this.expanded;
    }

    onClick(e) {
        // handle click
        e.stopPropagation(); // don't propagate event (to not catch event with pageClickHandler)
        this.toggle(); // toggle visibility
        this.success_callback(); // call custom callback
    }

    pageClickHandler(e) {
        if (this.menu.parentElement.contains(e.target)) { // clicked within the menu and...
            if (!this.hide_on_buttons) return; // ...should not hide on a button click
            if (!e.target.closest("button")) return; // ...not on a button => don't hide
        }
        this.menu.hidden = true; // hide context menu on a click away
    }

    keydownHandler(e) {
        // hide if "Escape" is pressed
        if (this.expanded && e.key === "Escape") {
            this.expanded = false;
            this.button.focus();
        }
    }
}

// +--------------------+
// | FORMAT TIMESTAMPS: |
// +--------------------+

const time_formatter = new Intl.DateTimeFormat(undefined, { // formats time as 0:12
    hour: "numeric",
    minute: "2-digit",
});

const date_formatter = new Intl.DateTimeFormat("en-GB", { // formats date as 19/03/26
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
});

const birth_date_formatter = new Intl.DateTimeFormat("en-GB");

export function format_birth_date(birth_date) {
    return birth_date_formatter.format(new Date(birth_date))
}

export function formatTimestamp(timestamp) {
    // format timestamp (i.e. for messages)
    // examples:
    // today, 12:34
    // yesterday, 6:00
    // 12.03.26, 0:01

    // define today and yesterday
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);

    const datetime = new Date(timestamp * 1000); // get datetime from timestamp
    const date = new Date(datetime.getFullYear(), datetime.getMonth(), datetime.getDate()); // extract date only

    const time_str = time_formatter.format(datetime); // format time as string
    if (date.getTime() === today.getTime()) {
        // today
        return `today, ${time_str}`;
    }
    if (date.getTime() === yesterday.getTime()) {
        // yesterday
        return `yesterday, ${time_str}`;
    }
    // neither today nor yesterday, write date (use periods for separation)
    return `${date_formatter.format(date).replaceAll("/", ".")}, ${time_str}`;
}

// +-----------------------+
// | HIDEABLE UI ELEMENTS: |
// +-----------------------+


export class HideableElement {
    // class to control HTML element visibility

    // define members
    element;
    #state; // number of times element was requested to be shown

    constructor(id, initial_state = 0) {
        this.element = document.getElementById(id);
        this.#state = initial_state; // assume initially hidden by default
    }

    show() {
        // increment state
        if (this.#state++) return; // if was already shown, return
        this.element.hidden = false; // show
    }

    hide(force = false) {
        if (!this.#state) return; // if already hidden, return
        if (force) this.#state = 0; // set to 0 to hide immediately
        else if (--this.#state) return; // decrement state, and return if still should be shown
        this.element.hidden = true; // hide
    }
}

// define global hideable "loading..." message available on all pages (initially shown)
export const page_loading = new HideableElement("loading", 1);

// hide "loading..." after DOM content is loaded (if other scripts requested to show, will stay shown until they hide)
document.addEventListener("DOMContentLoaded", _ => page_loading.hide());
// noinspection JSUnusedGlobalSymbols

import {api, processError} from "./api.js";

const info_box = document.getElementById("info-box");

export class InfoMessage {
    constructor(message, level, timeout = 10000) {
        this.message = message;
        if (level !== "info" && level !== "warning" && level !== "error" && level !== "success") {
            throw TypeError(`level should be "info", "warning", "error", or "success", not "${level}"`)
        }
        this.level = level;
        this.element = document.createElement("div");
        this.element.classList.add("info-message");
        this.element.classList.add(this.level);
        this.element.innerHTML = this.message;
        info_box.append(this.element);
        this.displayed = true;
        this.element.addEventListener("click", this.remove.bind(this));
        if (timeout >= 0) setTimeout(this.remove.bind(this), timeout);
    }

    remove() {
        if (!this.displayed) return;
        this.element.remove();
        this.displayed = false;
    }
}

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

export class Button {
    constructor(options = {}) {
        let {
            id = null,
            label = null,
            callback = () => null,
            classes = [],
            create = true,
        } = options;

        if (!create && id) this.button = document.getElementById(id);
        if (!this.button) {
            this.button = document.createElement("button");
            this.button.type = "button";
            if (id) this.button.id = id;
        }
        if (label) this.button.innerText = label;

        this.callback = callback.bind(this);
        classes.forEach(cls => this.button.classList.add(cls));

        this.controller = new AbortController();
        const params = {
            signal: this.controller.signal
        };
        this.button.addEventListener("click", this.onClick.bind(this), params);
    }

    abort() {
        this.controller.abort();
    }

    appendTo(element) {
        element.append(this.button);
    }

    onClick(e) {
        return this.callback(e);
    }

    get disabled() {
        return this.button.disabled;
    }

    set disabled(value) {
        this.button.disabled = value;
    }
}

export class LinkButton extends Button {
    constructor(options = {}) {
        let {
            url,
        } = options;

        options.callback = () => location.href = this.url;
        super(options);

        this.url = url;
    }
}

export class APIButton extends Button {
    constructor(options = {}) {
        let {
            url,
            payload = {},
            callback = () => null,
            success_message = "Success!",
        } = options;

        options.callback = (e) => this.APICallback(e);
        super(options);

        this.url = url;
        this.payload = payload;
        this.success_message = success_message;
        this.success_callback = callback.bind(this);
    }

    async APICallback() {
        if (this.disabled) return false;
        try {
            this.disabled = true;
            this.result = await api(this.url, this.payload, {attempts: 1});
            this.onSuccess();
        } catch (err) {
            return this.onError(err);
        } finally {
            this.disabled = false;
        }
    }

    onSuccess() {
        if (this.result.redirect) location.href = this.result.redirect.location;
        if (this.success_message) displaySuccess(this.success_message, 3000);
        this.success_callback(this.result);
    }

    onError(err) {
        processError(err);
    }
}

export function makeContextMenu(buttons, id = null, classes = [], tag = "div", create = true) {
    let menu = null;
    let wrapper = null;
    if (!create && id) menu = document.getElementById(id);
    if (!menu) {
        menu = document.createElement(tag);
        if (id) menu.id = id;
        wrapper = document.createElement("div");
        if (id) wrapper.id = id + "-wrapper";
        wrapper.classList.add("context-menu-wrapper");
        wrapper.append(menu);
    }
    menu.classList.add("context-menu");
    classes.forEach(cls => menu.classList.add(cls));
    buttons.forEach(button => {
        button.appendTo(menu);
    })
    return {menu, wrapper};
}

export class ContextMenuButton extends Button {
    constructor(options = {}) {
        let {
            menu,
            hide_on_buttons = true,
            callback = () => null,
        } = options;

        options.callback = (e) => this.onClick(e);
        super(options);

        this.success_callback = callback;
        this.menu = menu;
        if (!this.menu.id) this.menu.id = (this.id ?? `id-${Math.ceil(Math.random() * 1e5)}`) + "-menu";
        this.button.setAttribute("aria-controls", this.menu.id);
        this.expanded = false;
        this.hide_on_buttons = hide_on_buttons;

        const params = {
            signal: this.controller.signal
        };
        document.addEventListener("click", this.pageClickHandler.bind(this), params)
        document.addEventListener("keydown", this.keydownHandler.bind(this), params)
    }

    get expanded() {
        return !this.menu.hidden;
    }

    set expanded(value) {
        this.menu.hidden = !value;
        this.button.setAttribute("aria-expanded", (!!value).toString());
    }

    toggle() {
        this.expanded = !this.expanded;
    }

    onClick(e) {
        e.stopPropagation();
        this.toggle();
        this.success_callback();
    }

    pageClickHandler(e) {
        if (this.menu.parentElement.contains(e.target)) { // clicked within the menu and...
            if (!this.hide_on_buttons) return; // ...should not hide on a button click
            if (!e.target.closest("button")) return; // ...not on a button => don't hide
        }
        this.menu.hidden = true; // hide on click away
    }

    keydownHandler(e) {
        if (this.expanded && e.key === "Escape") {
            this.expanded = false;
            this.button.focus();
        }
    }
}

const time_formatter = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
});

const date_formatter = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
});

export function formatTimestamp(timestamp) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);

    const datetime = new Date(timestamp * 1000);
    const date = new Date(datetime.getFullYear(), datetime.getMonth(), datetime.getDate());

    const time_str = time_formatter.format(datetime);
    if (date.getTime() === today.getTime()) {
        return `today, ${time_str}`;
    }
    if (date.getTime() === yesterday.getTime()) {
        return `yesterday, ${time_str}`;
    }
    return `${date_formatter.format(date)}, ${time_str}`;
}


export class HideableElement {
    element;
    #state;

    constructor(id, initial_state = 0) {
        this.element = document.getElementById(id);
        this.#state = initial_state;
    }

    show() {
        if (this.#state++) return;
        this.element.hidden = false;
    }

    hide(force = false) {
        if (force) this.#state = 0;
        else if (--this.#state) return;
        this.element.hidden = true;
    }
}

export const page_loading = new HideableElement("loading", 1);

document.addEventListener("DOMContentLoaded", _ => page_loading.hide());
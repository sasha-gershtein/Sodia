// noinspection JSUnusedGlobalSymbols

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
        info_box.appendChild(this.element);
        this.displayed = true;
        this.element.addEventListener("click", this.remove.bind(this));
        if (timeout >= 0) setTimeout(this.remove.bind(this), timeout);
    }

    remove() {
        if (!this.displayed) return;
        info_box.removeChild(this.element);
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
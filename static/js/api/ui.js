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
        setTimeout(this.remove.bind(this), timeout);
    }

    remove() {
        if (!this.displayed) return;
        info_box.removeChild(this.element);
        this.displayed = false;
    }
}

export function displayInfo(message) {
    return new InfoMessage(message, "info")
}

export function displayWarning(message) {
    return new InfoMessage(message, "warning")
}

export function displayError(message) {
    return new InfoMessage(message, "error")
}

export function displaySuccess(message) {
    return new InfoMessage(message, "success")
}
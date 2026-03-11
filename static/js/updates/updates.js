import {api, processError} from "../api/api.js";

export class Updates {
    static polling_interval = 1000;

    static is_polling = false;
    static is_loading = false;
    static polling_timeout_id = null;
    static handlers = {};

    static register(name, handler) {
        if (this.handlers[name]) this.handlers[name].push(handler);
        else this.handlers[name] = [handler];
    }

    static remove(name, handler) {
        const index = this.handlers[name]?.indexOf(handler);
        if (index !== undefined && index >= 0) this.handlers[name].splice(index, 1);
        if (!this.handlers[name].length) delete this.handlers[name];
    }

    static startPolling() {
        this.is_polling = true;
        void this.call();
    }

    static stopPolling() {
        this.is_polling = false;
        if (this.polling_timeout_id) clearTimeout(this.polling_timeout_id);
    }

    static async call() {
        if (this.is_loading || !this.is_polling) return;
        this.is_loading = true;
        try {
            const response = await api("/api/updates/");
            for (const [name, updates] of Object.entries(response)) {
                if (!this.handlers[name]) {
                    console.error(`unregistered update ${name}:`, updates);
                    continue;
                }
                for (const msg of updates) {
                    for (const handler of this.handlers[name]) {
                        try {
                            handler(msg);
                        } catch (err) {
                            console.error("handler exception:", err);
                        }
                    }
                }
            }
        } catch (err) {
            processError(err);
        } finally {
            this.is_loading = false;
            if (this.is_polling) this.polling_timeout_id = setTimeout(() => this.call(), this.polling_interval);
        }
    }
}

function root(msg) {
    if (msg === "REFRESH") location.reload();
    if (msg?.redirect) location.href = msg.redirect.location;
}

Updates.register("root", root);

document.addEventListener("DOMContentLoaded", () => Updates.startPolling());
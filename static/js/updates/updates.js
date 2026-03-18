import {api, processError} from "../api/api.js";
import {displayError} from "../api/ui.js";

export class Updates {
    // static class to register callbacks for updates
    static polling_interval = 1000; // 1-second delay between requests

    // define members
    static is_polling = false;
    static is_loading = false;
    static polling_timeout_id = null;
    static handlers = {};

    static register(name, handler) {
        // register a callback handler for an update event of type name
        if (this.handlers[name]) this.handlers[name].push(handler);
        else this.handlers[name] = [handler];
    }

    static remove(name, handler) {
        // unregister a callback
        const index = this.handlers[name]?.indexOf(handler); // find callback handler
        if (index >= 0) this.handlers[name].splice(index, 1); // remove handler from the list
        if (!this.handlers[name].length) delete this.handlers[name]; // remove list if empty
    }

    static startPolling() {
        this.is_polling = true;
        void this.call();
    }

    // noinspection JSUnusedGlobalSymbols
    static stopPolling() {
        this.is_polling = false;
        if (this.polling_timeout_id) clearTimeout(this.polling_timeout_id); // if waiting for next call, stop
    }

    static async call() {
        // check for new updates
        if (this.is_loading || !this.is_polling) return; // stop if already loading response or polling is off
        this.is_loading = true; // set concurrent loading guard
        try {
            const response = await api("/api/updates/");
            for (const [name, updates] of Object.entries(response)) {
                // for every update
                if (!this.handlers[name]) continue; // if no callbacks are registered for this name, skip
                for (const msg of updates) {
                    for (const handler of this.handlers[name]) {
                        // for every callback registered for this name
                        try {
                            handler(msg); // execute callback
                        } catch (err) {
                            // callback handler raised an exception
                            // display error and call other handlers anyway
                            displayError("An unknown error occurred while processing an update.\n" +
                                "See console for more info");
                            console.error("handler exception:", err);
                        }
                    }
                }
            }
        } catch (err) {
            // display request errors
            processError(err);
        } finally {
            this.is_loading = false; // clear concurrent loading guard
            // set a timeout for next call if still polling
            if (this.is_polling) this.polling_timeout_id = setTimeout(() => this.call(), this.polling_interval);
        }
    }
}

function root(msg) {
    // root callback handler
    if (msg === "REFRESH") location.reload(); // refresh page
    if (msg?.redirect) location.href = msg.redirect.location; // redirect to a new page
}

Updates.register("root", root); // register root callback handler

// start polling after DOM content is loaded
document.addEventListener("DOMContentLoaded", () => Updates.startPolling());
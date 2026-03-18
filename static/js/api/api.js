// noinspection ExceptionCaughtLocallyJS

import {displayError, displayInfo, page_loading} from "./ui.js";

function getCookie(name) {
    // get a cookie with a specified name
    return document.cookie.split("; ") // get list of cookies
        .find(row => row.startsWith(name + "=")) // find the cookie with the right name
        ?.split("=")[1]; // return its value or undefined if not found
}

function get_csrftoken() {
    // extract CSRF protection token from cookies
    return getCookie("csrftoken");
}

function sleep(ms) {
    // wait asynchronously for a specified delay
    // return a Promise which is resolved in ms milliseconds
    return new Promise(resolve => setTimeout(resolve, ms));
}

export class BadAPIResponseError extends Error {
    // error when server returns response in a wrong format
    constructor(message) {
        super(message);
        this.name = "BadAPIResponseError";
    }
}

export class APIError extends Error {
    // error when server returns an annotated error response in the correct format
    constructor(message, reason, code, meta) {
        super(message);
        this.reason = reason;
        this.code = code;
        this.meta = meta;
        this.name = "APIError";
        if (this.meta?.redirect) location.href = this.meta.redirect.location; // redirect if necessary
    }
}

export class MaxRetriesError extends Error {
    // error when a maximum retries count is exceeded in attempt to get a response from the server
    constructor(message) {
        super(message);
        this.name = "MaxRetriesError";
    }
}

export class TimeoutError extends Error {
    // error raised by a single attempt if timeout is exceeded
    constructor(message) {
        super(message);
        this.name = "TimeoutError";
    }
}

async function makeRequest(url, body, timeout = 5000, signal = null) {
    // make a single request attempt

    // handle timeout
    const controller = new AbortController();
    // abort request when timeout is exceeded and raise TimeoutError();
    const timer = setTimeout(() => controller.abort(new TimeoutError()), timeout);

    // handle abortion of a custom external signal
    let abort_handler = null;
    if (signal !== null) {
        // external signal is defined
        if (signal.aborted) {
            // external signal is already aborted, so abort internal controller
            controller.abort(signal.reason);
        } else {
            // listen for external abortion and abort internal controller
            abort_handler = () => controller.abort(signal.reason);
            signal.addEventListener("abort", abort_handler, {once: true});
        }
    }

    try {
        // make request
        return await fetch(url, { // request specified url
            method: "POST", // always use POST HTTP method
            credentials: "same-origin", // include auth cookies when requesting same origin (true for all API)
            headers: {
                "Content-Type": "application/json", // send payload in JSON
                "Accept": "application/json", // request JSON response
                "X-CSRFToken": get_csrftoken(),
            },
            body,
            signal: controller.signal, // signal to abort if needed
        });
    } finally {
        clearTimeout(timer); // if timeout timer hasn't fired, stop it
        if (signal && abort_handler) { // if external signal is defined and hasn't fired, stop listening
            signal.removeEventListener("abort", abort_handler);
        }
    }
}

export async function api(url, payload = {}, options = {}) {
    let { // unpack parameters
        attempts = -1, // use unlimited attempts by default
        timeout = 5000, // 5 seconds default timeout for each attempt
        delay = 200, // delay between attempts
        signal = null, // external abortion signal
    } = options;

    let loading_message = null;
    // show a "loading..." info message if not completed in 500 ms
    const show_loading_timeout_id = setTimeout(() => {
        loading_message = displayInfo("loading...", -1);
    }, 500);

    try {
        const body = JSON.stringify(payload); // convert payload to JSON
        while (attempts !== 0) {
            attempts--;
            let response;
            try {
                // make API request
                response = await makeRequest(url, body, timeout, signal);
            } catch (err) {
                // error occurred and response is not available
                // if external signal isn't aborted, and it isn't a TimeoutError, throw
                if (signal?.aborted || !(err instanceof TimeoutError)) throw err;
                await sleep(delay); // wait for the delay
                continue; // try again
            }

            let parsed;
            try {
                // parse JSON
                parsed = await response.json();
            } catch (err) {
                // response is not in JSON format
                throw new BadAPIResponseError(`Non-JSON response on ${url}`);
            }
            // check for correct format
            if (parsed.success === undefined || parsed.result === undefined || parsed.error === undefined) {
                throw new BadAPIResponseError(`Bad response on ${url}`);
            }

            if (parsed.success) return parsed.result; // success!

            // error response
            const message = parsed.error.message;
            const reason = parsed.error.reason;
            const code = parsed.error.code;
            const meta = parsed.error.meta;
            // check for correct error format
            if (message === undefined || reason === undefined || code === undefined || meta === undefined) {
                throw new BadAPIResponseError(`Bad response on ${url}`);
            }
            throw new APIError(message, reason, code, meta);
        }
        // all attempts used up
        throw new MaxRetriesError("Unsuccessful API request");
    } finally {
        // if completed before "loading..." info message is shown, clear timeout
        clearTimeout(show_loading_timeout_id);
        if (loading_message !== null) loading_message.remove(); // if the message was shown, remove it
    }
}

export function processError(err) {
    // display error messages on exceptions raised by api()
    // returns null if could not connect or response is malformed, and throws exception back otherwise
    if (err instanceof APIError) {
        displayError(err.message);
        throw err;
    }
    if (err instanceof BadAPIResponseError) {
        displayError("The server returned an invalid response. Please try again later.");
        console.error(`${err.name}: ${err.message}`);
        return;
    }
    if (err instanceof MaxRetriesError) {
        displayError("Unable to connect to the server. Please try again later.");
        console.error(`${err.name}: ${err.message}`);
        return;
    }
    throw err;
}

function removePrefix(id, prefix) {
    // remove prefix from an id
    // if id does not start with prefix-, return null
    return prefix == null ? id : (
        id.startsWith(`${prefix}-`) ? id.substring(prefix.length + 1) : null
    );
}

export async function loadTemplate(url, payload = {}, options = {}) {
    // make an api request, and use response fields to populate template fields
    let {
        prefix = null, // template ids prefix (optional but preferred to avoid names clashes)
        title = null, // function to set document title based on response
        translators = {}, // for every field, caller can specify how to transform response value into displayed string
        show_loading = true, // if true, "loading..." message is shown until completion
    } = options;
    if (show_loading) page_loading.show();
    let response;
    try {
        // request doesn't affect server state and page is unusable without loading, so do many attempts
        response = await api(url, payload, {attempts: 100});
    } catch (err) {
        processError(err); // display request errors
        return;
    }
    // select container with template fields (defaults to document if no prefix is used)
    const container = prefix != null ? document.querySelector(`.template-container#${prefix}`) : document;
    container.querySelectorAll(".template").forEach(field => {
        // for each template field
        const id = removePrefix(field.id, prefix)?.replaceAll("-", "_"); // get field id (response key)
        if (!id) return; // skip field with no id
        const value = response[id]; // get value
        // translate value if a translator is given
        // otherwise, try to take value.name.toLowerCase() (often used for Python Enum types)
        const string = translators[id] ? translators[id](value) : value?.name?.toLowerCase() ?? value;
        if (string != null) field.innerText = string; // insert string to the field
    });
    if (title != null) {
        // noinspection JSValidateTypes
        document.title = title(response); // set document title
    }
    if (show_loading) page_loading.hide(); // if showing "loading...", hide
    return response; // return response to be used by further callback handlers
}
// noinspection ExceptionCaughtLocallyJS

"use strict";

import {displayError, displayInfo, hidePageLoading, showPageLoading} from "./ui.js";

function getCookie(name) {
    return document.cookie.split('; ')
        .find(row => row.startsWith(name + "="))
        ?.split("=")[1];
}

function get_csrftoken() {
    return getCookie("csrftoken");
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export class BadAPIResponseError extends Error {
    constructor(message) {
        super(message);
        this.name = "BadAPIResponseError";
    }
}

export class APIError extends Error {
    constructor(message, reason, code, meta) {
        super(message);
        this.reason = reason;
        this.code = code;
        this.meta = meta;
        this.name = "APIError";
        if (this.meta?.redirect) {
            location.href = this.meta.redirect.location;
        }
    }
}

export class MaxRetriesError extends Error {
    constructor(message) {
        super(message);
        this.name = "MaxRetriesError";
    }
}

async function makeRequest(url, body, timeout = 5000) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeout)

    try {
        return await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CSRFToken": get_csrftoken(),
            },
            body: body,
            signal: controller.signal,
        });
    } finally {
        clearTimeout(timer);
    }
}

export async function api(url, payload = {}, options = {}) {
    let {
        attempts = -1,
        timeout = 5000,
        delay = 200,
    } = options;
    let loading_message = null;
    const show_loading_timeout_id = setTimeout(() => {
        loading_message = displayInfo("loading...", -1);
    }, 250);
    try {
        const body = JSON.stringify(payload);
        while (attempts !== 0) {
            attempts--;
            try {
                const response = await makeRequest(url, body, timeout);
                let parsed = {}
                try {
                    parsed = await response.json();
                } catch (err) {
                    throw new BadAPIResponseError(`Non-JSON response on ${url}`);
                }
                if (parsed.success === undefined || parsed.result === undefined || parsed.error === undefined) {
                    throw new BadAPIResponseError(`Bad response on ${url}`);
                }
                if (parsed.success) return parsed.result;
                const message = parsed.error.message;
                const reason = parsed.error.reason;
                const code = parsed.error.code;
                const meta = parsed.error.meta;
                if (message === undefined || reason === undefined || code === undefined || meta === undefined) {
                    throw new BadAPIResponseError(`Bad response on ${url}`);
                }
                throw new APIError(message, reason, code, meta);
            } catch (err) {
                if (!((err.name === "AbortError") || (err instanceof TypeError)))
                    throw err;
            }
            await sleep(delay);
        }
        throw new MaxRetriesError("Unsuccessful API request");
    } finally {
        clearTimeout(show_loading_timeout_id);
        if (loading_message !== null) loading_message.remove();
    }
}

export function processError(err) {
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
    return prefix == null ? id : (
        id.startsWith(`${prefix}-`) ? id.substring(prefix.length + 1) : null
    );
}

export async function loadTemplate(url, payload = {}, options = {}) {
    let {
        prefix = null,
        title = null,
        translators = {},
    } = options;
    showPageLoading();
    let response;
    try {
        response = await api(url, payload, {attempts: 100});
    } catch (err) {
        processError(err);
        return;
    }
    const container = prefix != null ? document.querySelector(`.template-container#${prefix}`) : document;
    container.querySelectorAll(".template").forEach(field => {
        const id = removePrefix(field.id, prefix)?.replaceAll("-", "_");
        if (!id) return;
        const value = response[id];
        const string = translators[id] ? translators[id](value) : value?.name?.toLowerCase() ?? value;
        if (string != null) field.innerText = string;
    });
    if (title != null) { // noinspection JSValidateTypes
        document.title = title(response);
    }
    hidePageLoading();
    return response;
}
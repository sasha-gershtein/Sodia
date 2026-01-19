// noinspection ExceptionCaughtLocallyJS

"use strict";

const error_box = document.getElementById("error-box");
let hide_error_box = 0;

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

export function displayError(message) {
    if (!error_box) {
        alert(`error: ${message}`);
        return;
    }
    error_box.innerText = message;
    error_box.classList.remove("hidden");
    hide_error_box = new Date().getTime() + 4900;
    setTimeout(function () {
        if (hide_error_box < new Date().getTime()) error_box.classList.add("hidden");
    }, 5000)
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
    const body = JSON.stringify(payload);
    const full_url = url;
    while (attempts !== 0) {
        attempts--;
        try {
            const response = await makeRequest(full_url, body, timeout);
            let parsed = {}
            try {
                parsed = await response.json();
            } catch (err) {
                throw new BadAPIResponseError(`Non-JSON response on ${full_url}`);
            }
            if (parsed.success === undefined || parsed.result === undefined || parsed.error === undefined) {
                throw new BadAPIResponseError(`Bad response on ${full_url}`);
            }
            if (parsed.success) return parsed.result;
            const message = parsed.error.message;
            const reason = parsed.error.reason;
            const code = parsed.error.code;
            const meta = parsed.error.meta;
            if (message === undefined || reason === undefined || code === undefined || meta === undefined) {
                throw new BadAPIResponseError(`Bad response on ${full_url}`);
            }
            throw new APIError(message, reason, code, meta);
        } catch (err) {
            if (!((err.name === "AbortError") || (err instanceof TypeError)))
                throw err;
        }
        await sleep(delay);
    }
    throw new MaxRetriesError("Unsuccessful API request");
}
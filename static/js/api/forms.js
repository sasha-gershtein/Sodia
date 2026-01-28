// noinspection JSUnusedGlobalSymbols, JSUnusedLocalSymbols

import {api, APIError, BadAPIResponseError, displayError, MaxRetriesError} from "./api.js";

function trim(string, chars) {
    let i = 0;
    let j = string.length - 1;
    while (i <= j && chars.includes(string[i])) i++;
    while (i <= j && chars.includes(string[j])) j--;
    return string.substring(i, j + 1);
}

export class Field {
    constructor(input, form, signal = null) {
        this.input = input;
        this.form = form;
        this.name = input.name;
        this.label = trim((this.input.labels?.[0]?.textContent || this.name).toLowerCase(), " :.,=?!()*<>[]{}");
        this.type = input.type;
        this.error_list_element = this.input.parentElement.querySelector(".errorlist");
        this.custom_errors = [];

        this._is_showErrors_event = false;

        this.ERROR_MESSAGES = {
            badInput: () => "the value you entered cannot be parsed",
            patternMismatch: () => `please enter a valid ${this.label}`,
            rangeOverflow: () => `${this.label} can't be greater than ${this.input.max}`,
            rangeUnderflow: () => `${this.label} can't be smaller than ${this.input.min}`,
            stepMismatch: () => `${this.label} must be a multiple of ${this.input.step || "1"}` +
                `${this.input.min ? ` above ${this.input.min}` : ""}`,
            tooLong: () => `${this.label} can't be longer than ${this.input.maxLength} characters long`,
            tooShort: () => `${this.label} must be at least ${this.input.minLength} characters long`,
            typeMismatch: () => `please enter a valid ${this.label}`,
            valueMissing: () => `${this.label} is required`,
        }

        this.controller = new AbortController();
        const options = {
            signal: this.controller.signal
        };
        signal?.addEventListener("abort", this.abort.bind(this));

        this.input.addEventListener("beforeinput", this.onBeforeInput.bind(this), options);
        this.input.addEventListener("input", this.onInput.bind(this), options);
        this.input.addEventListener("change", this.onChange.bind(this), options);
        this.input.addEventListener("invalid", this.onInvalid.bind(this), options);
    }

    abort() {
        this.controller.abort();
    }

    getValue() {
        return this.input.value;
    }

    displayError(message) {
        let error = document.createElement("li");
        error.innerText = message;
        this.error_list_element?.appendChild(error);
    }

    showErrors(exclude_required = false) {
        if (this._is_showErrors_event) return; // a loop is detected, do not run again!
        this.clearErrors();
        if (this.input.validity.valid) return;
        if (this.error_list_element) this.error_list_element.innerHTML = "";
        for (const type in this.ERROR_MESSAGES) {
            if (this.input.validity[type]) {
                if (exclude_required && type === "valueMissing") continue;
                this.displayError(this.ERROR_MESSAGES[type]());
            }
        }
        for (const message of this.custom_errors) {
            this.displayError(message);
        }
        this.input.classList.add("show-errors");
        this.error_list_element?.classList.add("show-errors");
        this._is_showErrors_event = true;
        try {
            this.input.reportValidity();
        } finally {
            this._is_showErrors_event = false;
        }
    }

    clearErrors() {
        this.error_list_element?.classList.remove("show-errors");
        this.input.classList.remove("show-errors");
        if (this.error_list_element) {
            this.error_list_element.innerHTML = "";
        }
    }

    addError(message) {
        this.custom_errors.push(message);
        this.input.setCustomValidity(message);
    }

    validate() {
        this.custom_errors = [];
        // do custom validation ...
        // on error call this.addError()
        if (!this.custom_errors.length) this.input.setCustomValidity("");
        return this.input.validity.valid;
    }

    onBeforeInput(e) {
        // filter out invalid input
    }

    onInput(e) {
        // run silent validation
        if (this.validate()) this.clearErrors();
    }

    onChange(e) {
        // show validation result
        this.showErrors(true);
    }

    onInvalid(e) {
        // display errors
        if (this.error_list_element) {
            e.preventDefault(); // hide default tooltip
            this.showErrors();
        }
    }
}

class FormValidationField extends Field {
    constructor(form, signal = null) {
        let input = form.form.querySelector(`input[type='hidden'][name='${form.form.id}_form_validation_field']`);
        if (!input) {
            input = document.createElement("input");
            input.setAttribute("type", "hidden");
            input.setAttribute("name", `${form.form.id}_form_validation_field`);
            form.form.appendChild(input);
        }
        super(input, form, signal);
        this.error_list_element = form.error_list_element;
    }

    showErrors(_exclude_required = false) {
        this.clearErrors();
        if (this.input.validity.valid) return;
        for (const message of this.custom_errors) {
            if (!this.error_list_element) displayError(message);
            else this.displayError(message);
        }
        this.error_list_element?.classList.add("show-errors");
    }

    onInvalid(e) {
        e.preventDefault();
    }
}

export class Form {
    constructor(id, signal = null) {
        this.form = document.getElementById(id);
        if (!this.form) throw ReferenceError(`The form with id ${id} does not exist`);

        this.action = this.form.action;
        this.is_submitting = false;
        this.result = null;

        this.controller = new AbortController();
        const options = {
            signal: this.controller.signal
        };
        signal?.addEventListener("abort", this.abort.bind(this));

        this.error_list_element = this.form.querySelector(".errorlist.nonfield");
        this.form_validation_field = new FormValidationField(this, this.controller.signal);

        this.fields = {};
        for (let input of this.form) {
            this.addField(input);
        }

        this.form.addEventListener("beforeinput", this.onBeforeInput.bind(this), options);
        this.form.addEventListener("input", this.onInput.bind(this), options);
        this.form.addEventListener("change", this.onChange.bind(this), options);
        this.form.addEventListener("reset", this.onReset.bind(this), options);
        this.form.addEventListener("invalid", this.onInvalid.bind(this), options);
        this.form.addEventListener("submit", this.onSubmit.bind(this), options);
    }

    abort() {
        this.controller.abort();
    }

    removePrefix(name) {
        return name.startsWith(`${this.form.id}-`) ? name.substring(this.form.id.length + 1) : name;
    }

    addField(input) {
        if (!input.name) return;
        if (input === this.form_validation_field.input) return;
        let name = this.removePrefix(input.name);
        if (input.type !== "submit") this.fields[name] = new Field(input, this, this.controller.signal);
    }

    * [Symbol.iterator]() {
        for (const name in this.fields) {
            yield this.fields[name];
        }
    }

    addError(message) {
        this.form_validation_field.addError(message);
    }

    showErrorsForm() {
        this.form_validation_field.showErrors();
    }

    showErrors(exclude_required = false) {
        for (const field of this) {
            field.showErrors(exclude_required);
        }
        this.showErrorsForm();
    }

    validateForm() {
        return this.form_validation_field.validate();
    }

    validate() {
        let valid = true;
        for (const field of this) {
            valid &&= field.validate();
        }
        valid &&= this.validateForm();
        return valid;
    }

    clearErrorsForm() {
        this.form_validation_field.clearErrors();
    }

    clearErrors() {
        for (const field of this) field.clearErrors();
        this.form_validation_field.clearErrors();
    }

    getData() {
        let data = {};
        for (const field of this) {
            data[field.name] = field.getValue();
        }
        return data;
    }

    onBeforeInput(e) {
        if (this.is_submitting) e.preventDefault();
    }

    onInput(e) {
        this.validateForm();
    }

    onChange(e) {
        this.showErrorsForm();
    }

    onReset(e) {
    }

    onInvalid(e) {
    }

    async onSubmit(e) {
        e.preventDefault();
        if (this.is_submitting) return;
        if (!this.form_validation_field.input.validity.valid) {
            this.form_validation_field.showErrors();
            return;
        }
        this.is_submitting = true;
        try {
            this.result = await api(this.action, this.getData(), {attempts: 5});
            if (this.result.redirect) location.href = this.result.redirect.location;
        } catch (err) {
            if (err instanceof APIError) {
                if (err.code !== 499) {
                    displayError(err.message);
                    throw err;
                }
                for (const [field, errors] of Object.entries(err.meta)) {
                    for (const message of errors) {
                        if (field === "__all__" || !this.fields[field]) {
                            this.addError(message);
                            continue;
                        }
                        this.fields[field].addError(message);
                    }
                }
                this.showErrors();
                return;
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
        } finally {
            this.is_submitting = false;
        }
    }
}
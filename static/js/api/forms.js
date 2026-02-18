// noinspection JSUnusedGlobalSymbols, JSUnusedLocalSymbols

import {api, APIError, BadAPIResponseError, MaxRetriesError} from "./api.js";
import {displayError, displaySuccess} from "./ui.js";

function trim(string, chars) {
    let i = 0;
    let j = string.length - 1;
    while (i <= j && chars.includes(string[i])) i++;
    while (i <= j && chars.includes(string[j])) j--;
    return string.substring(i, j + 1);
}

export class Field {
    input;
    form;
    name;
    label;
    type;
    error_list_element;
    custom_errors = [];
    is_changed = false;
    is_submitting = false;
    #is_showErrors_event;
    ERROR_MESSAGES;
    controller;

    constructor(input, form, signal = null) {
        this.input = input;
        this.form = form;
        this.name = input.name;
        this.label = trim((this.input.labels?.[0]?.textContent || this.name).toLowerCase(), " \t\n\r:.,=?!()*<>[]{}");
        this.type = input.type;
        this.error_list_element = this.input.closest('.field')?.querySelector(".errorlist");

        this.#is_showErrors_event = false;

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
        const params = {
            signal: this.controller.signal
        };
        signal?.addEventListener("abort", this.abort.bind(this));

        this.addEventListeners(this.input, params);
    }

    abort() {
        this.controller.abort();
    }

    addEventListeners(element, params) {
        element.addEventListener("beforeinput", this.onBeforeInput.bind(this), params);
        element.addEventListener("input", this.onInput.bind(this), params);
        element.addEventListener("change", this.onChange.bind(this), params);
        element.addEventListener("invalid", this.onInvalid.bind(this), params);
    }

    get value() {
        return this.input.value;
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        this.input.value = value;
    }

    displayError(message) {
        let error = document.createElement("li");
        error.innerText = message;
        this.error_list_element?.appendChild(error);
    }

    showErrors(exclude_required = false) {
        if (this.#is_showErrors_event) return; // a loop is detected, do not run again!
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
        this.#is_showErrors_event = true;
        try {
            this.input.reportValidity();
        } finally {
            this.#is_showErrors_event = false;
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

    disable() {
        this.input.disabled = true;
    }

    enable() {
        this.input.disabled = false;
    }

    onBeforeInput(e) {
        // filter out invalid input
    }

    onInput(e) {
        // run silent validation
        this.is_changed = true;
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

export class CheckboxField extends Field { // this.type === "checkbox"
    get value() {
        return this.input.checked;
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        this.input.checked = value;
    }
}

export class MultiselectField extends Field { // this.type === "select-multiple"
    get value() {
        let options = [];
        for (const option of this.input.options) {
            if (option.selected) options.push(option.value);
        }
        return options;
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        let selected = value.map(option => option.id ?? option);
        for (const option of this.input.options) {
            option.selected = selected.includes(parseInt(option.value));
        }
    }
}

export class MultiCheckboxField extends Field { // this.type === "checkbox"
    options;

    constructor(...args) {
        super(...args);
        this.options = this.form.form.querySelectorAll(`input[type="checkbox"][name="${this.input.name}"]`);
        const params = {
            signal: this.controller.signal
        };
        for (const element of this.options) {
            if (element === this.input) continue;
            this.addEventListeners(element, params);
        }
    }

    get value() {
        let options = [];
        for (const option of this.options) {
            if (option.checked) options.push(option.value);
        }
        return options;
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        if (value === null) {
            for (const option of this.options) option.checked = false;
        }
        let selected = value.map(option => option.id ?? option);
        for (const option of this.options) {
            option.checked = selected.includes(parseInt(option.value));
        }
    }

    disable() {
        for (const option of this.options) {
            option.disabled = true;
        }
    }

    enable() {
        for (const option of this.options) {
            option.disabled = false;
        }
    }
}

export class SelectField extends Field { // this.type === "select-one"
    get value() {
        for (const option of this.input.options) {
            if (option.selected) return option.value;
        }
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        if (value === null) {
            for (const option of this.input.options) option.selected = false;
            return;
        }
        for (const option of this.input.options) {
            option.selected = parseInt(option.value) === (value.id ?? option);
        }
    }
}

export class RadioField extends Field { // this.type === "radio"
    options;

    constructor(...args) {
        super(...args);
        this.options = this.form.form.querySelectorAll(`input[type="radio"][name="${this.input.name}"]`);
        const params = {
            signal: this.controller.signal
        };
        for (const element of this.options) {
            if (element === this.input) continue;
            this.addEventListeners(element, params);
        }
    }

    get value() {
        for (const option of this.options) {
            if (option.checked) return option.value;
        }
        return null;
    }

    set value(value) {
        this.is_changed = false;
        this.clearErrors();
        if (value === null) {
            for (const option of this.options) option.checked = false;
            return;
        }
        for (const option of this.options) {
            if (option.value === (value.id ?? option)) {
                option.checked = true;
                return;
            }
        }
    }

    disable() {
        for (const option of this.options) {
            option.disabled = true;
        }
    }

    enable() {
        for (const option of this.options) {
            option.disabled = false;
        }
    }
}

class FormValidationField extends Field {
    constructor(form, signal = null) {
        let input = form.form.querySelector(`input[type='hidden'][name='${form.form.id}_form_validation_field']`);
        if (!input) {
            input = document.createElement("input");
            input.type = "hidden";
            input.name = `${form.form.id}_form_validation_field`;
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
    form;
    submit_button = null;
    reset_button = null;
    success_message = "Success!";
    action;
    disabled = false;
    result = null;
    controller;
    error_list_element;
    form_validation_field;
    fields;

    constructor(id, signal = null) {
        this.form = document.getElementById(id);
        if (!this.form) throw ReferenceError(`The form with id ${id} does not exist`);

        this.action = this.form.action;

        this.controller = new AbortController();
        const params = {
            signal: this.controller.signal
        };
        signal?.addEventListener("abort", this.abort.bind(this));

        this.error_list_element = this.form.querySelector(".errorlist.nonfield");
        this.form_validation_field = new FormValidationField(this, this.controller.signal);

        this.fields = {};
        for (let input of this.form) {
            this.addField(input);
        }

        this.form.addEventListener("beforeinput", this.onBeforeInput.bind(this), params);
        this.form.addEventListener("input", this.onInput.bind(this), params);
        this.form.addEventListener("change", this.onChange.bind(this), params);
        this.form.addEventListener("reset", this.onReset.bind(this), params);
        this.form.addEventListener("invalid", this.onInvalid.bind(this), params);
        this.form.addEventListener("submit", this.onSubmit.bind(this), params);
    }

    abort() {
        this.controller.abort();
    }

    removePrefix(name) {
        return name.startsWith(`${this.form.id}-`) ? name.substring(this.form.id.length + 1) : name;
    }

    addField(input) {
        if (input === this.form_validation_field.input) return;
        if (input.type === "submit") {
            this.submit_button = input;
            return;
        }
        if (input.type === "reset") {
            this.reset_button = input;
            return;
        }
        const name = this.removePrefix(input.name);
        if (!name) return;
        if (name in this.fields) return;
        switch (input.type) {
            case "checkbox":
                if (input.dataset.multiple !== undefined) {
                    this.fields[name] = new MultiCheckboxField(input, this, this.controller.signal);
                    break;
                }
                this.fields[name] = new CheckboxField(input, this, this.controller.signal);
                break;
            case "select-multiple":
                this.fields[name] = new MultiselectField(input, this, this.controller.signal);
                break;
            case "select-one":
                this.fields[name] = new SelectField(input, this, this.controller.signal);
                break;
            case "radio":
                this.fields[name] = new RadioField(input, this, this.controller.signal);
                break;
            default:
                this.fields[name] = new Field(input, this, this.controller.signal);
        }
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

    get data() {
        let data = {};
        for (const field of this) {
            data[field.name] = field.value;
            field.is_changed = false;
            if (this.disabled) field.is_submitting = true;
        }
        return data;
    }

    clear() {
        this.form.reset();
        this.clearErrors();
    }

    disable(disable_fields = true) {
        // disable form during submission
        // unsuitable for regular disabling as is
        // code relies on .disabled meaning 'is being submitted'
        this.disabled = true;
        if (this.submit_button) this.submit_button.disabled = true;
        if (disable_fields) {
            for (const field of this) {
                field.disable();
            }
        }
    }

    enable() {
        this.disabled = false;
        if (this.submit_button) this.submit_button.disabled = false;
        for (const field of this) {
            field.enable();
        }
    }

    onBeforeInput(e) {
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
        if (this.disabled) return false;
        if (!this.validate()) {
            return false;
        }
        try {
            this.disable();
            this.result = await api(this.action, this.data, {attempts: 5});
            return this.onSuccess();
        } catch (err) {
            return this.onError(err);
        } finally {
            this.enable();
        }
    }

    onSuccess(show_message = true, clear = true) {
        for (const field of this) field.is_submitting = false;
        if (this.result.redirect) {
            location.href = this.result.redirect.location;
            return false;
        }
        if (show_message && this.success_message) displaySuccess(this.success_message, 3000);
        if (clear) this.clear();
        return false;
    }

    onError(err) {
        for (const field of this) {
            if (field.is_submitting) field.is_changed = true;
            field.is_submitting = false;
        }
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
        }
        if (err instanceof BadAPIResponseError) {
            displayError("The server returned an invalid response. Please try again later.");
            console.error(`${err.name}: ${err.message}`);
            return false;
        }
        if (err instanceof MaxRetriesError) {
            displayError("Unable to connect to the server. Please try again later.");
            console.error(`${err.name}: ${err.message}`);
            return false;
        }
        throw err;
    }
}

export class UpdateForm extends Form {
    #init_promise;
    #polling_interval_id;
    #is_syncing = false;
    #autosave_button;
    #is_autosave = false;
    success_message = "Data updated successfully";

    constructor(...args) {
        super(...args);
        this.disable(true);
        this.#autosave_button = document.createElement("input");
        this.#autosave_button.type = "submit";
        this.#autosave_button.hidden = true;
        this.form.appendChild(this.#autosave_button);
        this.#init_promise = this.sync(true).then(this.afterInit.bind(this));
    }

    async sync(ignore_disabled = false) {
        if (this.#is_syncing || (this.disabled && !ignore_disabled)) return;
        try {
            this.#is_syncing = true;
            this.result = await api(this.action, {}, {attempts: 5});
            this.updateFields();
        } catch (err) {
            this.onError(err);
            throw err;
        } finally {
            this.#is_syncing = false;
        }
    }

    disable(disable_fields = false) {
        super.disable(disable_fields);
    }

    afterInit() {
        this.enable();
        this.#polling_interval_id = setInterval(this.sync.bind(this), 10000);
    }

    abort() {
        super.abort();
        clearInterval(this.#polling_interval_id);
    }

    waitInit() {
        return this.#init_promise;
    }

    get data() {
        let data = {};
        for (const field of this) {
            if (field.is_changed) {
                data[field.name] = field.value;
                field.is_changed = false;
                if (this.disabled) field.is_submitting = true;
            }
        }
        return data;
    }

    updateFields() {
        for (const [field, value] of Object.entries(this.result)) {
            if (field in this.fields &&
                !this.fields[field].is_changed && this.fields[field].input !== document.activeElement) {
                this.fields[field].value = value;
            }
        }
    }

    clear() {
        for (const field of this) field.is_changed = false;
        void this.sync();
        this.clearErrors();
    }

    onChange(e) {
        super.onChange(e);
        if (!e.isTrusted) return;
        this.form.requestSubmit(this.#autosave_button);
    }

    async onSubmit(e) {
        this.#is_autosave = e.submitter === this.#autosave_button;
        if (await super.onSubmit(e)) {
            this.form.requestSubmit(this.#autosave_button);
        }
        return false;
    }

    onSuccess(show_message = true, clear = false) {
        let changed = false;
        for (const field of this) {
            changed ||= field.is_changed;
            field.is_submitting = false;
        }
        super.onSuccess(show_message && !this.#is_autosave, clear);
        this.updateFields();
        return changed;
    }

    onError(err) {
        let changed = false;
        for (const field of this) {
            changed ||= field.is_changed;
            if (field.is_submitting) field.is_changed = true;
            field.is_submitting = false;
        }
        super.onError(err);
        return changed;
    }
}
// noinspection JSUnusedGlobalSymbols, JSUnusedLocalSymbols

import {api, APIError, processError} from "./api.js";
import {displayError, displaySuccess} from "./ui.js";

function trim(string, chars) {
    // return a string with characters from chars removed from its ends
    // calling substring once ensures that this function has O(n) time complexity, not O(n^2)
    let i = 0; // left side boundary
    let j = string.length - 1; // right side boundary
    while (i <= j && chars.includes(string[i])) i++;
    while (i <= j && chars.includes(string[j])) j--;
    return string.substring(i, j + 1); // return the new string
}

export class Field {
    // class to control an input element in a form

    // define members
    input; // HTML <input> element or similar
    form; // Form class instance of this Field
    name; // "name" attribute
    label; // human-readable label to refer to the field
    type; // "type" attribute
    error_list_element; // element to which field validation errors are added
    custom_errors = []; // list of custom field validation errors
    is_changed = false; // flag set if value is changed by the user since being reset
    is_submitting = false; // flag set if the value is being currently submitted to the server
    #is_showErrors_event = false; // flag to prevent infinite recursion when showing errors
    ERROR_MESSAGES; // list of functions to generate an error message for each type of default errors
    controller; // controller to abort all event listeners

    constructor(input, form, signal = null) {
        // configurate field's settings and
        this.input = input;
        this.form = form;
        this.name = input.name;
        // take first <label> if exists, or name attribute; trim whitespace and punctuation
        this.label = trim((this.input.labels?.[0]?.textContent || this.name).toLowerCase(), " \t\n\r:.,=?!()*<>[]{}");
        this.type = input.type;
        this.error_list_element = this.input.closest('.field')?.querySelector(".errorlist");

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
            signal: this.controller.signal,
        };
        signal?.addEventListener("abort", () => this.abort(), params);

        this.addEventListeners(this.input, params);
    }

    abort() {
        // remove all event listeners
        this.controller.abort();
    }

    addEventListeners(element, params) {
        // add all event listeners
        element.addEventListener("beforeinput", e => this.onBeforeInput(e), params); // before field's value is edited
        element.addEventListener("input", e => this.onInput(e), params); // after field's value is edited
        // after a change to field's value is committed (field is edited and unfocused)
        element.addEventListener("change", e => this.onChange(e), params);
        element.addEventListener("invalid", e => this.onInvalid(e), params); // field validation is failed
    }

    get value() {
        // return value if the field
        return this.input.value;
    }

    set value(value) {
        // set value of the field
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        this.input.value = value;
    }

    displayError(message) {
        // add error with a specified message to the error_list_element
        let error = document.createElement("li");
        error.innerText = message;
        this.error_list_element?.append(error);
    }

    showErrors(exclude_required = false) {
        if (this.#is_showErrors_event) return; // a loop is detected, do not run again!
        this.clearErrors(); // clear errors already displayed
        if (this.input.validity.valid) return; // if valid, return
        for (const type in this.ERROR_MESSAGES) {
            // for each error type, if this error is active, display its message
            if (this.input.validity[type]) {
                // ignore error for missing required fields if exclude_required is set
                if (exclude_required && type === "valueMissing") continue; // skip
                this.displayError(this.ERROR_MESSAGES[type]()); // display the error
            }
        }
        // display custom errors
        for (const message of this.custom_errors) {
            this.displayError(message);
        }
        // display error element
        this.input.classList.add("show-errors");
        this.error_list_element?.classList.add("show-errors");
        this.#is_showErrors_event = true; // add infinite recursion guard
        try {
            this.input.reportValidity(); // triggers "invalid" event, which calls showErrors back
        } finally {
            this.#is_showErrors_event = false; // clear infinite recursion guard
        }
    }

    clearErrors() {
        // clear field errors
        this.error_list_element?.classList.remove("show-errors"); // hide error element
        this.input.classList.remove("show-errors");
        if (this.error_list_element) this.error_list_element.innerHTML = ""; // clear error list
    }

    addError(message) {
        // add a custom error to the field
        this.custom_errors.push(message);
        this.input.setCustomValidity(message); // make field considered invalid
    }

    validate() {
        this.custom_errors = []; // reset errors
        // do custom validation ...
        // on error call this.addError()
        // make field considered valid if no errors found
        if (!this.custom_errors.length) this.input.setCustomValidity("");
        return this.input.validity.valid; // return true if field is valid
    }

    disable() {
        // disable field
        this.input.disabled = true;
    }

    enable() {
        // enable field
        this.input.disabled = false;
    }

    onBeforeInput() {
        // filter out invalid input
    }

    onInput() {
        // run silent validation without displaying errors
        this.is_changed = true; // set is_changed
        if (this.validate()) this.clearErrors(); // clear errors if fixed
    }

    onChange() {
        // show validation result
        this.showErrors(true); // show errors (ignore missing required fields)
    }

    onInvalid(e) {
        // display errors
        if (this.error_list_element) {
            // there is a special element to display errors, built-in tooltip is not needed
            e.preventDefault(); // hide default tooltip
            this.showErrors(); // show errors
        }
    }
}

export class CheckboxField extends Field {
    // this.type === "checkbox"
    get value() {
        return this.input.checked;
    }

    set value(value) {
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        this.input.checked = value;
    }
}

export class MultiselectField extends Field {
    // this.type === "select-multiple"

    get value() {
        // get value of the multiselect field
        // return list of selected values, e.g. [0, 2, 3]
        let options = [];
        for (const option of this.input.options) {
            if (option.selected) options.push(option.value); // add option's value to the list if selected
        }
        // noinspection JSValidateTypes
        return options;
    }

    set value(value) {
        // set value of multiselect field
        // accepts list of selected options, where each option is
        // either a value of one of the allowed options (e.g. [0, 2, 3])
        // or an object with .id being a value (e.g. [{id: 0}, {id: 2}, {id: 3}])
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        let selected = value.map(option => option.id ?? option); // get list of selected values
        for (const option of this.input.options) {
            option.selected = selected.includes(parseInt(option.value)); // select specified options
        }
    }
}

export class MultiCheckboxField extends Field {
    // this.type === "checkbox"
    // multiselect field made of multiple <input type="checkbox">
    options; // stores all <input> fields

    constructor(...args) {
        super(...args);
        // select all other <input> options
        this.options = this.form.form.querySelectorAll(`input[type="checkbox"][name="${this.input.name}"]`);
        const params = {
            signal: this.controller.signal,
        };
        // attach event listeners to all <input> options
        for (const element of this.options) {
            if (element === this.input) continue; // already attached listeners in constructor, so skip
            this.addEventListeners(element, params);
        }
    }

    get value() {
        // get value of the multiselect field
        // return list of selected values, e.g. [0, 2, 3]
        let options = [];
        for (const option of this.options) {
            if (option.checked) options.push(option.value); // add option's value to the list if selected
        }
        // noinspection JSValidateTypes
        return options;
    }

    set value(value) {
        // set value of multiselect field
        // accepts list of selected options, where each option is
        // either a value of one of the allowed options (e.g. [0, 2, 3])
        // or an object with .id being a value (e.g. [{id: 0}, {id: 2}, {id: 3}])
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        if (value === null) { // unselect all options
            for (const option of this.options) option.checked = false;
            return;
        }
        let selected = value.map(option => option.id ?? option); // get list of selected values
        for (const option of this.options) {
            option.checked = selected.includes(parseInt(option.value)); // select specified options
        }
    }

    disable() {
        // disable all options
        for (const option of this.options) {
            option.disabled = true;
        }
    }

    enable() {
        // enable all options
        for (const option of this.options) {
            option.disabled = false;
        }
    }
}

export class SelectField extends Field {
    // this.type === "select-one"

    get value() {
        // get value of selected option
        for (const option of this.input.options) {
            if (option.selected) return option.value;
        }
        return null; // no option selected
    }

    set value(value) {
        // select option with specified value
        // can be passed either a value (e.g. 2) or object with id field (e.g. {id: 2})
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        if (value === null) { // unselect all options
            for (const option of this.input.options) option.selected = false;
            return;
        }
        for (const option of this.input.options) {
            if (parseInt(option.value) === (value.id ?? option)) {
                option.selected = true; // select specified option
                return;
            }
        }
    }
}

export class RadioField extends Field {
    // this.type === "radio"
    // select field made of multiple <input type="radio">
    options; // stores all <input> fields

    constructor(...args) {
        super(...args);
        // select all other <input> options
        this.options = this.form.form.querySelectorAll(`input[type="radio"][name="${this.input.name}"]`);
        const params = {
            signal: this.controller.signal,
        };
        // attach event listeners to all <input> options
        for (const element of this.options) {
            if (element === this.input) continue; // already attached event listeners in constructor, so skip
            this.addEventListeners(element, params);
        }
    }

    get value() {
        // get value of selected option
        for (const option of this.options) {
            if (option.checked) return option.value;
        }
        return null; // no option is selected
    }

    set value(value) {
        // select option with specified value
        // can be passed either a value (e.g. 2) or object with id field (e.g. {id: 2})
        this.is_changed = false; // reset is_changed
        this.clearErrors();
        if (value === null) { // reset all options
            for (const option of this.options) option.checked = false;
            return;
        }
        for (const option of this.options) {
            if (option.value === (value.id ?? option)) {
                option.checked = true; // select specified option
                return;
            }
        }
    }

    disable() {
        // disable all options
        for (const option of this.options) {
            option.disabled = true;
        }
    }

    enable() {
        // enable all options
        for (const option of this.options) {
            option.disabled = false;
        }
    }
}

class FormValidationField extends Field {
    // hidden field to attach errors for form-level validation

    constructor(form, signal = null) {
        // try to select a field if exists
        let input = form.form.querySelector(`input[type="hidden"][name="${form.form.id}_form_validation_field"]`);
        if (!input) {
            // create a new
            input = document.createElement("input");
            input.type = "hidden";
            input.name = `${form.form.id}_form_validation_field`;
            form.form.append(input);
        }
        super(input, form, signal);
        this.error_list_element = form.error_list_element; // use form's error container
    }

    showErrors(_exclude_required = false) {
        // show form-level validation errors
        this.clearErrors();
        if (this.input.validity.valid) return; // if valid, return
        for (const message of this.custom_errors) {
            if (!this.error_list_element) displayError(message); // no place to display errors, so use an info message
            else this.displayError(message); // display error
        }
        this.error_list_element?.classList.add("show-errors"); // display error container
    }

    onInvalid(e) {
        e.preventDefault(); // do not use default tooltip
    }
}

export class Form {
    // class to control, validate, and submit forms

    // define members
    form; // HTML <form> element
    submit_button = null; // <input type="submit"> HTML element
    reset_button = null; // <input type="reset"> HTML element
    success_message = "Success!"; // message to be displayed on successful submission
    action; // url of API endpoint to send form data to on submission
    disabled = false; // true when form is being loaded or submitted
    result = null; // server's response on form submission
    controller; // controller to remove all event listeners if necessary
    error_list_element; // HTML element to display form-level validation errors in
    form_validation_field; // hidden <input> to attach form-level validation errors to
    fields; // Field objects associated with this form

    constructor(id, signal = null) {
        // initialise form
        this.form = document.getElementById(id); // select <form> element
        if (!this.form) throw ReferenceError(`The form with id ${id} does not exist`);

        this.action = this.form.action; // extract action attribute

        this.controller = new AbortController();
        const params = {
            signal: this.controller.signal,
        };
        signal?.addEventListener("abort", () => this.abort(), params);

        this.error_list_element = this.form.querySelector(".errorlist.nonfield"); // select error list element
        this.form_validation_field = new FormValidationField(this, this.controller.signal); // add form validation field

        // associate input fields in the form
        this.fields = {};
        for (let input of this.form) {
            this.addField(input);
        }

        this.form.addEventListener("beforeinput", e => this.onBeforeInput(e), params); // before a field is edited
        this.form.addEventListener("input", e => this.onInput(e), params); // after a field is edited
        this.form.addEventListener("change", e => this.onChange(e), params); // after a field's edit is committed
        this.form.addEventListener("reset", e => this.onReset(e), params); // form is reset
        this.form.addEventListener("invalid", e => this.onInvalid(e), params); // form is submitted, but is invalid
        this.form.addEventListener("submit", e => this.onSubmit(e), params); // form is submitted
    }

    abort() {
        // remove all event listeners
        this.controller.abort();
    }

    removePrefix(name) {
        // remove form prefix from a field name
        return name.startsWith(`${this.form.id}-`) ? name.substring(this.form.id.length + 1) : name;
    }

    addField(input) {
        // associate input field with the form
        if (input === this.form_validation_field.input) return; // skip hidden form validation field
        if (input.type === "submit") {
            this.submit_button = input; // set submit button (keeps last if multiple)
            return;
        }
        if (input.type === "reset") {
            this.reset_button = input; // set reset button (keeps last if multiple)
            return;
        }
        const name = this.removePrefix(input.name); // remove form prefix from input name
        if (!name) return; // skip fields with empty names
        if (name in this.fields) return; // field already associated
        // instantiate the right Field class based on input type
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
        // iterate over form fields
        for (const name in this.fields) {
            yield this.fields[name];
        }
    }

    addError(message) {
        // add a form-level validation error
        this.form_validation_field.addError(message);
    }

    showErrorsForm() {
        // show form-level validation errors
        this.form_validation_field.showErrors();
    }

    showErrors(exclude_required = false) {
        // show both field- and form-level validation errors
        for (const field of this) {
            field.showErrors(exclude_required);
        }
        this.showErrorsForm();
    }

    validateForm() {
        // run form-level validation and return true if valid
        return this.form_validation_field.validate();
    }

    validate() {
        // run both field- and form-level validation, return true if valid
        let valid = true;
        for (const field of this) {
            valid &&= field.validate();
        }
        valid &&= this.validateForm();
        return valid;
    }

    clearErrorsForm() {
        // clear form-level validation errors
        this.form_validation_field.clearErrors();
    }

    clearErrors() {
        // clear both field- and form-level validation errors
        for (const field of this) field.clearErrors();
        this.form_validation_field.clearErrors();
    }

    get data() {
        // prepare submission data (payload for API request)
        let data = {};
        for (const field of this) {
            data[field.name] = field.value;
            field.is_changed = false; // reset is_changed
            if (this.disabled) field.is_submitting = true; // set is_submitting if used from .onSubmit()
        }
        return data;
    }

    clear() {
        // clear form
        this.form.reset();
        this.clearErrors();
    }

    disable(disable_fields = true) {
        // disable form during submission
        // unsuitable for regular disabling as is
        // code relies on .disabled meaning "is being submitted"
        this.disabled = true;
        if (this.submit_button) this.submit_button.disabled = true; // disable submit button
        if (disable_fields) {
            // disable all form fields
            for (const field of this) {
                field.disable();
            }
        }
    }

    enable() {
        // enable all form fields
        this.disabled = false;
        if (this.submit_button) this.submit_button.disabled = false; // enable submit button
        for (const field of this) {
            field.enable();
        }
    }

    onBeforeInput() {
        // before a field is edited
    }

    onInput() {
        // after a field is edited
        // run form-level validation
        this.validateForm();
    }

    onChange() {
        // after a field's edit is committed
        // show form-level validation errors
        this.showErrorsForm();
    }

    onReset() {
        // form is reset
    }

    onInvalid() {
        // form is submitted, but is invalid
    }

    async onSubmit(e) {
        // form is submitted
        e.preventDefault(); // prevent browser from handling form submission
        if (this.disabled) return false; // do not submit if already being submitted
        if (!this.validate()) return false; // do not submit invalid form
        try {
            this.disable(); // disable form (set concurrent submission guard)
            this.result = await api(this.action, this.data, {attempts: 5}); // submit data
            return this.onSuccess(); // call success callback
        } catch (err) {
            return this.onError(err); // process request errors
        } finally {
            this.enable(); // reset concurrent submission guard
        }
    }

    onSuccess(show_message = true, clear = true) {
        // successful submission callback handler
        for (const field of this) field.is_submitting = false; // reset all fields' is_submitting
        if (this.result.redirect) {
            location.href = this.result.redirect.location; // redirect to a new page if necessary
            return false;
        }
        // show success message if defined
        if (show_message && this.success_message) displaySuccess(this.success_message, 3000);
        if (clear) this.clear(); // clear the form if necessary
        return false;
    }

    onError(err) {
        // process a request error
        for (const field of this) {
            // rollback field's is_changed to true for submitted fields
            if (field.is_submitting) field.is_changed = true;
            field.is_submitting = false; // reset is_submitting
        }
        if (err instanceof APIError && err.code === 499) {
            // validation or user input error
            for (const [field, errors] of Object.entries(err.meta)) {
                for (const message of errors) {
                    // add error to form or field
                    if (field === "__all__" || !this.fields[field]) {
                        this.addError(message);
                        continue;
                    }
                    this.fields[field].addError(message);
                }
            }
            this.showErrors(); // show added errors
            return false;
        }
        processError(err); // if not validation error, display error in an info message
        return false;
    }

    submit() {
        // request form submission
        this.form.requestSubmit(this.submit_button);
    }
}

export class UpdateForm extends Form {
    // subclass of Form for update forms (used in settings forms)

    // define members
    #init_promise; // promise to initialise form
    #polling_interval_id;
    #is_syncing = false; // concurrent syncing guard
    #autosave_button; // hidden button used to distinguish autosave from manual submission
    #is_autosave = false; // flag is true when form is being autosaved
    success_message = "Data updated successfully";

    constructor(...args) {
        super(...args);
        this.disable(true); // disable form until initialisation
        // create autosave button
        this.#autosave_button = document.createElement("input");
        this.#autosave_button.type = "submit";
        this.#autosave_button.hidden = true;
        this.form.append(this.#autosave_button);
        // sync data to initialise form and then enable form and start polling
        this.#init_promise = this.sync(true).then(() => this.afterInit()); // promise to initialise form
    }

    async sync(ignore_disabled = false) {
        // synchronise form data
        if (this.#is_syncing || (this.disabled && !ignore_disabled)) return; // if already syncing or submitting, return
        try {
            this.#is_syncing = true; // set concurrent syncing guard
            this.result = await api(this.action, {}, {attempts: 5}); // load data
            this.updateFields(); // update fields with data
        } catch (err) {
            this.onError(err); // process response errors
            throw err;
        } finally {
            this.#is_syncing = false; // clear concurrent syncing guard
        }
    }

    disable(disable_fields = false) {
        // disable form (only submit button, do not disable fields by default)
        super.disable(disable_fields);
    }

    afterInit() {
        // complete initialisation
        this.enable();
        this.#polling_interval_id = setInterval(() => this.sync(), 10000); // start sync polling every 10 seconds
    }

    abort() {
        // remove all event listeners and stop sync polling
        super.abort();
        clearInterval(this.#polling_interval_id);
    }

    waitInit() {
        // wait asynchronously for initialisation
        return this.#init_promise;
    }

    get data() {
        // prepare data for submission (payload for API request)
        let data = {};
        for (const field of this) {
            // only include changed fields
            if (field.is_changed) {
                data[field.name] = field.value;
                field.is_changed = false; // reset is_changed
                if (this.disabled) field.is_submitting = true; // set is_submitting if called from within .onSubmit()
            }
        }
        return data;
    }

    updateFields() {
        // update fields' values after syncing or submission
        for (const [field, value] of Object.entries(this.result)) {
            if (field in this.fields && // field exists
                !this.fields[field].is_changed && ( // and isn't being edited
                    this.fields[field].input !== document.activeElement
                    || this.fields[field] instanceof SelectField
                    || this.fields[field] instanceof MultiselectField
                    || this.fields[field] instanceof CheckboxField
                    || this.fields[field] instanceof RadioField
                )) {
                this.fields[field].value = value; // update value
            }
        }
    }

    clear() {
        // hard sync form
        for (const field of this) field.is_changed = false;
        void this.sync();
        this.clearErrors();
    }

    onChange(e) {
        // a change is commited
        super.onChange(e);
        if (!e.isTrusted) return;
        this.form.requestSubmit(this.#autosave_button); // autosave
    }

    async onSubmit(e) {
        this.#is_autosave = e.submitter === this.#autosave_button; // determine if autosaving
        if (await super.onSubmit(e)) {
            this.form.requestSubmit(this.#autosave_button); // resubmit if changed while submitting
        }
        return false;
    }

    onSuccess(show_message = true, clear = false) {
        // update fields values on successful submission
        let changed = false;
        for (const field of this) {
            changed ||= field.is_changed;
            field.is_submitting = false; // reset is_submitting
        }
        super.onSuccess(show_message && !this.#is_autosave, clear);
        this.updateFields(); // update unchanged fields
        return changed; // resubmit if any field changed during submission
    }

    onError(err) {
        // process request error
        let changed = false;
        for (const field of this) {
            changed ||= field.is_changed;
            if (field.is_submitting) field.is_changed = true; // rollback is_changed for submitted fields
            field.is_submitting = false; // reset is_submitting
        }
        super.onError(err);
        return changed; // resubmit if any field changed during submission
    }
}
import {Form} from "../api/forms.js";

// define RegistrationForm class (extend form validation to enforce matching passwords)
class RegistrationForm extends Form {
    validateForm() {
        super.validateForm();
        const p1 = this.fields.password.value;
        // noinspection JSUnresolvedReference
        const p2 = this.fields.password_confirm.value;
        if (p1 && p2 && p1 !== p2) { // both passwords non-empty and do not match
            this.addError("Passwords don't match");
        }
        return this.form_validation_field.input.validity.valid;
    }
}

// initialise forms
new Form("login");
new RegistrationForm("registration");
import {Form} from '../api/forms.js';

class RegistrationForm extends Form {
    validateForm() {
        super.validateForm();
        const p1 = this.fields["registration-password"].getValue();
        const p2 = this.fields["registration-password_confirm"].getValue();
        if (p1 && p2 && p1 !== p2) {
            this.addError("Passwords don't match");
        }
        return this.form_validation_field.input.validity.valid;
    }
}

const login_form = new Form('login');
const registration_form = new RegistrationForm('registration');
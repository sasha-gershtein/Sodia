import {Form, UpdateForm} from '../api/forms.js';

class ChangePasswordForm extends Form {
    success_message = "Password changed successfully";

    validateForm() {
        super.validateForm();
        const p = this.fields["old_password"].value;
        const p1 = this.fields["new_password"].value;
        const p2 = this.fields["new_password_confirm"].value;
        if (p1 && p2 && p1 !== p2) {
            this.addError("New passwords don't match");
        }
        if (p && p1 && p === p1) {
            this.addError("New password must be different from the old password");
        }
        return this.form_validation_field.input.validity.valid;
    }
}

const change_password_form = new ChangePasswordForm("change-password");

class AccountForm extends UpdateForm {
    success_message = "Account settings are saved successfully";
}

const account_settings_form = new AccountForm("account");
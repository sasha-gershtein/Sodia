import {Form, UpdateForm} from "../api/forms.js";
import {loadMe} from "../users/auth_base.js";

// define ChangePasswordForm class (extend form validation to enforce matching passwords and new password difference)
class ChangePasswordForm extends Form {
    success_message = "Password changed successfully";

    validateForm() {
        super.validateForm();
        const p = this.fields.old_password.value;
        // noinspection JSUnresolvedReference
        const p1 = this.fields.new_password.value;
        // noinspection JSUnresolvedReference
        const p2 = this.fields.new_password_confirm.value;
        if (p1 && p2 && p1 !== p2) { // both passwords non-empty and do not match
            this.addError("New passwords don't match");
        }
        if (p1 && p === p1) { // new password non-empty and equal to old password
            this.addError("New password must be different from the old password");
        }
        return this.form_validation_field.input.validity.valid;
    }
}

new ChangePasswordForm("change-password"); // initialise password change form

class AccountForm extends UpdateForm {
    // override success message for account settings form
    success_message = "Account settings are saved successfully";

    constructor(...args) {
        super(...args);
        // override pattern mismatch error message for notifications settings form
        this.fields.username.ERROR_MESSAGES.patternMismatch =
            () => `${this.label} can only contain lowercase English letters, digits, periods, dashes and underscores`;
    }

    onSuccess(show_message = true, clear = false) {
        void loadMe();
        return super.onSuccess(show_message, clear);
    }
}

new AccountForm("account"); // initialise account settings form
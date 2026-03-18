import {UpdateForm} from "../api/forms.js";

class PrivacyForm extends UpdateForm {
    // override success message for privacy settings form
    success_message = "Privacy settings are saved successfully";
}

new PrivacyForm("privacy"); // initialise privacy settings form
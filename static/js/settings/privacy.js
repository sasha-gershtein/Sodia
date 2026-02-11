import {UpdateForm} from '../api/forms.js';

class PrivacyForm extends UpdateForm {
    success_message = "Privacy settings are saved successfully";
}

const privacy_settings_form = new PrivacyForm("privacy");
import {UpdateForm} from '../api/forms.js';

class NotificationsForm extends UpdateForm {
    success_message = "Notifications settings are saved successfully";
}

const notifications_settings_form = new NotificationsForm("notifications");
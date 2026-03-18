import {UpdateForm} from "../api/forms.js";

class NotificationsForm extends UpdateForm {
    // override success message for notifications settings form
    success_message = "Notifications settings are saved successfully";
}

new NotificationsForm("notifications"); // initialise notifications settings form
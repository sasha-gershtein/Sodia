import {UpdateForm} from "../api/forms.js";

class ChallengesForm extends UpdateForm {
    // override success message for notifications settings form
    success_message = "Challenges settings are saved successfully";
}

new ChallengesForm("challenges"); // initialise challenges settings form
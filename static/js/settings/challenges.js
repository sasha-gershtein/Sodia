import {UpdateForm} from '../api/forms.js';

class ChallengesForm extends UpdateForm {
    success_message = "Challenges settings are saved successfully";
}

const challenges_settings_form = new ChallengesForm("challenges");
import {Form} from "../api/forms.js";
import {loadTemplate} from "../api/api.js";

const logout_form = new Form("logout");

loadTemplate(
    "/api/users/me/",
    {},
    {
        prefix: "navigation"
    }
).then(response => {
    document.querySelector("#profile-link").href = `/profile/${response.username}`
})

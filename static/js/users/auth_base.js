import {Form} from "../api/forms.js";
import {loadTemplate} from "../api/api.js";

new Form("logout"); // initialise logout form

// load own profile info to display in navigation bar
export async function loadMe(show_loading = false) {
    const response = await loadTemplate( // load navigation bar template
        "/api/users/me/",
        {},
        {
            prefix: "navigation",
            show_loading,
            translators: {
                unread_messages_count: count => count || "",  // hide if 0
            },
        }
    );
    document.querySelector("#profile-link").href = `/profile/${response.username}/`; // add link to own profile
}

void loadMe(true);
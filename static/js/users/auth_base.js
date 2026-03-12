import {Form} from "../api/forms.js";
import {loadTemplate} from "../api/api.js";

const logout_form = new Form("logout");

export async function loadMe(show_loading = false) {
    const response = await loadTemplate(
        "/api/users/me/",
        {},
        {
            prefix: "navigation",
            show_loading,
            translators: {
                unread_messages_count: count => count || "",
            }
        }
    );
    document.querySelector("#profile-link").href = `/profile/${response.username}/`;
}

void loadMe(true);
import {Form} from "../api/forms.js";
import {loadTemplate} from "../api/api.js";
import {ContextMenuButton} from "../api/ui.js";

new Form("logout"); // initialise logout form

new ContextMenuButton({
    id: "nav-menu-button",
    create: false,
    menu: document.getElementById("nav-panel"),
    hide_on_buttons: false,
});

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
    document.getElementById("navigation-notifications-count").innerText = response.unread_messages_count || "";
    document.getElementById("profile-link").href = `/profile/${response.username}/`; // add link to own profile
}

void loadMe(true);
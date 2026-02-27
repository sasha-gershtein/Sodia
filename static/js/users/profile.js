import {loadTemplate} from "../api/api.js";
import {insertInteractionButtons} from "../interactions/interactions.js";

const list = window.location.pathname.split("/");
const username = list[list.findIndex(e => e === "profile") + 1];
loadTemplate(
    "/api/users/full-info/",
    {
        username: username
    },
    {
        prefix: "profile",
        title: _ => `${username} — Sodia`,
        translators: {
            house: house => house?.name,
        }
    }
).then(user_info => {
    insertInteractionButtons(user_info, document.querySelector("#profile-buttons"));
});

import {api, loadTemplate} from "../api/api.js";
import {insertInteractionButtons, insertUser} from "../interactions/interactions.js";
import {ContextMenuButton} from "../api/ui.js";

let friends_list = document.getElementById("friends-list");
let friends_loaded = false;
let user_id = null;

async function show_friends() {
    if (friends_loaded) return;
    let friends = await api("/api/interactions/get-friends/", {id: user_id}, {attempts: 5});
    if (!friends.length) {
        friends_list.innerHTML = "Friends will be displayed here...";
    }
    friends_list.innerHTML = "";
    friends.forEach(friend_info => insertUser(friend_info, friends_list));
    friends_loaded = true;
}

function load(user_info) {
    user_id = user_info.id;
    insertInteractionButtons(user_info, document.querySelector("#profile-buttons"));
    // noinspection JSUnresolvedReference
    if (user_info.friends_visible) {
        let friends_button = new ContextMenuButton({
            menu: friends_list,
            hide_on_buttons: false,
            id: "profile-friends-count",
            create: false,
            callback: show_friends,
        });
        friends_button.disabled = false;
    }
}

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
            friends_count: friends_count => `${friends_count} friend${friends_count === 1 ? "" : "s"}`,
        }
    }
).then(load);

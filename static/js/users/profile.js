import {api, loadTemplate, processError} from "../api/api.js";
import {insertInteractionButtons, insertUser} from "../interactions/interactions.js";
import {ContextMenuButton} from "../api/ui.js";

const friends_list = document.getElementById("friends-list")

async function show_friends() {
    show_friends.friends_loaded ??= false;
    if (show_friends.friends_loaded) return;
    show_friends.friends_loaded = true;
    let friends;
    try {
        friends = await api("/api/interactions/get-friends/", {id: show_friends.user_id}, {attempts: 5});
    } catch (err) {
        return processError(err);
    }
    if (!friends.length) {
        friends_list.innerHTML = "Friends will be displayed here...";
    }
    friends_list.innerHTML = "";
    friends.forEach(friend_info => insertUser(friend_info, friends_list));
}

function load(user_info) {
    load.friends_button ??= null;
    show_friends.user_id = user_info.id;
    insertInteractionButtons(user_info, {
        container: document.querySelector("#profile-buttons"),
        rebuild: load,
    });
    if (load.friends_button === null) {
        load.friends_button = new ContextMenuButton({
            menu: friends_list,
            hide_on_buttons: false,
            id: "profile-friends-count",
            create: false,
            callback: show_friends,
        });
    }
    // noinspection JSUnresolvedReference
    load.friends_button.disabled = !user_info.friends_visible;
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

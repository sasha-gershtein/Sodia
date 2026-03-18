import {api, loadTemplate, processError} from "../api/api.js";
import {insertInteractionButtons, insertUser} from "../interactions/interactions.js";
import {ContextMenuButton} from "../api/ui.js";

// select HTML elements
const friends_list = document.getElementById("friends-list");
const full_name_container = document.getElementById("profile-full-name");
const profile_buttons_container = document.getElementById("profile-buttons");

// load and show list of user's friends
async function show_friends() {
    show_friends.friends_loaded ??= false; // if friends_loaded is not defined, set as false
    if (show_friends.friends_loaded) return; // if friends already loaded, don't load again
    show_friends.friends_loaded = true; // set true to prevent multiple concurrent loading (reset on error)
    let friends;
    try {
        // load friends of user with id = show_friends.user_id (defined by load())
        friends = await api("/api/interactions/get-friends/", {id: show_friends.user_id}, {attempts: 5});
    } catch (err) {
        show_friends.friends_loaded = false; // failed => reset flag
        processError(err); // display request errors
        return;
    }
    if (!friends.length) {  // user has no friend
        friends_list.innerHTML = "Friends will be displayed here...";
    }
    friends_list.innerHTML = ""; // clear the container
    friends.forEach(friend_info => insertUser(friend_info, friends_list)); // insert all users into the container
}

// additional tasks to load the page (called at loading and on relation status change)
function load(user_info) {
    // noinspection JSUnresolvedReference
    if (user_info.first_name && user_info.last_name) {
        // full name is visible
        const full_name = user_info.first_name + " " + user_info.last_name;
        // if full name is different from display name, display on the page
        // noinspection JSUnresolvedReference
        if (full_name !== user_info.display_name) full_name_container.innerText = full_name;
    }
    show_friends.user_id = user_info.id; // set user_id to be used to show friends list
    insertInteractionButtons(user_info, { // build and render buttons for user interaction
        container: profile_buttons_container,
        rebuild: load, // on button presses call load() again
        set_ids: true,  // buttons only displayed on the page once, so add id fields to buttons
    });
    load.friends_button ??= null; // if friends_button is not defined, set as null
    if (load.friends_button === null) {
        // create button (only do once on the first load)
        load.friends_button = new ContextMenuButton({
            menu: friends_list,
            hide_on_buttons: false,
            id: "profile-friends-count",
            create: false,
            callback: show_friends,
        });
    }
    // noinspection JSUnresolvedReference
    load.friends_button.disabled = !user_info.friends_visible; // disable if friends list is not visible
}

// extract username from url
const list = location.pathname.split("/");
const username = list[list.findIndex(e => e === "profile") + 1];

// load the page
// noinspection JSUnusedGlobalSymbols
loadTemplate(
    "/api/users/full-info/",
    {
        username: username,
    },
    {
        prefix: "profile",
        title: () => `${username} — Sodia`,
        translators: {
            house: house => house?.name, // show house name if defined, hide otherwise
            // show "1 friend" or "n friends" if n != 1
            friends_count: friends_count => `${friends_count} friend${friends_count === 1 ? "" : "s"}`,
            country: country => country?.name, // show country name if defined, hide otherwise
        }
    }
).then(load); // then call load()
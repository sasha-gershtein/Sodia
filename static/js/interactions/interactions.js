import {APIButton, ContextMenuButton, displayError, LinkButton, makeContextMenu} from "../api/ui.js";

export class Relation {
    // Users relation enum class (values are not arbitrary, has to match Python's interactions.models.Relation!)
    static SAME_USER = "SAME_USER";
    static FRIENDS = "FRIENDS";
    static PENDING_SENT = "PENDING_SENT";
    static PENDING_RECEIVED = "PENDING_RECEIVED";
    static NONE = "NONE";
    static FRIEND_REQUEST_FORBIDDEN = "FRIEND_REQUEST_FORBIDDEN";
    static BLOCKED = "BLOCKED";
}

export function makeInteractionButtons(user_info, rebuild, set_ids = false) {
    // create buttons for all available profile actions, and assemble main button and hidden actions menu
    // add id to buttons if set_ids is true

    // available actions  | condition
    // Edit profile         relation == SAME_USER
    // Add friend           relation == NONE
    // Respond to request   relation == PENDING_RECEIVED
    //   * accept
    //   * deny
    // Withdraw request     relation == PENDING_SENT
    // Message              can_message == true
    // - always hidden:
    // Remove friend        relation == FRIENDS
    // Block                relation != SAME_USER, BLOCKED
    // Unblock              relation == BLOCKED

    // values to determine:
    let main_btn = null;
    let main_menu = null;
    let menu_btn = null;
    let menu_buttons = [];
    let menu = null;

    // noinspection JSUnresolvedReference
    const relation = user_info.relation;
    // noinspection JSUnresolvedReference
    const can_message = user_info.can_message;
    const username = user_info.username;
    const user_id = user_info.id;
    const main_id = set_ids ? "main-action-btn" : null; // if set_ids = false, main_id = null

    switch (relation) {
        case Relation.SAME_USER:
            main_btn = new LinkButton({ // edit own profile
                url: "/settings/account/",
                id: main_id,
                classes: ["edit-btn"],
                label: "Edit profile",
            });
            break;
        case Relation.NONE:
            main_btn = new APIButton({ // send a friend request
                url: "/api/interactions/friend/send/",
                payload: {
                    id: user_id,
                },
                id: main_id,
                classes: ["add-friend-btn"],
                label: "Add friend",
                callback: rebuild,
                success_message: "Friend request sent",
            });
            break;
        case Relation.PENDING_RECEIVED:
            let accept = new APIButton({ // accept friend request
                url: "/api/interactions/friend/respond/",
                payload: {
                    id: user_id,
                    accept: true,
                },
                id: set_ids ? "accept-friend-btn" : null, // do not set ids if set_ids is false
                classes: ["accept-friend-btn"],
                label: "Accept",
                callback: rebuild,
                success_message: "Friend request accepted",
            });
            let deny = new APIButton({ // deny friend request
                url: "/api/interactions/friend/respond/",
                payload: {
                    id: user_id,
                    accept: false,
                },
                id: set_ids ? "deny-friend-btn" : null, // do not set ids if set_ids is false
                classes: ["deny-friend-btn"],
                label: "Ignore",
                callback: rebuild,
                success_message: "Friend request ignored",
            });
            main_menu = makeContextMenu([accept, deny], "respond-friend-menu");
            main_btn = new ContextMenuButton({ // button to see response options
                menu: main_menu.menu,
                id: main_id,
                label: "Respond to request...",
            });
            break;
        case Relation.PENDING_SENT:
            main_btn = new APIButton({ // withdraw friend request
                url: "/api/interactions/friend/withdraw/",
                payload: {
                    id: user_id,
                },
                id: main_id,
                classes: ["withdraw-friend-btn"],
                label: "Withdraw friend request",
                callback: rebuild,
                success_message: "Friend request withdrawn",
            });
            break;
        case Relation.FRIENDS:
            break;
        case Relation.FRIEND_REQUEST_FORBIDDEN:
            break;
        case Relation.BLOCKED:
            break;
        default:
            // unknown value, shouldn't happen
            displayError("An error occurred. Try refreshing the page");
            throw Error(`Unknown relation status: ${relation}`);
    }
    if (can_message) {
        const count = user_info.unread_messages_count;
        const message_button = new LinkButton({ // message
            url: `/message/${username}/`,
            id: set_ids ? (main_btn === null ? main_id : "message-btn") : null,
            classes: ["message-btn"],
            label: "Message" + (count ? ` (${count})` : ""), // if there are unread messages, add " (n)"
        });
        // promote message button to main if no other main button action is available
        if (main_btn === null) main_btn = message_button;
        else menu_buttons.push(message_button); // otherwise, add to hidden actions
    }

    if (relation === Relation.FRIENDS) {
        menu_buttons.push(new APIButton({ // remove friend
            url: "/api/interactions/friend/remove/",
            payload: {
                id: user_id,
            },
            id: set_ids ? "remove-friend-btn" : null, // do not set ids if set_ids is false
            classes: ["remove-friend-btn"],
            label: "Remove friend",
            callback: rebuild,
            success_message: "Friend removed",
        }));
    }
    if (relation !== Relation.SAME_USER) {
        if (relation === Relation.BLOCKED) {
            menu_buttons.push(new APIButton({ // unblock user
                url: "/api/interactions/unblock/",
                payload: {
                    id: user_id,
                },
                id: set_ids ? "unblock-btn" : null, // do not set ids if set_ids is false
                classes: ["unblock-btn"],
                label: "Unblock",
                callback: rebuild,
                success_message: "User unblocked",
            }));
        } else {
            menu_buttons.push(new APIButton({ // block user
                url: "/api/interactions/block/",
                payload: {
                    id: user_id,
                },
                id: set_ids ? "block-btn" : null, // do not set ids if set_ids is false
                classes: ["block-btn"],
                label: "Block",
                callback: rebuild,
                success_message: "User blocked",
            }));
        }
    }

    if (menu_buttons.length) {
        // make hidden actions menu
        menu = makeContextMenu(menu_buttons, "hidden-actions-menu");
        menu_btn = new ContextMenuButton({
            menu: menu.menu,
            id: set_ids ? "hidden-actions-btn" : null, // do not set ids if set_ids is false
            classes: ["hidden-actions-btn"],
            label: "...",
        })
    }

    return {main_btn, main_menu, menu_btn, menu}
}

export function insertInteractionButtons(user_info, options) {
    // insert interactions button into a container based on user's info
    // and attach rebuild to all buttons' callbacks, which will recreate buttons based on the new relation
    let { // unpack parameters
        container, // container to insert buttons to
        add_menu = true, // only main action button is displayed if false
        set_ids = false, // add id to buttons if true
        // default rebuild callback is to just call this function again to recreate buttons
        rebuild = user_info => insertInteractionButtons(user_info, {container, add_menu, set_ids}),
    } = options;
    // noinspection JSUnresolvedReference
    let buttons = makeInteractionButtons(user_info, rebuild, set_ids); // determine and assemble profile buttons
    container.innerHTML = ""; // clear container
    // insert buttons to container
    if (buttons.main_btn) buttons.main_btn.appendTo(container);
    if (buttons.main_menu) container.append(buttons.main_menu.wrapper);
    if (!add_menu) return; // do not add hidden actions menu
    if (buttons.menu_btn) {
        buttons.menu_btn.appendTo(container);
        container.append(buttons.menu.wrapper);
    }
}

export function insertUser(user_info, container, only_message = false) {
    // insert a user to a list of users with interaction buttons
    let user = document.createElement("div");
    user.classList.add("user");
    let name = document.createElement("a");
    name.href = `/profile/${user_info.username}/`; // click on name takes to user profile
    // noinspection JSUnresolvedReference
    name.innerText = user_info.display_name;
    let button_container = document.createElement("div");
    if (only_message) {
        // only insert button to message when available
        // noinspection JSUnresolvedReference
        if (user_info.can_message) {
            // create button to message
            const count = user_info.unread_messages_count;
            new LinkButton({ // message
                url: `/message/${user_info.username}/`,
                label: "Message" + (count ? ` (${count})` : ""),
                classes: ["message-btn"],
            }).appendTo(button_container);
        }
    } else insertInteractionButtons(user_info, {
        container: button_container,
        add_menu: false, // insert main button only
    });
    user.append(name, button_container);
    container.append(user);
}
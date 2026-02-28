import {APIButton, ContextMenuButton, displayError, LinkButton, makeContextMenu} from "../api/ui.js";

export class Relation {
    static SAME_USER = "SAME_USER";
    static FRIENDS = "FRIENDS";
    static PENDING_SENT = "PENDING_SENT";
    static PENDING_RECEIVED = "PENDING_RECEIVED";
    static NONE = "NONE";
    static FAILED_REQUEST = "FAILED_REQUEST";
    static BLOCKED = "BLOCKED";
}

export function makeInteractionButtons(user_info, rebuild) {
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
    const main_id = "main-action-btn";

    switch (relation) {
        case Relation.SAME_USER:
            main_btn = new LinkButton({
                url: "/settings/account/",
                id: main_id,
                label: "Edit profile",
            });
            break;
        case Relation.NONE:
            main_btn = new APIButton({
                url: "/api/interactions/friend/send/",
                payload: {
                    id: user_id,
                },
                id: main_id,
                label: "Add friend",
                callback: rebuild,
                success_message: "Friend request sent",
            });
            break;
        case Relation.PENDING_RECEIVED:
            let accept = new APIButton({
                url: "/api/interactions/friend/respond/",
                payload: {
                    id: user_id,
                    accept: true,
                },
                id: "accept-friend-btn",
                label: "Accept",
                callback: rebuild,
                success_message: "Friend request accepted",
            });
            let deny = new APIButton({
                url: "/api/interactions/friend/respond/",
                payload: {
                    id: user_id,
                    accept: false,
                },
                id: "deny-friend-btn",
                label: "Ignore",
                callback: rebuild,
                success_message: "Friend request ignored",
            });
            main_menu = makeContextMenu([accept, deny], "respond-friend-menu");
            main_btn = new ContextMenuButton({
                menu: main_menu.menu,
                id: main_id,
                label: "Respond to request...",
            });
            break;
        case Relation.PENDING_SENT:
            main_btn = new APIButton({
                url: "/api/interactions/friend/withdraw/",
                payload: {
                    id: user_id,
                },
                id: main_id,
                label: "Withdraw friend request",
                callback: rebuild,
                success_message: "Friend request withdrawn",
            });
            break;
        case Relation.FRIENDS:
            break;
        case Relation.FAILED_REQUEST:
            break;
        case Relation.BLOCKED:
            break;
        default:
            displayError("An error occurred. Try refreshing the page");
            throw Error(`Unknown relation status: ${relation}`);
    }
    let message_button = null;
    if (can_message) {
        message_button = new LinkButton({
            url: `/message/${username}/`,
            id: main_btn === null ? main_id : "message-btn",
            label: "Message",
        })
    }
    if (main_btn === null) main_btn = message_button;
    else if (message_button !== null) menu_buttons.push(message_button);

    if (relation === Relation.FRIENDS) {
        menu_buttons.push(new APIButton({
            url: "/api/interactions/friend/remove/",
            payload: {
                id: user_id,
            },
            id: "remove-friend-btn",
            label: "Remove friend",
            callback: rebuild,
            success_message: "Friend removed",
        }));
    }
    if (relation !== Relation.SAME_USER) {
        if (relation === Relation.BLOCKED) {
            menu_buttons.push(new APIButton({
                url: "/api/interactions/unblock/",
                payload: {
                    id: user_id,
                },
                id: "unblock-btn",
                label: "Unblock",
                callback: rebuild,
                success_message: "User unblocked",
            }));
        } else {
            menu_buttons.push(new APIButton({
                url: "/api/interactions/block/",
                payload: {
                    id: user_id,
                },
                id: "block-btn",
                label: "Block",
                callback: rebuild,
                success_message: "User blocked",
            }));
        }
    }

    if (menu_buttons.length) {
        menu = makeContextMenu(menu_buttons, "hidden-actions-menu");
        menu_btn = new ContextMenuButton({
            menu: menu.menu,
            id: "hidden-actions-btn",
            label: "...",
        })
    }

    return {main_btn, main_menu, menu_btn, menu}
}

export function insertInteractionButtons(user_info, container, add_menu = true) {
    // noinspection JSUnresolvedReference
    let buttons = makeInteractionButtons(user_info,
        (user_info) => insertInteractionButtons(user_info, container, add_menu)
    );
    container.innerHTML = "";
    if (buttons.main_btn) buttons.main_btn.appendTo(container);
    if (buttons.main_menu) container.appendChild(buttons.main_menu.wrapper);
    if (!add_menu) return;
    if (buttons.menu_btn) {
        buttons.menu_btn.appendTo(container);
        container.appendChild(buttons.menu.wrapper);
    }
}

export function insertUser(user_info, container) {
    let box = document.createElement("div");
    box.classList.add("user");
    let name = document.createElement("span");
    // noinspection JSUnresolvedReference
    name.innerText = user_info.display_name;
    box.appendChild(name);
    let button_container = document.createElement("div");
    insertInteractionButtons(user_info, button_container, false);
    box.appendChild(button_container);
    container.appendChild(box);
}
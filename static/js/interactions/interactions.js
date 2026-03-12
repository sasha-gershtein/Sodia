import {APIButton, ContextMenuButton, displayError, LinkButton, makeContextMenu} from "../api/ui.js";

export class Relation {
    static SAME_USER = "SAME_USER";
    static FRIENDS = "FRIENDS";
    static PENDING_SENT = "PENDING_SENT";
    static PENDING_RECEIVED = "PENDING_RECEIVED";
    static NONE = "NONE";
    static FRIEND_REQUEST_FORBIDDEN = "FRIEND_REQUEST_FORBIDDEN";
    static BLOCKED = "BLOCKED";
}

export function makeInteractionButtons(user_info, rebuild, set_ids = false) {
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
    const main_id = set_ids ? "main-action-btn" : null;

    switch (relation) {
        case Relation.SAME_USER:
            main_btn = new LinkButton({
                url: "/settings/account/",
                id: main_id,
                classes: ["edit-btn"],
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
                classes: ["add-friend-btn"],
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
                id: set_ids ? "accept-friend-btn" : null,
                classes: ["accept-friend-btn"],
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
                id: set_ids ? "deny-friend-btn" : null,
                classes: ["deny-friend-btn"],
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
            displayError("An error occurred. Try refreshing the page");
            throw Error(`Unknown relation status: ${relation}`);
    }
    let message_button = null;
    if (can_message) {
        const count = user_info.unread_messages_count;
        message_button = new LinkButton({
            url: `/message/${username}/`,
            id: set_ids ? (main_btn === null ? main_id : "message-btn") : null,
            classes: ["message-btn"],
            label: "Message" + (count ? ` (${count})` : ""),
        });
    }
    if (main_btn === null) main_btn = message_button;
    else if (message_button !== null) menu_buttons.push(message_button);

    if (relation === Relation.FRIENDS) {
        menu_buttons.push(new APIButton({
            url: "/api/interactions/friend/remove/",
            payload: {
                id: user_id,
            },
            id: set_ids ? "remove-friend-btn" : null,
            classes: ["remove-friend-btn"],
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
                id: set_ids ? "unblock-btn" : null,
                classes: ["unblock-btn"],
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
                id: set_ids ? "block-btn" : null,
                classes: ["block-btn"],
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
            id: set_ids ? "hidden-actions-btn" : null,
            classes: ["hidden-actions-btn"],
            label: "...",
        })
    }

    return {main_btn, main_menu, menu_btn, menu}
}

export function insertInteractionButtons(user_info, options) {
    let {
        container,
        add_menu = true,
        rebuild = (user_info) => insertInteractionButtons(user_info, {container, add_menu}),
        set_ids = false,
    } = options;
    // noinspection JSUnresolvedReference
    let buttons = makeInteractionButtons(user_info, rebuild, set_ids);
    container.innerHTML = "";
    if (buttons.main_btn) buttons.main_btn.appendTo(container);
    if (buttons.main_menu) container.append(buttons.main_menu.wrapper);
    if (!add_menu) return;
    if (buttons.menu_btn) {
        buttons.menu_btn.appendTo(container);
        container.append(buttons.menu.wrapper);
    }
}

export function insertUser(user_info, container, only_message = false) {
    let box = document.createElement("div");
    box.classList.add("user");
    let name = document.createElement("a");
    name.href = `/profile/${user_info.username}/`;
    // noinspection JSUnresolvedReference
    name.innerText = user_info.display_name;
    let button_container = document.createElement("div");
    if (only_message) {
        // noinspection JSUnresolvedReference
        if (user_info.can_message) {
            const count = user_info.unread_messages_count;
            new LinkButton({
                url: `/message/${user_info.username}/`,
                label: "Message" + (count ? ` (${count})` : ""),
                classes: ["message-btn"],
            }).appendTo(button_container);
        }
    } else insertInteractionButtons(user_info, {
        container: button_container,
        add_menu: false,
    });
    box.append(name, button_container);
    container.append(box);
}
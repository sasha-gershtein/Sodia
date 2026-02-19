import {loadTemplate} from "../api/api.js";
import {loading} from "../api/ui.js";

const list = window.location.pathname.split("/");
const username = list[list.findIndex(e => e === "profile") + 1];
loadTemplate(
    "/api/users/full-info/",
    {
        username: username
    },
    {
        title: _ => `${username} — Sodia`,
        translators: {
            house: house => house?.name,
        }
    }
).catch(err => {
    if (err.code === 404 && err.reason === "USER_NOT_FOUND") {
        loading.querySelector("div").innerText = "404 Error\nThis user does not exist";
    }
    throw err;
});

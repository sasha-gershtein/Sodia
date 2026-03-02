import {displayError, hidePageLoading, showPageLoading} from "../api/ui.js";
import {api} from "../api/api.js";
import {insertUser} from "../interactions/interactions.js";

showPageLoading();

const query = new URLSearchParams(location.search).get("q");

const input = document.querySelector("#search-query");
input.value = query;

const search_results = document.querySelector("#search-results");

api(
    "/api/users/search/",
    {query}
).catch(
    err => displayError(err)
).then(users => {
    // noinspection JSUnresolvedReference
    if (!users.length) return;
    search_results.innerHTML = "";
    users.forEach(user_info => {
        insertUser(user_info, search_results);
    })
});

hidePageLoading();
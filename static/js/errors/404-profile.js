// this file is used both for profile and dialogue 404 errors

// extract username from url
const list = location.pathname.split("/");
const username = list[list.findIndex(e => ["profile", "message"].includes(e)) + 1];

const username_box = document.getElementById("404-username"); // exists on profile 404 page
if (username_box) username_box.innerText = username;

// initialise link to search for user
const url = new URL("/search/", location.href);
url.searchParams.set("q", username);
document.getElementById("search-link").href = url;
document.getElementById("404-username-search").innerText = username;
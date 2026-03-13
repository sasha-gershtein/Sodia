const list = location.pathname.split("/");
const username = list[list.findIndex(e => ["profile", "message"].includes(e)) + 1];

const username_box = document.getElementById("404-username");
if (username_box) username_box.innerText = username;
const url = new URL("/search/", location.href);
url.searchParams.set("q", username);
document.getElementById("search-link").href = url;
document.getElementById("404-username-search").innerText = username;
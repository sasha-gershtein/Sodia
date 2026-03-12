import {api, processError} from "../api/api.js";
import {insertUser} from "../interactions/interactions.js";
import {page_loading} from "../api/ui.js";

const sodia_btn = document.getElementById("sodia-btn");
const pressing_button_list = document.getElementById("pressing-button-list");
const sodia_btn_presses_count = document.getElementById("sodia-btn-presses-count");

function populate_list(list) {
    list.innerHTML = "";
    list.forEach((user_info) => {
        insertUser(user_info, pressing_button_list, true);
    });
}

function display_state(response) {
    const {
        is_pressing_sodia_button,
        sodia_button_info
    } = response;
    pressing_button_list.innerHTML = "";
    if (is_pressing_sodia_button) {
        sodia_btn.classList.add("pressed");
        sodia_button_info.forEach((user_info) => {
            insertUser(user_info, pressing_button_list, true);
        });
    } else {
        sodia_btn.classList.remove("pressed");
        sodia_btn_presses_count.innerText = !sodia_button_info ? "" :
            (sodia_button_info === 1 ? "One person is" : `${sodia_button_info} people are`);
    }
}

async function load() {
    try {
        display_state(await api("/api/users/load-home/", {}, {attempts: 100}));
    } catch (err) {
        processError(err);
    }
}

async function onPress() {
    sodia_btn.classList.toggle("pressed");
    sodia_btn.disabled = true;
    try {
        const url = "/api/users/sodia-btn/" + (sodia_btn.classList.contains("pressed") ? "press/" : "unpress/");
        display_state(await api(url, {}, {attempts: 5}));
    } catch (err) {
        processError(err);
        sodia_btn.classList.toggle("pressed");
    } finally {
        sodia_btn.disabled = false;
        sodia_btn.focus();
    }
}

sodia_btn.addEventListener("click", onPress);

page_loading.show()
load().then(() => page_loading.hide());
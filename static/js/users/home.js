import {api, processError} from "../api/api.js";
import {insertUser} from "../interactions/interactions.js";
import {page_loading} from "../api/ui.js";

// select HTML elements
const sodia_btn = document.getElementById("sodia-btn");
const pressing_button_list = document.getElementById("pressing-button-list");
const sodia_btn_presses_count = document.getElementById("sodia-btn-presses-count");

// display Sodia Button state (at loading or updates)
function display_state(response) {
    const {
        is_pressing_sodia_button,
        sodia_button_info,
    } = response;
    pressing_button_list.innerHTML = ""; // clear list of users pressing the button
    if (is_pressing_sodia_button) {
        sodia_btn.classList.add("pressed"); // show button being pressed if not already
        sodia_button_info.forEach(user_info => { // insert users pressing the button in the list below
            insertUser(user_info, pressing_button_list, true);
        });
    } else {
        // not pressing the Sodia Button
        sodia_btn.classList.remove("pressed"); // show button not being pressed if not already
        // update count of people pressing the button
        // hide if 0, put "One person is" if 1, and "n people are" otherwise
        sodia_btn_presses_count.innerText = !sodia_button_info ? "" :
            (sodia_button_info === 1 ? "One person is" : `${sodia_button_info} people are`);
    }
}

// load Sodia Button state
async function load() {
    try {
        // request doesn't affect server state and page is unusable without loading, so do many attempts
        display_state(await api("/api/users/load-home/", {}, {attempts: 100}));
    } catch (err) {
        processError(err); // display request errors
    }
}

// press or unpress Sodia Button
async function onPress() {
    sodia_btn.classList.toggle("pressed");
    sodia_btn.disabled = true; // disable subsequent pressing while loading
    try {
        // "/api/users/sodia-btn/" + "press/" or "unpress/"
        const url = "/api/users/sodia-btn/" + (sodia_btn.classList.contains("pressed") ? "press/" : "unpress/");
        display_state(await api(url, {}, {attempts: 5}));
    } catch (err) {
        sodia_btn.classList.toggle("pressed"); // change visual state back
        processError(err); // display request errors
    } finally {
        sodia_btn.disabled = false; // enable button
        sodia_btn.focus(); // return focus on the button (removed on disabling)
    }
}

// start listening to Sodia Button presses
sodia_btn.addEventListener("click", onPress);

// load the page
page_loading.show() // show "loading..." message
load().then(() => page_loading.hide()); // load and then hide message
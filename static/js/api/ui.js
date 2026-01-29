const error_box = document.getElementById("error-box");
let hide_error_box = 0;

export function displayError(message) {
    if (!error_box) {
        alert(`error: ${message}`);
        return;
    }
    error_box.innerText = message;
    error_box.classList.remove("hidden");
    hide_error_box = new Date().getTime() + 4900;
    setTimeout(function () {
        if (hide_error_box < new Date().getTime()) error_box.classList.add("hidden");
    }, 5000)
}
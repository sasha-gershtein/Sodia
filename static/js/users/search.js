import {HideableElement} from "../api/ui.js";
import {insertUser} from "../interactions/interactions.js";
import {Form} from "../api/forms.js";

// extract search query from url
function get_url_query() {
    // get parameter q from url (i.e. /?q=...) and cut if too long
    return new URLSearchParams(location.search).get("q").substring(0, search_form.fields.query.input.maxLength);
}

// create interactive HTML elements
const loading = new HideableElement("loading-search-results"); // "loading..." message
const no_results = new HideableElement("no-results"); // "no results found" message

const search_results = document.getElementById("search-results"); // search results container

// define SearchForm class
class SearchFrom extends Form {
    success_message = null; // do not show success message on submit

    constructor(id) {
        super(id);
        this.fields.query.ERROR_MESSAGES.valueMissing = () => "please enter a search query";
        // hidden button for form submission on back and front browser history navigation
        this.popstate_button = document.createElement("input");
        this.popstate_button.type = "submit";
        this.popstate_button.hidden = true;
        this.form.append(this.popstate_button);
    }


    async onSubmit(e) {
        const focused = document.activeElement === this.fields.query.input; // remember if input field is focused
        if (e.submitter !== this.popstate_button) {
            // actual form submission, not browser history navigation => update url without page reloading
            const url = new URL(location);
            url.searchParams.set("q", this.fields.query.value);
            history.pushState({}, "", url);
        }
        loading.show(); // show "loading..." message
        try {
            await super.onSubmit(e); // submit the form
        } finally {
            loading.hide(); // hide "loading..." message
            if (focused) this.fields.query.input.focus(); // return focus on input if necessary
        }
    }

    onSuccess(show_message = false, clear = false) {
        const r = super.onSuccess(show_message, clear); // run super method
        search_results.innerHTML = ""; // clear search results container
        if (!this.result.length) {
            // no results found, so display message
            no_results.show();
            return;
        }
        no_results.hide(true); // make sure "no results found" message is hidden
        this.result.forEach(user_info => { // display search results
            insertUser(user_info, search_results);
        });
        return r; // return super method's return value
    }
}

const search_form = new SearchFrom("search-form"); // initialise search form
search_form.fields.query.value = get_url_query(); // set input field's value to query from url
// if form is valid (if query is not empty), submit to run search (but do not push history state)
if (search_form.validate()) search_form.form.requestSubmit(search_form.popstate_button);

// start listening for browser history navigation
addEventListener("popstate", () => {
    search_form.fields.query.value = get_url_query(); // update the input field's value
    search_form.form.requestSubmit(search_form.popstate_button); // run search (but do not push history state)
});
import {HideableElement} from "../api/ui.js";
import {insertUser} from "../interactions/interactions.js";
import {Form} from "../api/forms.js";

function get_url_query() {
    return new URLSearchParams(location.search).get("q");
}

const loading = new HideableElement("loading-search-results");
const no_results = new HideableElement("no-results");

const search_results = document.querySelector("#search-results");

class SearchFrom extends Form {
    success_message = null;

    constructor(id) {
        super(id);
        this.fields.query.ERROR_MESSAGES.valueMissing = () => "please enter a search query";
        this.popstate_button = document.createElement("input");
        this.popstate_button.type = "submit";
        this.popstate_button.hidden = true;
        this.form.append(this.popstate_button);
    }


    async onSubmit(e) {
        const focused = document.activeElement === this.fields.query.input;
        if (e.submitter !== this.popstate_button) {
            const url = new URL(location);
            url.searchParams.set("q", this.fields.query.value);
            history.pushState({}, "", url);
        }
        loading.show();
        try {
            await super.onSubmit(e);
        } finally {
            loading.hide();
            if (focused) this.fields.query.input.focus();
        }
    }

    onSuccess(show_message = false, clear = false) {
        const r = super.onSuccess(show_message, clear);
        search_results.innerHTML = "";
        if (!this.result.length) {
            no_results.show();
            return;
        }
        no_results.hide(true);
        this.result.forEach(user_info => {
            insertUser(user_info, search_results);
        });
        return r;
    }
}

const search_form = new SearchFrom("search-form");
search_form.fields.query.value = get_url_query().substring(0, search_form.fields.query.input.maxLength);
if (search_form.validate()) search_form.submit();

addEventListener("popstate", (e) => {
    search_form.fields.query.value = get_url_query();
    search_form.form.requestSubmit(search_form.popstate_button);
});
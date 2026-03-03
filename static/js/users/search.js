import {HideableElement} from "../api/ui.js";
import {insertUser} from "../interactions/interactions.js";
import {Form} from "../api/forms.js";

const query = new URLSearchParams(location.search).get("q");

const loading = new HideableElement("loading-search-results");
const no_results = new HideableElement("no-results");

const search_results = document.querySelector("#search-results");

class SearchFrom extends Form {
    success_message = null;

    constructor(id) {
        super(id);
        this.fields.query.ERROR_MESSAGES.valueMissing = () => "please enter a search query";
    }


    async onSubmit(e) {
        const focused = document.activeElement === this.fields.query.input;
        const url = new URL(location);
        url.searchParams.set("q", this.fields.query.value);
        history.pushState({}, "", url);
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
search_form.fields.query.value = query.substring(0, search_form.fields.query.input.maxLength);
if (search_form.validate()) search_form.submit();
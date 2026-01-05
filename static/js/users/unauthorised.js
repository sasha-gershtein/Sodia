import {api} from '../api/api.js';

const login_form = document.getElementById('sign-in');
const signup_form = document.getElementById('sign-up');

login_form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const identifier = login_form.identifier.value;
    const password = login_form.password.value;
    console.log(await api("/login", {identifier: identifier, password: password}))
})
# Sodia

**Sodia** (from **so**cial me**dia** — I know, I'm _very_ creative) is a web application, a social media for school
students. It is designed to help new students to meet people and make friends when they change schools.

This is my Computer Science A-Level project for NEA (non-exam assessment) completed in 2025 - 2026. This has to be done
fully by myself, so any contributions are not welcome and will not be accepted, unfortunately.

I'm learning to use Django, and for this project I decided not to use some of the build-in functionality in Django (such
as user authentication or the admin panel) to better understand how the back end of a web application can be designed
from scratch.

I also use pure JavaScript on the front end to make API requests for fetching data and actions that can often be done
with Django templates and automatic POST requests on form submission. This makes my app closer to a single-page
application. I think it'd be cooler to make an SPA from scratch, but this might be a stretch goal.

Despite (or, rather, due to) this being a learning project, I'm really trying to write good easy-to-maintain code.
I have also gone through the whole codebase to add elaborate comments and doc strings.

Things I'm using or implementing for the first time in a big project for Sodia:

* Django and web frameworks in general
* Relational SQL database
* Git and GitHub
* Full client and server side user input validation
* Secrets and cryptographically secure hashes
* Thread-safe programming and race conditions
* Asynchronous programming in JavaScript
* JavaScript classes and modules

Things I decided against:

* Any frontend frameworks
* Django REST Framework
* Websockets for live updates (I use polling instead)
* Supporting HTTPS
* Production hosting
* Responsive UI
* Localisation
* Logging

## References

Tutorials:

* [Python Django 7 Hour Course](https://www.youtube.com/watch?v=PtQiiknWUcI)
* [Git and GitHub - Full Course](https://www.youtube.com/watch?v=rH3zE7VlIMs)
* [Django Crash Course - Python Web Framework](https://www.youtube.com/watch?v=0roB7wZMLqI)
* [Django For Everybody - Full Python University Course](https://www.youtube.com/watch?v=o0XbHvKxw7Y)
* [Git Tutorial for Beginners: Learn Git in 1 Hour](https://www.youtube.com/watch?v=8JJ101D3knE)
* [Git Explained in 100 Seconds](https://www.youtube.com/watch?v=hwP7WQkmECE)
* [Modern Python logging](https://www.youtube.com/watch?v=9L77QExPmI0)
* [JavaScript OOP Crash Course (ES5 & ES6)](https://www.youtube.com/watch?v=vDJpGenyHaA)

Docs:

* [Django documentation](https://docs.djangoproject.com/en/6.0/ref/)
* [Python documentation](https://docs.python.org/3/)
* [Mozilla JavaScript reference](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/)
* [Mozilla HTML reference](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/)
* [Mozilla CSS reference](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/)

AI:

* [ChatGPT](https://chatgpt.com/)
* [Google Gemini](https://gemini.google.com/)
* [Claude](https://claude.ai/)

Other:

* [Stack Overflow](https://stackoverflow.com/)
* [Medium](https://medium.com/)
* [Can I Use](https://caniuse.com/)
* [Wikipedia](https://en.wikipedia.org/wiki/Main_Page)
* [Хабр (Habr)](https://habr.com/ru/feed/)

## AI use

Throughout development, I used large language models (LLMs) to help me design and implement features. AI helped me with:

* Learning a tool / framework / library (along with tutorials and docs)
* Learning about industry standards and common designs
* Remembering syntax / command / function
* Choosing one technical solution over another
* Proofreading my code
* Debugging

Some of the autocomplete functionality in my IDE (PyCharm) is probably powered by an LLM, but it never writes code by
itself.

Unless explicitly stated in code comments and my project report, I **never** used code written entirely by AI. All app's
functionality is implemented by me, and I made sure to understand exactly what every part of my code does.
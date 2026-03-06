// noinspection JSUnusedGlobalSymbols

export class PushOnlyDeque {
    #front = -1;
    #back = -1;
    #data = [];
    #prev = [];
    #next = [];

    constructor(array = []) {
        array.forEach((item) => this.pushBack(item));
    }

    get length() {
        return this.#data.length;
    }

    get front() {
        return this.#data[this.#front];
    }

    get back() {
        return this.#data[this.#back];
    }

    pushBack(item) {
        if (!this.length) {
            this.#prev.push(-1);
            this.#front = this.#back = 0;
        } else {
            this.#prev.push(this.#back);
            this.#back = this.#next[this.#back] = this.length;
        }
        this.#data.push(item);
        this.#next.push(-1);
    }

    pushFront(item) {
        if (!this.length) {
            this.#next.push(-1);
            this.#front = this.#back = 0;
        } else {
            this.#next.push(this.#front);
            this.#front = this.#prev[this.#front] = this.length;
        }
        this.#data.push(item);
        this.#prev.push(-1);
    }

    * #iterate() {
        let i = this.#front;
        while (i >= 0) {
            yield this.#data[i];
            i = this.#next[i];
        }
    }

    * #iterate_back() {
        let i = this.#back;
        while (i >= 0) {
            yield this.#data[i];
            i = this.#prev[i];
        }
    }

    [Symbol.iterator]() {
        return this.#iterate();
    };

    reversed() {
        const self = this;
        return {
            [Symbol.iterator]() {
                return self.#iterate_back();
            }
        }
    }
}
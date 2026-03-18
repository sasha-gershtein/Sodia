// noinspection JSUnusedGlobalSymbols

export class PushOnlyDeque {
    // doubly linked list data structure (double-ended queue)
    // only allows pushes to front and back, does not support deletion
    // insert in either direction is O(1), and iteration is O(n)

    // define private members
    #front = -1; // index of first element in #data
    #back = -1; // index of last element in #data
    #data = []; // array to store elements
    #prev = []; // array to store indexes of previous elements
    #next = []; // array to store indexes of following elements

    constructor(array = []) {
        // if instantiated with a non-empty array, add elements to the end sequentially
        array.forEach(item => this.pushBack(item));
    }

    get length() {
        // return the number of elements in the deque
        return this.#data.length;
    }

    get front() {
        // return the first element of the deque (undefined if empty)
        return this.#data[this.#front];
    }

    get back() {
        // return the last element of the deque (undefined if empty)
        return this.#data[this.#back];
    }

    pushBack(item) {
        // previous element of the newly added element is the old last element (-1 if deque was empty)
        this.#prev.push(this.#back);
        if (!this.length) {
            // deque is empty
            this.#front = this.#back = 0; // front and back point to the newly added first element
        } else {
            // last element and next of second-to-last are the newly added element
            this.#back = this.#next[this.#back] = this.length;
        }
        this.#data.push(item); // add element to #data
        this.#next.push(-1); // next of last does not exist
    }

    pushFront(item) {
        // next element of the newly added element is the old first element (-1 if deque was empty)
        this.#next.push(this.#front);
        if (!this.length) {
            // deque is empty
            this.#front = this.#back = 0; // front and back point to the newly added first element
        } else {
            // first element and previous of the second are newly added element
            this.#front = this.#prev[this.#front] = this.length;
        }
        this.#data.push(item); // add element to #data
        this.#prev.push(-1); // previous of first does not exist
    }

    * #iterate() {
        // generator for iteration
        let i = this.#front; // start from the first element
        while (i >= 0) { // until next doesn't exist
            yield this.#data[i]; // yield an element
            i = this.#next[i]; // get next
        }
    }

    * #iterate_back() {
        // generator for reversed iteration
        let i = this.#back; // start from the last element
        while (i >= 0) { // until previous doesn't exist
            yield this.#data[i]; // yield an element
            i = this.#prev[i]; // get previous
        }
    }

    [Symbol.iterator]() {
        return this.#iterate();
    };

    reversed() {
        // get a proxi object for reversed iteration
        const self = this; // define self for closure
        return {
            [Symbol.iterator]() {
                return self.#iterate_back();
            }
        }
    }
}
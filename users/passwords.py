"""This file defines the Password class to handle passwords hashes and verify them"""

import hashlib
import secrets
import base64
import os
from typing import overload


class Password:
    """Class for values of PasswordField that store a cryptographically secure hash of a password
    and implement verification methods"""
    # default settings
    ALGORITHM = "sha256"
    # passwords are hashed 200000 times in a row to make exhaustive search attack less time-efficient
    ITERATIONS = 200000
    __slots__ = (  # memory optimisation
        "algorithm",
        "iterations",
        "salt",
        "password_hash",
        "salt_string",
        "password_hash_string",
    )

    @staticmethod
    def get_hash(password, algorithm, salt, iterations):
        """return the hash of a password"""
        return hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)

    @classmethod
    def from_password(cls, password: str):
        """return a Password instance from a plaintext password"""
        return cls(password=password)

    @classmethod
    def from_db_value(cls, value: str):
        """return a Password instance from a db value"""
        return cls(db_string=value)

    @overload
    def __init__(self, db_string: str):
        ...

    @overload
    def __init__(self, password: str, *,
                 salt: bytes | None = None,
                 algorithm: str = ALGORITHM,
                 iterations: int = ITERATIONS):
        ...

    def __init__(
            self,
            password: str | None = None, *,  # plaintext password
            db_string: str | None = None,  # db value
            salt: bytes | None = None,
            algorithm: str = ALGORITHM,
            iterations: int = ITERATIONS
    ):
        if db_string is not None:
            try:
                algorithm, iterations, salt_string, password_hash_string = db_string.split(":")
                self.salt_string = salt_string
                self.password_hash_string = password_hash_string
                prefix, self.algorithm = algorithm.split("-", 1)
                if prefix != "pbkdf2":
                    raise ValueError(f"Unsupported algorithm: {algorithm}")
                self.iterations = int(iterations)
            except ValueError as e:
                raise ValueError(f"Wrong db string format: {db_string}") from e
            self.salt = base64.b64decode(salt_string)
            self.password_hash = base64.b64decode(password_hash_string)
            return

        self.algorithm = algorithm
        self.iterations = iterations
        # generate cryptographically secure random salt if not passed
        self.salt: bytes = os.urandom(32) if salt is None else salt
        if password is None:
            raise ValueError("Must provide either a password or a db_string")
        self.password_hash: bytes = self.get_hash(password, self.algorithm, self.salt, self.iterations)
        self.password_hash_string = base64.b64encode(self.password_hash).decode("ascii")
        self.salt_string = base64.b64encode(self.salt).decode("ascii")

    def verify(self, password: str) -> bool:
        """compare plaintext password to password hash (timing attack resistant)"""
        # hash string password using same salt
        # compare hashes using constant-time comparison to prevent timing attacks
        return secrets.compare_digest(self.password_hash,
                                      self.get_hash(password, self.algorithm, self.salt, self.iterations))

    def __eq__(self, other):
        """shorthand for self.verify(other: str) or compare hashes with another Password instance"""
        if isinstance(other, Password):
            return secrets.compare_digest(self.password_hash, other.password_hash)
        if isinstance(other, str):
            return self.verify(other)
        return NotImplemented

    def __str__(self):
        """get db value"""
        return f"pbkdf2-{self.algorithm}:{self.iterations}:{self.salt_string}:{self.password_hash_string}"

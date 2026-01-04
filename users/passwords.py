import hashlib
import secrets
import base64
import os


class Password:
    ALGORITHM = "sha256"
    ITERATIONS = 200000
    __slots__ = (
        "algorithm",
        "iterations",
        "salt",
        "password_hash",
        "salt_string",
        "password_hash_string",
    )

    @staticmethod
    def get_hash(password, algorithm, salt, iterations):
        return hashlib.pbkdf2_hmac(algorithm, password.encode("utf-8"), salt, iterations)

    @classmethod
    def from_password(cls, password: str):
        return cls(password=password)

    @classmethod
    def from_db_value(cls, value: str):
        return cls(db_string=value)

    def __init__(
            self,
            password: str | None = None, *,
            db_string: str | None = None,
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
        self.salt: bytes = os.urandom(32) if salt is None else salt
        if password is None:
            raise ValueError("Must provide either a password or a db_string")
        self.password_hash: bytes = self.get_hash(password, self.algorithm, self.salt, self.iterations)
        self.password_hash_string = base64.b64encode(self.password_hash).decode("ascii")
        self.salt_string = base64.b64encode(self.salt).decode("ascii")

    def verify(self, password: str) -> bool:
        return secrets.compare_digest(self.password_hash,
                                      self.get_hash(password, self.algorithm, self.salt, self.iterations))

    def __eq__(self, other):
        if isinstance(other, Password):
            return secrets.compare_digest(self.password_hash, other.password_hash)
        if isinstance(other, str):
            return self.verify(other)
        return NotImplemented

    def __str__(self):
        return f"pbkdf2-{self.algorithm}:{self.iterations}:{self.salt_string}:{self.password_hash_string}"

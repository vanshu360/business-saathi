"""Errors raised by services. main.py turns them into clear JSON responses."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class InvalidRequest(AppError):
    status_code = 400

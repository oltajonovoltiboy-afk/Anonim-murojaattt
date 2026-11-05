"""Servis qatlamidagi xatoliklar. API va bot ularni foydalanuvchiga tushunarli xabarga aylantiradi."""
from __future__ import annotations


class ServiceError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    status_code = 404


class PermissionDeniedError(ServiceError):
    status_code = 403


class ValidationFailedError(ServiceError):
    status_code = 422


class ConflictError(ServiceError):
    status_code = 409

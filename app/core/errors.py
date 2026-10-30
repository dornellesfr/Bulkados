from fastapi import HTTPException


class DomainError(HTTPException):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


class InvalidTokenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class RegistrationRejectedError(Exception):
    pass


class AuthProviderUnavailableError(Exception):
    pass


class CatalogUnavailableError(Exception):
    pass

import urllib.parse

from cryptography.fernet import Fernet
from sqlalchemy.engine.url import make_url

from app.core.config import settings

# Initialize Fernet cipher suite
cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_data(data: str) -> str:
    """Encrypts a string."""
    if not data:
        return data
    return cipher_suite.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypts a string."""
    if not encrypted_data:
        return encrypted_data
    return cipher_suite.decrypt(encrypted_data.encode()).decode()


# In a real production environment, this should be loaded from a secure configuration source.
ALLOWED_DB_DRIVERS = {"postgresql", "mysql", "mssql+pyodbc"}
ALLOWED_DB_HOSTS = {
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
}  # Add your trusted DB hosts here
ALLOWED_DB_PORTS = {5432, 3306, 1433, None}  # None allows default port


class ConnectionStringError(ValueError):
    """Custom exception for invalid connection strings."""

    pass


def validate_connection_string(connection_string: str) -> bool:
    """
    Validates a SQLAlchemy connection string against a pre-defined allowlist.

    Raises:
        ConnectionStringError: If any part of the connection string is disallowed.

    Returns:
        True if the connection string is valid.
    """
    if not connection_string:
        raise ConnectionStringError("Connection string cannot be empty.")

    try:
        url = make_url(connection_string)
    except Exception as e:
        raise ConnectionStringError(f"Invalid connection string format: {e}")

    if url.drivername not in ALLOWED_DB_DRIVERS:
        raise ConnectionStringError(
            f"Database driver '{url.drivername}' is not allowed."
        )

    if url.host not in ALLOWED_DB_HOSTS:
        # A simple check for common private IP ranges can be added for more security
        if not (url.host.startswith("192.168.") or url.host.startswith("10.")):
            raise ConnectionStringError(
                f"Database host '{url.host}' is not in the allowlist."
            )

    if url.port not in ALLOWED_DB_PORTS:
        raise ConnectionStringError(f"Database port '{url.port}' is not allowed.")

    # Check for potentially malicious query parameters
    if url.query and any(key in url.query for key in ["sslmode", "sslrootcert"]):
        if url.query.get("sslmode") == "disable":
            raise ConnectionStringError(
                "SSL mode 'disable' is not allowed for security reasons."
            )

    return True

# Import base64 for printing the ciphertext.
import base64

# Import the client library.
from google.cloud import kms
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def crc32c(data: bytes) -> int:
    import crcmod  # type: ignore

    crc32c_fun = crcmod.predefined.mkPredefinedCrcFun("crc-32c")
    return crc32c_fun(data)


def _get_kms_client_and_path(key_id: str):
    """
    Helper to get KMS client and key path from settings.
    """
    project_id = settings.GCP_PROJECT_ID
    location_id = settings.GCP_PROJECT_REGION
    key_ring_id = settings.GOOGLE_KMS_KEY_RING_ID

    if not all([project_id, location_id, key_ring_id, key_id]):
        logger.warning("Google KMS settings are missing. Operations may fail.")
        # We allow it to proceed to let the client raise error or for testing mock purposes,
        # but in production this will fail if called.
        pass

    client = kms.KeyManagementServiceClient()
    key_name = client.crypto_key_path(project_id, location_id, key_ring_id, key_id)
    return client, key_name


def decrypt_symmetric(ciphertext: str, key_id: str) -> str:
    """
    Decrypt the ciphertext using the symmetric key
    """
    # If debug mode is enabled, return the ciphertext without decrypting.
    if settings.DEBUG:
        return ciphertext

    client, key_name = _get_kms_client_and_path(key_id)

    # Decode the base64-encoded ciphertext string to bytes.
    ciphertext_bytes = base64.b64decode(ciphertext)

    # Optional, but recommended: compute ciphertext's CRC32C.
    # See crc32c() function defined below.
    ciphertext_crc32c = crc32c(ciphertext_bytes)

    # Call the API.
    decrypt_response = client.decrypt(
        request={
            "name": key_name,
            "ciphertext": ciphertext_bytes,
            "ciphertext_crc32c": ciphertext_crc32c,
        }
    )

    # Optional, but recommended: perform integrity verification on decrypt_response.
    # For more details on ensuring E2E in-transit integrity to and from Cloud KMS visit:
    # https://cloud.google.com/kms/docs/data-integrity-guidelines
    if not decrypt_response.plaintext_crc32c == crc32c(decrypt_response.plaintext):
        raise Exception("The response received from the server was corrupted in-transit.")
    # End integrity verification

    print(f"Plaintext: {decrypt_response.plaintext!r}")
    return decrypt_response.plaintext.decode("utf-8")


def encrypt_symmetric(plaintext: str, key_id: str) -> str:
    """
    Encrypt plaintext using a symmetric key.
    """
    # If debug mode is enabled, return the plaintext without encrypting.
    if settings.DEBUG:
        return plaintext

    # Convert the plaintext to bytes.
    plaintext_bytes = plaintext.encode("utf-8")

    # Optional, but recommended: compute plaintext's CRC32C.
    # See crc32c() function defined below.
    plaintext_crc32c = crc32c(plaintext_bytes)

    # Create the client.
    client, key_name = _get_kms_client_and_path(key_id)

    # Call the API.
    encrypt_response = client.encrypt(
        request={
            "name": key_name,
            "plaintext": plaintext_bytes,
            "plaintext_crc32c": plaintext_crc32c,
        }
    )

    # Optional, but recommended: perform integrity verification on encrypt_response.
    # For more details on ensuring E2E in-transit integrity to and from Cloud KMS visit:
    # https://cloud.google.com/kms/docs/data-integrity-guidelines
    if not encrypt_response.verified_plaintext_crc32c:
        raise Exception("The request sent to the server was corrupted in-transit.")
    if not encrypt_response.ciphertext_crc32c == crc32c(encrypt_response.ciphertext):
        raise Exception("The response received from the server was corrupted in-transit.")
    # End integrity verification

    print(f"Ciphertext: {base64.b64encode(encrypt_response.ciphertext)}")
    return base64.b64encode(encrypt_response.ciphertext).decode("utf-8")

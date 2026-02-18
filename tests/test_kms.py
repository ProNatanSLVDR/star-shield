from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from starshield.kms import crc32c, decrypt_symmetric, encrypt_symmetric


class TestCrc32c(TestCase):
    def test_returns_int(self):
        result = crc32c(b"hello")
        self.assertIsInstance(result, int)

    def test_consistent_output(self):
        self.assertEqual(crc32c(b"test"), crc32c(b"test"))

    def test_different_input_different_output(self):
        self.assertNotEqual(crc32c(b"hello"), crc32c(b"world"))


@override_settings(DEBUG=True)
class TestKmsDebugMode(TestCase):
    def test_decrypt_passthrough(self):
        result = decrypt_symmetric("plaintext-value", "key-id")
        self.assertEqual(result, "plaintext-value")

    def test_encrypt_passthrough(self):
        result = encrypt_symmetric("plaintext-value", "key-id")
        self.assertEqual(result, "plaintext-value")


@override_settings(
    DEBUG=False,
    GCP_PROJECT_ID="test-project",
    GCP_PROJECT_REGION="us-central1",
    GOOGLE_KMS_KEY_RING_ID="test-ring",
)
class TestKmsNonDebug(TestCase):
    @patch("starshield.kms.kms.KeyManagementServiceClient")
    def test_encrypt_symmetric(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.crypto_key_path.return_value = "projects/test/keys/test"

        plaintext = "secret-data"
        ciphertext_bytes = b"encrypted-bytes"

        mock_response = MagicMock()
        mock_response.verified_plaintext_crc32c = True
        mock_response.ciphertext = ciphertext_bytes
        mock_response.ciphertext_crc32c = crc32c(ciphertext_bytes)
        mock_client.encrypt.return_value = mock_response

        result = encrypt_symmetric(plaintext, "test-key")

        self.assertIsInstance(result, str)
        mock_client.encrypt.assert_called_once()

    @patch("starshield.kms.kms.KeyManagementServiceClient")
    def test_decrypt_symmetric(self, mock_client_cls):
        import base64

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.crypto_key_path.return_value = "projects/test/keys/test"

        plaintext_bytes = b"decrypted-data"
        ciphertext_b64 = base64.b64encode(b"encrypted-bytes").decode("utf-8")

        mock_response = MagicMock()
        mock_response.plaintext = plaintext_bytes
        mock_response.plaintext_crc32c = crc32c(plaintext_bytes)
        mock_client.decrypt.return_value = mock_response

        result = decrypt_symmetric(ciphertext_b64, "test-key")

        self.assertEqual(result, "decrypted-data")
        mock_client.decrypt.assert_called_once()

    @patch("starshield.kms.kms.KeyManagementServiceClient")
    def test_encrypt_integrity_check_fails_plaintext(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.crypto_key_path.return_value = "projects/test/keys/test"

        mock_response = MagicMock()
        mock_response.verified_plaintext_crc32c = False
        mock_client.encrypt.return_value = mock_response

        with self.assertRaises(Exception, msg="corrupted in-transit"):  # noqa: B017
            encrypt_symmetric("data", "test-key")

    @patch("starshield.kms.kms.KeyManagementServiceClient")
    def test_encrypt_integrity_check_fails_ciphertext(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.crypto_key_path.return_value = "projects/test/keys/test"

        mock_response = MagicMock()
        mock_response.verified_plaintext_crc32c = True
        mock_response.ciphertext = b"data"
        mock_response.ciphertext_crc32c = 99999  # Wrong CRC
        mock_client.encrypt.return_value = mock_response

        with self.assertRaises(Exception, msg="corrupted in-transit"):  # noqa: B017
            encrypt_symmetric("data", "test-key")

    @patch("starshield.kms.kms.KeyManagementServiceClient")
    def test_decrypt_integrity_check_fails(self, mock_client_cls):
        import base64

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.crypto_key_path.return_value = "projects/test/keys/test"

        mock_response = MagicMock()
        mock_response.plaintext = b"data"
        mock_response.plaintext_crc32c = 99999  # Wrong CRC
        mock_client.decrypt.return_value = mock_response

        ciphertext_b64 = base64.b64encode(b"encrypted").decode("utf-8")

        with self.assertRaises(Exception, msg="corrupted in-transit"):  # noqa: B017
            decrypt_symmetric(ciphertext_b64, "test-key")

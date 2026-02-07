from django.test import SimpleTestCase

from starshield.qrcodes import generate_qrcode_png, hex_to_rgb


class TestHexToRgb(SimpleTestCase):
    def test_common_colors(self):
        cases = [
            ("#000000", (0, 0, 0)),
            ("#FFFFFF", (255, 255, 255)),
            ("#FF0000", (255, 0, 0)),
            ("#00FF00", (0, 255, 0)),
            ("#0000FF", (0, 0, 255)),
            ("#0066ff", (0, 102, 255)),
        ]
        for hex_color, expected_rgb in cases:
            with self.subTest(hex_color=hex_color):
                self.assertEqual(hex_to_rgb(hex_color), expected_rgb)

    def test_without_hash_prefix(self):
        self.assertEqual(hex_to_rgb("FF5733"), (255, 87, 51))


class TestGenerateQrcodePng(SimpleTestCase):
    def test_returns_bytes(self):
        result = generate_qrcode_png("https://example.com")

        self.assertIsInstance(result, bytes)

    def test_starts_with_png_magic_bytes(self):
        result = generate_qrcode_png("https://example.com")

        self.assertTrue(result[:4] == b"\x89PNG")

    def test_custom_colors(self):
        result = generate_qrcode_png(
            "https://example.com",
            fill_color="#FF0000",
            background_color="#00FF00",
        )

        self.assertIsInstance(result, bytes)
        self.assertTrue(result[:4] == b"\x89PNG")

    def test_rounded_style(self):
        result = generate_qrcode_png("https://example.com", style="rounded")

        self.assertIsInstance(result, bytes)
        self.assertTrue(len(result) > 0)

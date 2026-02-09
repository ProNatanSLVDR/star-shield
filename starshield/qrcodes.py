import io

import qrcode
from PIL import Image, ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import (
    HorizontalGradiantColorMask,
    RadialGradiantColorMask,
    SolidFillColorMask,
    SquareGradiantColorMask,
    VerticalGradiantColorMask,
)
from qrcode.image.styles.moduledrawers import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def generate_qrcode_png(
    link: str,
    fill_color: str = "#000000",
    fill_color_secondary: str = "#000000",
    background_color: str = "#FFFFFF",
    style: str = "square",
    color_mask: str = "solid",
    logo_file=None,
    badge_file=None,
    box_size: int = 10,
    border: int = 4,
) -> bytes:
    """
    Generate a PNG QR code image with customization options.

    Args:
        link: The URL/data to encode in the QR code
        fill_color: Hex color for QR code modules (default: "#000000")
        background_color: Hex color for background (default: "#FFFFFF")
        style: "square" or "rounded" (default: "square")
        logo_file: Optional file-like object or path to logo image file
        box_size: Size of each QR code module in pixels (default: 10)
        border: Border size in modules (default: 4)

    Returns:
        bytes: PNG image data
    """

    color_f = hex_to_rgb(fill_color)
    color_f_sec = hex_to_rgb(fill_color_secondary)
    color_bg = hex_to_rgb(background_color)

    module_drawer_map = {
        "square": SquareModuleDrawer(),
        "square_spaced": GappedSquareModuleDrawer(),
        "rounded": RoundedModuleDrawer(),
        "circle": CircleModuleDrawer(),
    }

    color_mask_map = {
        "solid": SolidFillColorMask(back_color=color_bg, front_color=color_f),
        "round_radial": RadialGradiantColorMask(back_color=color_bg, center_color=color_f_sec, edge_color=color_f),
        "square_radial": SquareGradiantColorMask(back_color=color_bg, center_color=color_f_sec, edge_color=color_f),
        "horizontal_gradiant": HorizontalGradiantColorMask(
            back_color=color_bg, left_color=color_f_sec, right_color=color_f
        ),
        "vertical_gradiant": VerticalGradiantColorMask(
            back_color=color_bg, top_color=color_f_sec, bottom_color=color_f
        ),
    }

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Higher error correction for logo
        box_size=box_size,
        border=border,
    )
    qr.add_data(link)
    qr.make(fit=True)

    # Prepare logo with white rounded-rect background (handles transparent PNGs)
    embeded_image = None
    if logo_file:
        logo = Image.open(logo_file).convert("RGBA")
        padding = int(max(logo.size) * 0.15)
        bg_w = logo.width + padding * 2
        bg_h = logo.height + padding * 2
        radius = int(min(bg_w, bg_h) * 0.2)

        # Draw white rounded rectangle
        bg = Image.new("RGBA", (bg_w, bg_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bg)
        draw.rounded_rectangle([0, 0, bg_w - 1, bg_h - 1], radius=radius, fill=(255, 255, 255, 255))

        # Paste logo centered on the background
        bg.paste(logo, (padding, padding), logo)
        embeded_image = bg

    # Create QR code with square modules first
    img = qr.make_image(
        embeded_image=embeded_image,
        color_mask=color_mask_map[color_mask],
        module_drawer=module_drawer_map[style],
        image_factory=StyledPilImage,
    )
    img = img.convert("RGBA")

    # Composite destination badge in bottom-right corner
    if badge_file:
        badge = Image.open(badge_file).convert("RGBA")
        badge_size = int(img.width * 0.05)
        badge = badge.resize((badge_size, badge_size), Image.LANCZOS)
        margin = int(img.width * 0.02)
        x = img.width - badge_size - margin
        y = img.height - badge_size - margin
        img.paste(badge, (x, y), badge)

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes.getvalue()

"""
Choice constants for models.
"""

# QR Code Style Choices
QR_STYLE_CHOICES = [
    ("square", "Carré"),
    ("square_spaced", "Carré espacé"),
    ("rounded", "Arrondi"),
    ("circle", "Cercle"),
]

# QR Code Color Mask Choices
QR_COLOR_MASK_CHOICES = [
    ("solid", "Solide"),
    ("round_radial", "Dégradé radial rond"),
    ("square_radial", "Dégradé radial carré"),
    ("horizontal_gradiant", "Dégradé horizontal"),
    ("vertical_gradiant", "Dégradé vertical"),
]

# QR Code Routing Choices
QR_ROUTING_CHOICES = [
    ("feedback", "Feedback"),
    ("roulette", "Roulette"),
]

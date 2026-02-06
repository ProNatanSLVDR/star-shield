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
    ("verify", "Vérification des codes"),
]

# AI Response Choices
AI_TONE_CHOICES = [
    ("professionnel", "Professionnel"),
    ("empathique", "Empathique"),
    ("enthousiaste", "Enthousiaste"),
    ("amical", "Amical"),
    ("concis", "Concis"),
]

AI_LENGTH_CHOICES = [
    ("short", "Courte"),
    ("medium", "Moyenne"),
    ("long", "Longue"),
]

AI_LANGUAGE_CHOICES = [
    ("fr", "Français"),
    ("en", "English"),
    ("auto", "Auto-detect"),
]

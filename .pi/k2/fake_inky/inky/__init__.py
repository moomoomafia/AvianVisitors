"""K2 fake Inky driver (.pi/ only, D20). frame/display.py push_panel lazy-imports
`inky.auto.auto` or `inky.inky_el133uf1.Inky`; this package stands in for both and
records every push so a test can assert "the panel was (not) touched"."""

PUSHES = []


class FakeInky:
    width, height = 1600, 1200

    def __init__(self, resolution=(1600, 1200)):
        self.width, self.height = resolution
        self.image = None

    def set_image(self, image, saturation=0.5):
        self.image = image.copy()

    def show(self):
        PUSHES.append(self.image)

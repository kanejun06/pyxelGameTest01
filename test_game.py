import pyxel

class App:
    def __init__(self):
        pyxel.init(256, 256)
        self.x = 128
        self.y = 128
        self.color = pyxel.COLOR_RED
        pyxel.run(self.update, self.draw)
        
    def update(self):
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.x = min(self.x + 4, pyxel.width - 16)
        if pyxel.btn(pyxel.KEY_LEFT):
            self.x = max(self.x - 4, 0)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.y = min(self.y + 4, pyxel.height - 16)
        if pyxel.btn(pyxel.KEY_UP):
            self.y = max(self.y - 4, 0)
        
    def draw(self):
        pyxel.cls(7)
        pyxel.rect(self.x, self.y, 16, 16, self.color)

if __name__ == '__main__':
    App()

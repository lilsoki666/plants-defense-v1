
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from random import randint, choice
import json
import os

Window.clearcolor = (0.04, 0.10, 0.08, 1)

COLS = 8
ROWS = 5

PLANTS = {
    "sun": {"name": "Surya", "cost": 50, "hp": 100},
    "pea": {"name": "Penembak", "cost": 100, "hp": 100},
    "wall": {"name": "Pelindung", "cost": 50, "hp": 450},
    "ice": {"name": "Es", "cost": 175, "hp": 100},
}

class GameBoard(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plants = {}
        self.zombies = []
        self.bullets = []
        self.energy = 150
        self.selected = "pea"
        self.elapsed = 0
        self.spawn_timer = 0
        self.sun_timer = 0
        self.kills = 0
        self.state = "playing"
        self.bind(pos=self.draw, size=self.draw)
        Clock.schedule_interval(self.update, 1 / 30)

    def cell(self, col, row):
        cw = self.width / COLS
        ch = self.height / ROWS
        return self.x + col * cw, self.y + row * ch, cw, ch

    def plant_at(self, col, row):
        if self.state != "playing":
            return
        key = (col, row)
        if key in self.plants:
            return

        data = PLANTS[self.selected]
        if self.energy < data["cost"]:
            return

        self.energy -= data["cost"]
        self.plants[key] = {
            "type": self.selected,
            "hp": data["hp"],
            "timer": 0,
        }
        self.draw()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if self.state != "playing":
            return True

        cw = self.width / COLS
        ch = self.height / ROWS
        col = int((touch.x - self.x) / cw)
        row = int((touch.y - self.y) / ch)
        if 0 <= col < COLS and 0 <= row < ROWS:
            self.plant_at(col, row)
        return True

    def spawn_zombie(self):
        row = randint(0, ROWS - 1)
        level = int(self.elapsed / 35)
        kind = choice(["basic", "basic", "helmet"])
        hp = 100 + level * 25
        speed = 13 + randint(0, 5) + level
        if kind == "helmet":
            hp *= 2
            speed *= 0.75
        self.zombies.append({
            "x": self.x + self.width + dp(12),
            "row": row,
            "hp": hp,
            "maxhp": hp,
            "speed": speed,
            "kind": kind,
            "attack": 0,
        })

    def update(self, dt):
        if self.state != "playing":
            return

        self.elapsed += dt
        self.spawn_timer += dt
        self.sun_timer += dt

        interval = max(2.8, 7.0 - self.elapsed / 100)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            self.spawn_zombie()

        if self.sun_timer >= 6:
            self.sun_timer = 0
            for p in self.plants.values():
                if p["type"] == "sun":
                    self.energy += 25

        # Tanaman menembak zombie pada jalur yang sama.
        for (col, row), p in list(self.plants.items()):
            p["timer"] += dt
            if p["type"] in ("pea", "ice") and p["timer"] >= 1.2:
                px, py, cw, ch = self.cell(col, row)
                self.bullets.append({
                    "x": px + cw * 0.75,
                    "row": row,
                    "speed": 210,
                    "damage": 25 if p["type"] == "pea" else 15,
                    "ice": p["type"] == "ice",
                })
                p["timer"] = 0

        for b in self.bullets[:]:
            b["x"] += b["speed"] * dt
            hit = None
            for z in self.zombies:
                if z["row"] == b["row"] and abs(z["x"] - b["x"]) < dp(20):
                    hit = z
                    break
            if hit:
                hit["hp"] -= b["damage"]
                if b["ice"]:
                    hit["speed"] *= 0.75
                self.bullets.remove(b)
                if hit["hp"] <= 0:
                    self.zombies.remove(hit)
                    self.kills += 1
                    self.energy += 10
            elif b["x"] > self.x + self.width:
                self.bullets.remove(b)

        for z in self.zombies[:]:
            col = int((z["x"] - self.x) / (self.width / COLS))
            key = (col, z["row"])
            plant = self.plants.get(key)

            if plant:
                z["attack"] += dt
                if z["attack"] >= 0.7:
                    plant["hp"] -= 20
                    z["attack"] = 0
                    if plant["hp"] <= 0:
                        del self.plants[key]
            else:
                z["x"] -= z["speed"] * dt

            if z["x"] <= self.x:
                self.state = "lost"

        if self.kills >= 25:
            self.state = "won"

        self.draw()
        app = App.get_running_app()
        if app and app.hud:
            app.hud.text = (
                f"Energi: {self.energy}   "
                f"Musuh dikalahkan: {self.kills}/25   "
                f"{self.state.upper() if self.state != 'playing' else ''}"
            )

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.12, 0.35, 0.16, 1)
            Rectangle(pos=self.pos, size=self.size)

            cw = self.width / COLS
            ch = self.height / ROWS

            for row in range(ROWS):
                for col in range(COLS):
                    px, py, w, h = self.cell(col, row)
                    if (row + col) % 2 == 0:
                        Color(0.19, 0.44, 0.19, 1)
                    else:
                        Color(0.16, 0.39, 0.17, 1)
                    Rectangle(pos=(px, py), size=(w, h))
                    Color(0.45, 0.65, 0.38, 0.6)
                    Line(rectangle=(px, py, w, h), width=0.5)

            # Tanaman: bentuk sederhana agar tak perlu file gambar.
            for (col, row), p in self.plants.items():
                px, py, w, h = self.cell(col, row)
                cx, cy = px + w * .5, py + h * .5
                typ = p["type"]

                Color(0.12, 0.65, 0.20, 1)
                Rectangle(pos=(cx-w*.04, cy-h*.25), size=(w*.08, h*.3))
                Color(0.1, 0.8, 0.25, 1)
                Ellipse(pos=(cx-w*.22, cy-h*.27), size=(w*.22, h*.12))
                Ellipse(pos=(cx, cy-h*.27), size=(w*.22, h*.12))

                if typ == "sun":
                    Color(1, .75, .05, 1)
                    Ellipse(pos=(cx-w*.25, cy-h*.05), size=(w*.5, h*.5))
                    Color(1, .9, .25, 1)
                    Ellipse(pos=(cx-w*.17, cy+h*.03), size=(w*.34, h*.34))
                elif typ == "wall":
                    Color(.65, .38, .12, 1)
                    Ellipse(pos=(cx-w*.28, cy-h*.18), size=(w*.56, h*.48))
                    Color(.95, .78, .45, 1)
                    Ellipse(pos=(cx-w*.15, cy-h*.02), size=(w*.08, h*.08))
                    Ellipse(pos=(cx+w*.07, cy-h*.02), size=(w*.08, h*.08))
                else:
                    Color(.3, .9, .15, 1) if typ == "pea" else Color(.2, .8, 1, 1)
                    Ellipse(pos=(cx-w*.28, cy-h*.04), size=(w*.48, h*.35))
                    Ellipse(pos=(cx+w*.02, cy+h*.02), size=(w*.27, h*.22))
                    Color(.04, .12, .04, 1)
                    Ellipse(pos=(cx+w*.17, cy+h*.10), size=(w*.045, h*.06))

            # Peluru.
            for b in self.bullets:
                px, py, w, h = self.cell(0, b["row"])
                Color(.3, .9, 1, 1) if b["ice"] else Color(.65, 1, .15, 1)
                Ellipse(pos=(b["x"], py+h*.48), size=(dp(12), dp(12)))

            # Zombie.
            for z in self.zombies:
                px, py, w, h = self.cell(0, z["row"])
                zy = py + h * .2
                zx = z["x"]
                Color(.35, .48, .32, 1)
                Ellipse(pos=(zx, zy+h*.28), size=(w*.38, h*.43))
                Color(.22, .27, .20, 1)
                Rectangle(pos=(zx+w*.05, zy), size=(w*.25, h*.3))
                Color(.92, .9, .72, 1)
                Ellipse(pos=(zx+w*.08, zy+h*.48), size=(w*.07, h*.07))
                Ellipse(pos=(zx+w*.23, zy+h*.48), size=(w*.07, h*.07))
                if z["kind"] == "helmet":
                    Color(.65, .68, .72, 1)
                    Rectangle(pos=(zx-w*.02, zy+h*.66), size=(w*.43, h*.12))
                # Bar HP.
                Color(.15, .08, .08, 1)
                Rectangle(pos=(zx, zy+h*.77), size=(w*.4, dp(4)))
                Color(.2, .9, .25, 1)
                Rectangle(pos=(zx, zy+h*.77),
                          size=(w*.4*max(0, z["hp"]/z["maxhp"]), dp(4)))

class PlantDefenseApp(App):
    def build(self):
        self.hud = Label(
            text="Energi: 150   Pilih tanaman lalu sentuh petak",
            size_hint_y=None, height=dp(38)
        )

        root = BoxLayout(orientation="vertical", padding=dp(5), spacing=dp(5))
        root.add_widget(self.hud)

        bar = GridLayout(cols=4, size_hint_y=None, height=dp(52), spacing=dp(4))
        self.board = GameBoard()
        self.buttons = {}

        for key, data in PLANTS.items():
            btn = Button(
                text=f"{data['name']}\n{data['cost']} energi",
                font_size=dp(11)
            )
            btn.bind(on_release=lambda b, k=key: self.select(k))
            bar.add_widget(btn)
            self.buttons[key] = btn

        root.add_widget(bar)
        root.add_widget(self.board)

        bottom = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        restart = Button(text="Ulangi")
        restart.bind(on_release=self.restart)
        bottom.add_widget(restart)
        root.add_widget(bottom)
        return root

    def select(self, key):
        self.board.selected = key
        self.hud.text = (
            f"Tanaman: {PLANTS[key]['name']} — "
            f"Biaya {PLANTS[key]['cost']} energi. Sentuh petak."
        )

    def restart(self, *args):
        self.board.plants.clear()
        self.board.zombies.clear()
        self.board.bullets.clear()
        self.board.energy = 150
        self.board.elapsed = 0
        self.board.spawn_timer = 0
        self.board.sun_timer = 0
        self.board.kills = 0
        self.board.state = "playing"
        self.hud.text = "Energi: 150   Pilih tanaman lalu sentuh petak"
        self.board.draw()

if __name__ == "__main__":
    PlantDefenseApp().run()

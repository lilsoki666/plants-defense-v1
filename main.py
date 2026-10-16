
# -*- coding: utf-8 -*-
"""Plant Defense - offline tower-defense with pixel-art graphics."""
import random
import math
from dataclasses import dataclass

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, Line, Triangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

GAME_TITLE = "PLANT DEFENSE"
LANES, COLUMNS = 5, 9
WIN_KILLS = 25
START_SUN = 200
SUN_INTERVAL = 6.5
ZOMBIE_INTERVAL_START = 5.0

COSTS = {"pea": 100, "ice": 125, "sun": 50, "wall": 75}


@dataclass
class Plant:
    row: int
    col: int
    kind: str
    cooldown: float = 0.0
    hp: float = 100.0
    anim: float = 0.0


@dataclass
class Zombie:
    row: int
    x: float
    hp: float
    max_hp: float
    speed: float
    attack_timer: float = 0.0
    anim: float = 0.0
    slow_timer: float = 0.0


@dataclass
class Projectile:
    row: int
    x: float
    y: float
    damage: float
    speed: float
    kind: str = "pea"


class GameBoard(Widget):
    """Game world rendered with Kivy canvas and pixel-style shapes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plants = []
        self.zombies = []
        self.projectiles = []
        self.sun = START_SUN
        self.kills = 0
        self.elapsed = 0.0
        self.spawn_timer = 2.5
        self.sun_timer = SUN_INTERVAL
        self.game_state = "playing"
        self.selected_plant = "pea"
        self.cell_w = self.cell_h = 1.0
        self.board_x = self.board_y = 0.0
        self.board_w = self.board_h = 1.0
        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def reset(self):
        self.plants.clear()
        self.zombies.clear()
        self.projectiles.clear()
        self.sun = START_SUN
        self.kills = 0
        self.elapsed = 0.0
        self.spawn_timer = 2.5
        self.sun_timer = SUN_INTERVAL
        self.game_state = "playing"
        self.redraw()

    def select_plant(self, kind):
        self.selected_plant = kind

    def plant_cost(self, kind):
        return COSTS.get(kind, 100)

    def board_geometry(self):
        margin = dp(7)
        self.board_x = self.x + margin
        self.board_y = self.y + margin
        self.board_w = max(1, self.width - margin * 2)
        self.board_h = max(1, self.height - margin * 2)
        self.cell_w = self.board_w / COLUMNS
        self.cell_h = self.board_h / LANES

    def on_touch_down(self, touch):
        if self.game_state != "playing":
            return super().on_touch_down(touch)
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.board_geometry()
        bx = touch.x - self.board_x
        by = touch.y - self.board_y

        if bx < 0 or by < 0 or bx >= self.board_w or by >= self.board_h:
            return super().on_touch_down(touch)

        col = int(bx / self.cell_w)
        row = LANES - 1 - int(by / self.cell_h)

        if not (0 <= row < LANES and 0 <= col < COLUMNS):
            return True
        if any(p.row == row and p.col == col for p in self.plants):
            return True

        cost = self.plant_cost(self.selected_plant)
        if self.sun < cost:
            return True

        self.sun -= cost
        hp = 300.0 if self.selected_plant == "wall" else 100.0
        self.plants.append(
            Plant(row, col, self.selected_plant, hp=hp)
        )
        self.redraw()
        return True

    def update(self, dt):
        if self.game_state != "playing":
            self.redraw()
            return

        dt = min(dt, 0.06)
        self.elapsed += dt
        self.spawn_timer -= dt
        self.sun_timer -= dt

        # Passive energy generation.
        if self.sun_timer <= 0:
            self.sun += 25
            self.sun_timer = SUN_INTERVAL

        # Waves gradually become more difficult.
        spawn_interval = max(1.65, ZOMBIE_INTERVAL_START - self.elapsed / 115.0)
        if self.spawn_timer <= 0:
            self.spawn_zombie()
            self.spawn_timer = spawn_interval * random.uniform(0.82, 1.18)

        # Plant behavior.
        for p in self.plants[:]:
            p.anim += dt
            p.cooldown -= dt

            if p.kind == "sun":
                if p.cooldown <= 0:
                    self.sun += 25
                    p.cooldown = 7.0
                continue

            if p.kind == "wall":
                continue

            targets = [
                z for z in self.zombies
                if z.row == p.row and z.x > self.plant_x(p.col)
            ]

            if targets and p.cooldown <= 0:
                px = self.plant_x(p.col) + self.cell_w * 0.24
                py = self.lane_y(p.row) + self.cell_h * 0.12

                if p.kind == "ice":
                    self.projectiles.append(
                        Projectile(p.row, px, py, 14, self.cell_w * 2.0, "ice")
                    )
                    p.cooldown = 1.55
                else:
                    self.projectiles.append(
                        Projectile(p.row, px, py, 20, self.cell_w * 2.65, "pea")
                    )
                    p.cooldown = 1.05

        # Projectile movement and collisions.
        for shot in self.projectiles[:]:
            shot.x += shot.speed * dt
            hit = next(
                (
                    z for z in self.zombies
                    if z.row == shot.row
                    and abs(z.x - shot.x) < self.cell_w * 0.23
                ),
                None,
            )

            if hit:
                hit.hp -= shot.damage
                if shot.kind == "ice":
                    hit.speed = min(hit.speed, self.cell_w * 0.07)
                    hit.slow_timer = 2.8
                self.projectiles.remove(shot)
            elif shot.x > self.board_x + self.board_w + self.cell_w:
                self.projectiles.remove(shot)

        # Zombies attack plants or advance.
        for z in self.zombies[:]:
            z.anim += dt
            if z.slow_timer > 0:
                z.slow_timer -= dt

            blocker = next(
                (
                    p for p in self.plants
                    if p.row == z.row
                    and abs(z.x - self.plant_x(p.col)) < self.cell_w * 0.34
                ),
                None,
            )

            if blocker:
                z.attack_timer -= dt
                if z.attack_timer <= 0:
                    blocker.hp -= 12 if blocker.kind == "wall" else 20
                    z.attack_timer = 0.72
                    if blocker.hp <= 0 and blocker in self.plants:
                        self.plants.remove(blocker)
            else:
                z.x -= z.speed * (0.48 if z.slow_timer > 0 else 1.0) * dt

            if z.hp <= 0:
                self.zombies.remove(z)
                self.kills += 1
                self.sun += 15
                continue

            if z.x < self.board_x - self.cell_w * 0.28:
                self.game_state = "lost"

        if self.kills >= WIN_KILLS:
            self.game_state = "won"

        self.redraw()

    def spawn_zombie(self):
        row = random.randrange(LANES)
        hp = random.choice([78.0, 95.0, 115.0])
        hp += min(65, self.elapsed * 0.16)
        speed = self.cell_w * random.uniform(0.065, 0.095)
        self.zombies.append(
            Zombie(
                row,
                self.board_x + self.board_w + self.cell_w * 0.35,
                hp,
                hp,
                speed,
            )
        )

    def plant_x(self, col):
        return self.board_x + (col + 0.5) * self.cell_w

    def lane_y(self, row):
        return self.board_y + (LANES - row - 0.5) * self.cell_h

    def diamond(self, cx, cy, hw, hh, colors):
        """Draw a diamond tile with three shaded faces."""
        top = (cx, cy + hh)
        right = (cx + hw, cy)
        bottom = (cx, cy - hh)
        left = (cx - hw, cy)

        Color(*colors[0])
        Triangle(points=[*top, *left, *bottom])
        Color(*colors[1])
        Triangle(points=[*top, *right, *bottom])
        Color(*colors[2])
        Line(points=[*top, *right, *bottom, *left, *top], width=0.8)

    def pixel_plant(self, p, cx, cy, s):
        """Draw a small blocky character without external image assets."""
        bob = abs(math.sin(p.anim * 4.0)) * s * 0.035

        if p.kind == "sun":
            Color(0.98, 0.72, 0.15, 1)
            Rectangle(pos=(cx-s*.20, cy+s*.30+bob), size=(s*.40, s*.40))
            Color(1.0, 0.9, 0.35, 1)
            Rectangle(pos=(cx-s*.11, cy+s*.39+bob), size=(s*.22, s*.22))
            Color(0.18, 0.62, 0.25, 1)
            Rectangle(pos=(cx-s*.07, cy-s*.27), size=(s*.14, s*.45))
            Color(0.27, 0.76, 0.29, 1)
            Rectangle(pos=(cx-s*.31, cy-s*.08), size=(s*.25, s*.12))
            return

        if p.kind == "wall":
            Color(0.48, 0.31, 0.19, 1)
            Rectangle(pos=(cx-s*.27, cy-s*.27), size=(s*.54, s*.60))
            Color(0.68, 0.48, 0.28, 1)
            Rectangle(pos=(cx-s*.22, cy+s*.03), size=(s*.44, s*.22))
            Color(0.25, 0.18, 0.12, 1)
            Rectangle(pos=(cx-s*.14, cy-s*.04), size=(s*.07, s*.07))
            Rectangle(pos=(cx+s*.07, cy-s*.04), size=(s*.07, s*.07))
            return

        Color(0.14, 0.48, 0.20, 1)
        Rectangle(pos=(cx-s*.06, cy-s*.30), size=(s*.12, s*.34))
        Color(0.20, 0.68, 0.27, 1)
        Rectangle(pos=(cx-s*.30, cy-s*.20), size=(s*.22, s*.10))
        Rectangle(pos=(cx+s*.08, cy-s*.14), size=(s*.22, s*.10))

        if p.kind == "ice":
            Color(0.25, 0.70, 0.91, 1)
            Rectangle(pos=(cx-s*.23, cy+s*.03+bob), size=(s*.46, s*.39))
            Color(0.63, 0.92, 1.0, 1)
            Rectangle(pos=(cx-s*.15, cy+s*.17+bob), size=(s*.16, s*.13))
            Color(0.06, 0.28, 0.47, 1)
            Rectangle(pos=(cx-s*.12, cy+s*.13+bob), size=(s*.06, s*.07))
            Rectangle(pos=(cx+s*.08, cy+s*.13+bob), size=(s*.06, s*.07))
        else:
            Color(0.21, 0.70, 0.26, 1)
            Rectangle(pos=(cx-s*.23, cy+s*.03+bob), size=(s*.46, s*.39))
            Color(0.35, 0.88, 0.31, 1)
            Rectangle(pos=(cx-s*.15, cy+s*.23+bob), size=(s*.15, s*.12))
            Color(0.08, 0.28, 0.12, 1)
            Rectangle(pos=(cx-s*.12, cy+s*.15+bob), size=(s*.06, s*.07))
            Rectangle(pos=(cx+s*.08, cy+s*.15+bob), size=(s*.06, s*.07))
            Color(0.11, 0.43, 0.17, 1)
            Rectangle(pos=(cx+s*.17, cy+s*.10+bob), size=(s*.18, s*.14))

    def pixel_zombie(self, z, cx, cy, s):
        walk = int(math.sin(z.anim * 7.0) * s * 0.035)

        Color(0.03, 0.08, 0.05, 0.38)
        Ellipse(pos=(cx-s*.32, cy-s*.30), size=(s*.64, s*.16))

        Color(0.25, 0.32, 0.28, 1)
        Rectangle(pos=(cx-s*.20+walk, cy-s*.28), size=(s*.15, s*.28))
        Rectangle(pos=(cx+s*.05-walk, cy-s*.28), size=(s*.15, s*.28))

        Color(0.36, 0.47, 0.36, 1)
        Rectangle(pos=(cx-s*.24, cy-s*.01), size=(s*.48, s*.43))
        Color(0.48, 0.58, 0.42, 1)
        Rectangle(pos=(cx-s*.20, cy+s*.22), size=(s*.40, s*.17))

        Color(0.20, 0.31, 0.25, 1)
        Rectangle(pos=(cx-s*.31, cy+s*.02), size=(s*.12, s*.25))
        Rectangle(pos=(cx+s*.19, cy+s*.02), size=(s*.12, s*.25))

        Color(0.55, 0.65, 0.47, 1)
        Rectangle(pos=(cx-s*.20, cy+s*.23), size=(s*.40, s*.27))
        Color(0.08, 0.10, 0.08, 1)
        Rectangle(pos=(cx-s*.11, cy+s*.34), size=(s*.07, s*.07))
        Rectangle(pos=(cx+s*.06, cy+s*.34), size=(s*.07, s*.07))
        Color(0.32, 0.12, 0.12, 1)
        Rectangle(pos=(cx-s*.06, cy+s*.24), size=(s*.13, s*.04))

        bw = s * .65
        bh = max(dp(2), s * .045)
        bx, by = cx - bw/2, cy + s*.60
        Color(0.10, 0.12, 0.10, 1)
        Rectangle(pos=(bx, by), size=(bw, bh))
        Color(0.88, 0.20, 0.16, 1)
        Rectangle(
            pos=(bx, by),
            size=(bw * max(0, min(1, z.hp/z.max_hp)), bh),
        )

    def redraw(self, *_args):
        self.board_geometry()
        self.canvas.clear()

        with self.canvas:
            Color(0.035, 0.075, 0.085, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Pixelated distant landscape.
            Color(0.07, 0.16, 0.15, 1)
            for i in range(12):
                Rectangle(
                    pos=(self.x+i*self.width/11,
                         self.y+self.height*.86+(i%3)*dp(3)),
                    size=(self.width/14, dp(3)),
                )

            Color(0.015, 0.04, 0.025, 0.40)
            Rectangle(pos=(self.board_x, self.board_y),
                      size=(self.board_w, self.board_h))

            # Diamond tiles give the field an isometric-inspired look.
            for row in range(LANES):
                for col in range(COLUMNS):
                    cx = self.board_x + (col+.5)*self.cell_w
                    cy = self.board_y + (row+.5)*self.cell_h
                    hw, hh = self.cell_w*.51, self.cell_h*.49
                    if (row+col) % 2 == 0:
                        shades = [
                            (.16,.40,.22,1),
                            (.22,.49,.26,1),
                            (.10,.30,.16,1),
                        ]
                    else:
                        shades = [
                            (.13,.34,.19,1),
                            (.19,.43,.23,1),
                            (.09,.27,.14,1),
                        ]
                    self.diamond(cx, cy, hw, hh, shades)
                    Color(.35,.57,.27,.45)
                    Rectangle(
                        pos=(cx-hw*.45, cy-hh*.18),
                        size=(max(1,hw*.10), max(1,hh*.09)),
                    )

            Color(.75,.88,.62,.18)
            for row in range(1, LANES):
                y = self.board_y + row*self.cell_h
                Line(points=[self.board_x,y,
                             self.board_x+self.board_w,y], width=.7)

            for p in self.plants:
                cx, cy = self.plant_x(p.col), self.lane_y(p.row)
                s = min(self.cell_w*.76, self.cell_h*.95)
                Color(.02,.05,.02,.35)
                Ellipse(pos=(cx-s*.34,cy-s*.27),size=(s*.68,s*.18))
                self.pixel_plant(p,cx,cy,s)

                max_hp = 300 if p.kind == "wall" else 100
                if p.hp < max_hp:
                    bw, bh = s*.62, max(dp(2),s*.04)
                    by = cy-s*.39
                    Color(.08,.09,.08,1)
                    Rectangle(pos=(cx-bw/2,by),size=(bw,bh))
                    Color(.94,.64,.16,1)
                    Rectangle(
                        pos=(cx-bw/2,by),
                        size=(bw*max(0,p.hp/max_hp),bh),
                    )

            for shot in self.projectiles:
                r = max(dp(3), self.cell_h*.07)
                if shot.kind == "ice":
                    Color(.55,.91,1,1)
                    Rectangle(pos=(shot.x-r,shot.y-r),size=(r*2,r*2))
                    Color(.85,.98,1,1)
                    Rectangle(pos=(shot.x-r*.35,shot.y-r*.35),
                              size=(r*.7,r*.7))
                else:
                    Color(.58,.94,.25,1)
                    Rectangle(pos=(shot.x-r,shot.y-r),size=(r*2,r*2))
                    Color(.82,1,.48,1)
                    Rectangle(pos=(shot.x-r*.35,shot.y-r*.35),
                              size=(r*.7,r*.7))

            for z in self.zombies:
                self.pixel_zombie(
                    z, z.x, self.lane_y(z.row),
                    min(self.cell_w*.76,self.cell_h*.88),
                )

            Color(.62,.82,.43,.85)
            Line(rectangle=(self.board_x,self.board_y,
                            self.board_w,self.board_h),width=1.2)

            if self.game_state in ("won","lost"):
                Color(.015,.025,.025,.78)
                Rectangle(pos=self.pos,size=self.size)


class PlantDefenseApp(App):
    def build(self):
        self.title = GAME_TITLE
        Window.clearcolor = (.035,.075,.08,1)
        root = BoxLayout(
            orientation="vertical", padding=dp(7), spacing=dp(5)
        )

        header = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(40), spacing=dp(7),
        )
        self.title_label = Label(
            text="[b]PLANT DEFENSE[/b]", markup=True,
            font_size="19sp", color=(.78,1,.69,1), halign="left",
        )
        self.sun_label = Label(
            text="SUN 200", font_size="15sp", color=(1,.82,.28,1),
            size_hint_x=None, width=dp(85),
        )
        self.score_label = Label(
            text="KILLS 0/25", font_size="14sp",
            color=(.92,.96,.89,1), size_hint_x=None, width=dp(105),
        )
        header.add_widget(self.title_label)
        header.add_widget(self.sun_label)
        header.add_widget(self.score_label)
        root.add_widget(header)

        toolbar = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(46), spacing=dp(4),
        )
        self.buttons = {}
        options = [
            ("pea","PEA 100",(.15,.48,.22,1)),
            ("ice","ICE 125",(.10,.38,.55,1)),
            ("sun","SUN 50",(.55,.39,.08,1)),
            ("wall","WALL 75",(.40,.27,.17,1)),
        ]
        for kind, label, color in options:
            b = Button(
                text=label, font_size="11sp",
                background_normal="", background_color=color,
            )
            b.bind(on_release=lambda _b,k=kind:self.choose_plant(k))
            toolbar.add_widget(b)
            self.buttons[kind] = b

        self.restart_button = Button(
            text="RESTART", size_hint_x=None, width=dp(83),
            font_size="11sp", background_normal="",
            background_color=(.52,.20,.17,1),
        )
        self.restart_button.bind(on_release=lambda *_:self.restart_game())
        toolbar.add_widget(self.restart_button)
        root.add_widget(toolbar)

        self.board = GameBoard()
        root.add_widget(self.board)

        self.status_label = Label(
            text="Pilih unit lalu sentuh petak untuk menanam.",
            size_hint_y=None, height=dp(25), font_size="11sp",
            color=(.76,.87,.77,1),
        )
        root.add_widget(self.status_label)
        Clock.schedule_interval(self.refresh_hud, .15)
        self.choose_plant("pea")
        return root

    def choose_plant(self, kind):
        self.board.select_plant(kind)
        for key, button in self.buttons.items():
            button.opacity = 1.0 if key == kind else .72
        descriptions = {
            "pea": "Pea Shooter menembakkan proyektil hijau.",
            "ice": "Ice Plant memperlambat zombie.",
            "sun": "Sun Plant menghasilkan 25 energi berkala.",
            "wall": "Wall Plant kuat dan menahan zombie lebih lama.",
        }
        self.status_label.text = (
            descriptions[kind] + " Biaya: " + str(COSTS[kind]) + "."
        )

    def restart_game(self):
        self.board.reset()
        self.choose_plant(self.board.selected_plant)
        self.status_label.text = "Kalahkan 25 zombie untuk menang."

    def refresh_hud(self, _dt):
        self.sun_label.text = "SUN {}".format(self.board.sun)
        self.score_label.text = "KILLS {}/{}".format(
            self.board.kills, WIN_KILLS
        )

        if self.board.game_state == "won":
            self.status_label.text = (
                "YOU WIN! Semua zombie dikalahkan — tekan RESTART."
            )
        elif self.board.game_state == "lost":
            self.status_label.text = (
                "GAME OVER! Zombie menembus pertahanan — tekan RESTART."
            )
        elif self.board.sun < self.board.plant_cost(
            self.board.selected_plant
        ):
            self.status_label.text = (
                "Energi belum cukup. Tunggu energi atau kalahkan zombie."
            )


if __name__ == "__main__":
    PlantDefenseApp().run()

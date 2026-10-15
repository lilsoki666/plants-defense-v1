# -*- coding: utf-8 -*-
"""
Plant Defense
Offline tower-defense prototype for Android.
Engine: Python + Kivy.
No external Python packages beyond Kivy are required.
"""

import random
from dataclasses import dataclass

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget


GAME_TITLE = "PLANT DEFENSE"

LANES = 5
COLUMNS = 9
WIN_KILLS = 25

START_SUN = 175
SUN_INTERVAL = 7.0
ZOMBIE_INTERVAL_START = 5.0


@dataclass
class Plant:
    row: int
    col: int
    kind: str
    cooldown: float = 0.0
    hp: float = 100.0


@dataclass
class Zombie:
    row: int
    x: float
    hp: float
    speed: float
    attack_timer: float = 0.0


@dataclass
class Projectile:
    row: int
    x: float
    y: float
    damage: float
    speed: float
    kind: str = "pea"


class GameBoard(Widget):
    """Game world rendered directly with Kivy canvas instructions."""

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

        self.cell_w = 1.0
        self.cell_h = 1.0
        self.board_x = 0.0
        self.board_y = 0.0
        self.board_w = 1.0
        self.board_h = 1.0

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
        return 100 if kind == "pea" else 125

    def board_geometry(self):
        # Leave a small margin around the playing field.
        margin = dp(8)
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

        occupied = any(
            p.row == row and p.col == col for p in self.plants
        )

        if occupied:
            return True

        cost = self.plant_cost(self.selected_plant)
        if self.sun < cost:
            return True

        self.sun -= cost
        self.plants.append(
            Plant(row=row, col=col, kind=self.selected_plant)
        )
        self.redraw()
        return True

    def update(self, dt):
        if self.game_state != "playing":
            self.redraw()
            return

        dt = min(dt, 0.08)
        self.elapsed += dt
        self.spawn_timer -= dt
        self.sun_timer -= dt

        # Periodic sun energy.
        if self.sun_timer <= 0:
            self.sun += 25
            self.sun_timer = SUN_INTERVAL

        # Zombie waves gradually become more frequent.
        spawn_interval = max(1.7, ZOMBIE_INTERVAL_START - self.elapsed / 100)
        if self.spawn_timer <= 0:
            self.spawn_zombie()
            self.spawn_timer = spawn_interval * random.uniform(0.75, 1.25)

        # Plants fire when zombies are in the same lane.
        for plant in self.plants:
            plant.cooldown -= dt
            targets = [
                z for z in self.zombies
                if z.row == plant.row
                and z.x > self.plant_x(plant.col)
            ]

            if targets and plant.cooldown <= 0:
                px = self.plant_x(plant.col) + self.cell_w * 0.28
                py = self.lane_y(plant.row)

                if plant.kind == "ice":
                    self.projectiles.append(
                        Projectile(
                            row=plant.row,
                            x=px,
                            y=py,
                            damage=14,
                            speed=self.cell_w * 2.0,
                            kind="ice",
                        )
                    )
                    plant.cooldown = 1.6
                else:
                    self.projectiles.append(
                        Projectile(
                            row=plant.row,
                            x=px,
                            y=py,
                            damage=20,
                            speed=self.cell_w * 2.5,
                            kind="pea",
                        )
                    )
                    plant.cooldown = 1.25

        # Move projectiles and resolve hits.
        for shot in self.projectiles[:]:
            shot.x += shot.speed * dt
            hit = None

            for zombie in self.zombies:
                if zombie.row != shot.row:
                    continue

                if abs(zombie.x - shot.x) < self.cell_w * 0.22:
                    hit = zombie
                    break

            if hit is not None:
                hit.hp -= shot.damage
                if shot.kind == "ice":
                    hit.speed = min(hit.speed, self.cell_w * 0.12)

                if shot in self.projectiles:
                    self.projectiles.remove(shot)
            elif shot.x > self.board_x + self.board_w:
                if shot in self.projectiles:
                    self.projectiles.remove(shot)

        # Zombie movement and attacks.
        for zombie in self.zombies[:]:
            blocking_plant = None

            for plant in self.plants:
                if plant.row != zombie.row:
                    continue

                plant_center = self.plant_x(plant.col)
                if (
                    zombie.x <= plant_center + self.cell_w * 0.35
                    and zombie.x >= plant_center - self.cell_w * 0.35
                ):
                    blocking_plant = plant
                    break

            if blocking_plant is not None:
                zombie.attack_timer -= dt
                if zombie.attack_timer <= 0:
                    blocking_plant.hp -= 18
                    zombie.attack_timer = 0.8

                    if blocking_plant.hp <= 0:
                        if blocking_plant in self.plants:
                            self.plants.remove(blocking_plant)
            else:
                zombie.x -= zombie.speed * dt

            if zombie.hp <= 0:
                if zombie in self.zombies:
                    self.zombies.remove(zombie)
                    self.kills += 1
                    self.sun += 10

            # Reaching the left side means the lawn is breached.
            if zombie.x < self.board_x - self.cell_w * 0.25:
                self.game_state = "lost"

        if self.kills >= WIN_KILLS:
            self.game_state = "won"

        self.redraw()

    def spawn_zombie(self):
        row = random.randrange(LANES)
        hp = random.choice([75.0, 90.0, 110.0])
        speed = self.cell_w * random.uniform(0.075, 0.12)

        # Add a modest difficulty increase over time.
        hp += min(40, self.elapsed * 0.12)

        self.zombies.append(
            Zombie(
                row=row,
                x=self.board_x + self.board_w + self.cell_w * 0.35,
                hp=hp,
                speed=speed,
            )
        )

    def plant_x(self, col):
        return self.board_x + (col + 0.5) * self.cell_w

    def lane_y(self, row):
        return self.board_y + (LANES - row - 0.5) * self.cell_h

    def redraw(self, *_args):
        self.board_geometry()
        self.canvas.clear()

        with self.canvas:
            # Background.
            Color(0.055, 0.12, 0.12, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Lawn.
            Color(0.17, 0.39, 0.20, 1)
            RoundedRectangle(
                pos=(self.board_x, self.board_y),
                size=(self.board_w, self.board_h),
                radius=[dp(10)],
            )

            # Alternating lawn tiles.
            for row in range(LANES):
                for col in range(COLUMNS):
                    x = self.board_x + col * self.cell_w
                    y = self.board_y + row * self.cell_h

                    if (row + col) % 2 == 0:
                        Color(0.20, 0.44, 0.22, 1)
                    else:
                        Color(0.16, 0.37, 0.19, 1)

                    Rectangle(
                        pos=(x, y),
                        size=(self.cell_w, self.cell_h),
                    )

            # Grid lines.
            Color(0.75, 0.88, 0.67, 0.24)
            for col in range(COLUMNS + 1):
                x = self.board_x + col * self.cell_w
                Line(
                    points=[
                        x, self.board_y,
                        x, self.board_y + self.board_h,
                    ],
                    width=1,
                )

            for row in range(LANES + 1):
                y = self.board_y + row * self.cell_h
                Line(
                    points=[
                        self.board_x, y,
                        self.board_x + self.board_w, y,
                    ],
                    width=1,
                )

            # Plants.
            for plant in self.plants:
                cx = self.plant_x(plant.col)
                cy = self.lane_y(plant.row)
                radius = min(self.cell_w, self.cell_h) * 0.27

                if plant.kind == "ice":
                    Color(0.25, 0.78, 0.96, 1)
                else:
                    Color(0.31, 0.88, 0.34, 1)

                Ellipse(
                    pos=(cx - radius, cy - radius),
                    size=(radius * 2, radius * 2),
                )

                # Plant face.
                Color(0.04, 0.15, 0.09, 1)
                Ellipse(
                    pos=(cx - radius * 0.40, cy + radius * 0.10),
                    size=(radius * 0.18, radius * 0.18),
                )
                Ellipse(
                    pos=(cx + radius * 0.20, cy + radius * 0.10),
                    size=(radius * 0.18, radius * 0.18),
                )

                # Small leaf.
                Color(0.15, 0.65, 0.24, 1)
                Ellipse(
                    pos=(cx - radius * 0.90, cy - radius * 0.75),
                    size=(radius * 0.85, radius * 0.38),
                )

                # Plant health bar.
                bar_w = self.cell_w * 0.52
                bar_h = max(dp(2), self.cell_h * 0.045)
                bar_x = cx - bar_w / 2
                bar_y = cy - radius - bar_h * 2

                Color(0.12, 0.12, 0.12, 1)
                Rectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h))
                Color(0.20, 0.92, 0.35, 1)
                Rectangle(
                    pos=(bar_x, bar_y),
                    size=(bar_w * max(0, plant.hp / 100), bar_h),
                )

            # Zombies.
            for zombie in self.zombies:
                cy = self.lane_y(zombie.row)
                radius = min(self.cell_w, self.cell_h) * 0.27

                # Body.
                Color(0.40, 0.42, 0.34, 1)
                RoundedRectangle(
                    pos=(zombie.x - radius * 0.65, cy - radius * 1.15),
                    size=(radius * 1.3, radius * 1.7),
                    radius=[radius * 0.25],
                )

                # Head.
                Color(0.56, 0.61, 0.47, 1)
                Ellipse(
                    pos=(zombie.x - radius, cy + radius * 0.15),
                    size=(radius * 2, radius * 1.65),
                )

                # Eyes.
                Color(0.95, 0.95, 0.80, 1)
                Ellipse(
                    pos=(zombie.x - radius * 0.55, cy + radius * 0.72),
                    size=(radius * 0.42, radius * 0.35),
                )
                Ellipse(
                    pos=(zombie.x + radius * 0.12, cy + radius * 0.72),
                    size=(radius * 0.42, radius * 0.35),
                )

                Color(0.12, 0.12, 0.10, 1)
                Ellipse(
                    pos=(zombie.x - radius * 0.40, cy + radius * 0.82),
                    size=(radius * 0.15, radius * 0.15),
                )
                Ellipse(
                    pos=(zombie.x + radius * 0.24, cy + radius * 0.82),
                    size=(radius * 0.15, radius * 0.15),
                )

                # Zombie health bar.
                max_hp = 150.0
                bar_w = self.cell_w * 0.48
                bar_h = max(dp(2), self.cell_h * 0.045)
                bar_x = zombie.x - bar_w / 2
                bar_y = cy + radius * 1.85

                Color(0.12, 0.12, 0.12, 1)
                Rectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h))
                Color(0.90, 0.22, 0.18, 1)
                Rectangle(
                    pos=(bar_x, bar_y),
                    size=(bar_w * max(0, min(1, zombie.hp / max_hp)), bar_h),
                )

            # Projectiles.
            for shot in self.projectiles:
                if shot.kind == "ice":
                    Color(0.55, 0.91, 1.0, 1)
                else:
                    Color(0.70, 1.0, 0.28, 1)

                r = max(dp(4), self.cell_h * 0.075)
                Ellipse(
                    pos=(shot.x - r, shot.y - r),
                    size=(r * 2, r * 2),
                )

            # Top and bottom border accents.
            Color(0.67, 0.85, 0.51, 0.85)
            Line(
                rectangle=(
                    self.board_x,
                    self.board_y,
                    self.board_w,
                    self.board_h,
                ),
                width=1.3,
            )

            # End-state overlay.
            if self.game_state in ("won", "lost"):
                Color(0.02, 0.04, 0.04, 0.78)
                Rectangle(pos=self.pos, size=self.size)


class PlantDefenseApp(App):
    def build(self):
        self.title = GAME_TITLE

        # Landscape game layout.
        Window.clearcolor = (0.035, 0.075, 0.08, 1)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(6),
        )

        # Header.
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(42),
            spacing=dp(8),
        )

        self.title_label = Label(
            text="[b]PLANT DEFENSE[/b]",
            markup=True,
            font_size="20sp",
            color=(0.88, 1, 0.77, 1),
            halign="left",
        )
        self.sun_label = Label(
            text="☀ 175",
            font_size="17sp",
            color=(1.0, 0.83, 0.27, 1),
            size_hint_x=None,
            width=dp(90),
        )
        self.score_label = Label(
            text="ZOMBIE: 0/25",
            font_size="15sp",
            color=(0.93, 0.95, 0.91, 1),
            size_hint_x=None,
            width=dp(120),
        )

        header.add_widget(self.title_label)
        header.add_widget(self.sun_label)
        header.add_widget(self.score_label)
        root.add_widget(header)

        # Plant selection toolbar.
        toolbar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(6),
        )

        self.pea_button = Button(
            text="PEA SHOOTER  •  100",
            font_size="13sp",
            background_normal="",
            background_color=(0.16, 0.50, 0.24, 1),
        )
        self.ice_button = Button(
            text="ICE PLANT  •  125",
            font_size="13sp",
            background_normal="",
            background_color=(0.12, 0.42, 0.58, 1),
        )
        self.restart_button = Button(
            text="RESTART",
            size_hint_x=None,
            width=dp(100),
            font_size="13sp",
            background_normal="",
            background_color=(0.52, 0.23, 0.18, 1),
        )

        self.pea_button.bind(on_release=lambda *_: self.choose_plant("pea"))
        self.ice_button.bind(on_release=lambda *_: self.choose_plant("ice"))
        self.restart_button.bind(on_release=lambda *_: self.restart_game())

        toolbar.add_widget(self.pea_button)
        toolbar.add_widget(self.ice_button)
        toolbar.add_widget(self.restart_button)
        root.add_widget(toolbar)

        # Main playfield.
        self.board = GameBoard()
        root.add_widget(self.board)

        # Status footer.
        self.status_label = Label(
            text="Pilih tanaman, lalu sentuh petak rumput untuk menanam.",
            size_hint_y=None,
            height=dp(28),
            font_size="12sp",
            color=(0.78, 0.87, 0.79, 1),
        )
        root.add_widget(self.status_label)

        Clock.schedule_interval(self.refresh_hud, 0.15)
        self.choose_plant("pea")

        return root

    def choose_plant(self, kind):
        self.board.select_plant(kind)

        if kind == "pea":
            self.pea_button.background_color = (0.22, 0.68, 0.30, 1)
            self.ice_button.background_color = (0.12, 0.42, 0.58, 1)
            self.status_label.text = "Pea Shooter dipilih — biaya 100 energi."
        else:
            self.ice_button.background_color = (0.20, 0.62, 0.82, 1)
            self.pea_button.background_color = (0.16, 0.50, 0.24, 1)
            self.status_label.text = "Ice Plant dipilih — biaya 125 energi."

    def restart_game(self):
        self.board.reset()
        self.choose_plant(self.board.selected_plant)
        self.status_label.text = (
            "Permainan dimulai. Kalahkan 25 zombie untuk menang."
        )

    def refresh_hud(self, _dt):
        self.sun_label.text = "☀ {}".format(self.board.sun)
        self.score_label.text = "ZOMBIE: {}/{}".format(
            self.board.kills, WIN_KILLS
        )

        if self.board.game_state == "won":
            self.status_label.text = (
                "MENANG! Semua jalur aman. Tekan RESTART untuk bermain lagi."
            )
        elif self.board.game_state == "lost":
            self.status_label.text = (
                "KALAH! Zombie menembus pertahanan. Tekan RESTART."
            )
        elif self.board.sun < self.board.plant_cost(
            self.board.selected_plant
        ):
            self.status_label.text = (
                "Energi belum cukup. Tunggu matahari atau kalahkan zombie."
            )


if __name__ == "__main__":
    PlantDefenseApp().run()

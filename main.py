
# -*- coding: utf-8 -*-
"""Plant Defense: original offline pixel-art tower defense for Android."""
import json, os, random, math
from dataclasses import dataclass

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, Line, Triangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

TITLE = "PLANT DEFENSE"
LANES, COLS = 5, 9
SAVE_FILE = "plant_defense_save.json"

PLANTS = {
    "sprout": {"name": "Sprout Blaster", "cost": 100, "hp": 100, "cool": 1.05, "damage": 20, "color": (.25,.82,.28,1), "desc": "Penembak standar"},
    "frost": {"name": "Frostbud", "cost": 125, "hp": 95, "cool": 1.55, "damage": 14, "color": (.35,.82,.98,1), "desc": "Memperlambat zombie"},
    "bloom": {"name": "Sun Bloom", "cost": 50, "hp": 85, "cool": 7.0, "damage": 0, "color": (1,.75,.18,1), "desc": "Menghasilkan energi"},
    "bark": {"name": "Bark Guard", "cost": 75, "hp": 330, "cool": 0, "damage": 0, "color": (.62,.39,.22,1), "desc": "Pertahanan kokoh"},
    "burst": {"name": "Burst Berry", "cost": 150, "hp": 75, "cool": 99, "damage": 90, "color": (1,.35,.23,1), "desc": "Ledakan area sekali pakai"},
    "twin": {"name": "Twin Sprout", "cost": 200, "hp": 105, "cool": 1.45, "damage": 14, "color": (.38,.88,.3,1), "desc": "Menembak dua proyektil"},
    "snare": {"name": "Root Snare", "cost": 100, "hp": 90, "cool": 99, "damage": 8, "color": (.55,.66,.28,1), "desc": "Perangkap satu kali"},
}

ZOMBIES = {
    "walker": {"hp": 100, "speed": .080, "damage": 18, "color": (.53,.63,.43,1), "reward": 15},
    "runner": {"hp": 70, "speed": .135, "damage": 13, "color": (.68,.72,.43,1), "reward": 18},
    "brute": {"hp": 210, "speed": .052, "damage": 30, "color": (.45,.50,.37,1), "reward": 25},
    "helmet": {"hp": 155, "speed": .067, "damage": 20, "color": (.60,.65,.49,1), "reward": 22},
}


@dataclass
class Plant:
    row: int
    col: int
    kind: str
    hp: float
    cooldown: float = 0.
    anim: float = 0.


@dataclass
class Zombie:
    row: int
    x: float
    kind: str
    hp: float
    max_hp: float
    speed: float
    attack: float = 0.
    anim: float = 0.
    slow: float = 0.


@dataclass
class Shot:
    row: int
    x: float
    y: float
    damage: float
    speed: float
    kind: str = "sprout"


@dataclass
class SunDrop:
    x: float
    y: float
    value: int = 25
    ttl: float = 9.
    phase: float = 0.


class PixelBoard(Widget):
    """Game simulation and pixel-art arena."""

    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.plants, self.zombies = [], []
        self.shots, self.suns = [], []
        self.sun = 175
        self.kills = 0
        self.elapsed = 0.
        self.spawn = 2.2
        self.sun_clock = 4.
        self.wave = 1
        self.state = "playing"
        self.mode = "adventure"
        self.level = 1
        self.goal = 21
        self.paused = False
        self.selected = "sprout"
        self.shovel = False
        self.cellw = self.cellh = 1.
        self.bx = self.by = 0.
        self.bw = self.bh = 1.
        self.bind(pos=self.draw, size=self.draw)
        Clock.schedule_interval(self.tick, 1 / 30.)

    def start(self, mode="adventure", level=1):
        self.plants, self.zombies = [], []
        self.shots, self.suns = [], []
        self.sun = 175
        self.kills = 0
        self.elapsed = 0.
        self.spawn = 2.
        self.sun_clock = 4.
        self.wave = 1
        self.state = "playing"
        self.paused = False
        self.mode = mode
        self.level = level
        self.goal = (18 + level * 3) if mode == "adventure" else (
            10**9 if mode == "survival" else 12
        )
        self.selected = "sprout"
        self.shovel = False
        self.draw()

    def geom(self):
        pad = dp(5)
        self.bx, self.by = self.x + pad, self.y + pad
        self.bw = max(1, self.width - 2 * pad)
        self.bh = max(1, self.height - 2 * pad)
        self.cellw = self.bw / COLS
        self.cellh = self.bh / LANES

    def px(self, c):
        return self.bx + (c + .5) * self.cellw

    def py(self, r):
        return self.by + (LANES - r - .5) * self.cellh

    def touch_sun(self, x, y):
        for s in self.suns[:]:
            if (s.x - x)**2 + (s.y - y)**2 < dp(40)**2:
                self.sun += s.value
                self.suns.remove(s)
                return True
        return False

    def on_touch_down(self, t):
        if self.state != "playing" or self.paused:
            return True
        if not self.collide_point(*t.pos):
            return super().on_touch_down(t)

        self.geom()
        if self.touch_sun(t.x, t.y):
            self.draw()
            self.app.refresh()
            return True

        bx, by = t.x - self.bx, t.y - self.by
        if bx < 0 or by < 0 or bx >= self.bw or by >= self.bh:
            return True

        c = int(bx / self.cellw)
        r = LANES - 1 - int(by / self.cellh)
        existing = next((p for p in self.plants if p.row == r and p.col == c), None)

        if self.shovel:
            if existing:
                self.plants.remove(existing)
            self.shovel = False
            self.app.set_status("Sekop digunakan.")
            self.draw()
            self.app.refresh()
            return True

        if existing:
            return True

        data = PLANTS[self.selected]
        if self.sun < data["cost"]:
            self.app.set_status("Energi belum cukup untuk unit ini.")
            return True

        self.sun -= data["cost"]
        self.plants.append(Plant(r, c, self.selected, data["hp"]))
        self.app.set_status(data["name"] + " ditempatkan.")
        self.draw()
        self.app.refresh()
        return True

    def spawn_zombie(self):
        row = random.randrange(LANES)
        if self.elapsed < 20:
            kind = "walker"
        else:
            roll = random.random()
            kind = (
                "runner" if roll < .22 else
                "brute" if roll < .40 else
                "helmet" if roll < .60 else "walker"
            )

        d = ZOMBIES[kind]
        scale = 1 + max(0, self.level - 1) * .10 + self.elapsed * .0015
        hp = d["hp"] * scale
        self.zombies.append(Zombie(
            row, self.bx + self.bw + self.cellw * .4,
            kind, hp, hp, self.cellw * d["speed"]
        ))

    def tick(self, dt):
        if self.state != "playing" or self.paused:
            self.draw()
            return

        dt = min(dt, .05)
        self.elapsed += dt
        self.spawn -= dt
        self.sun_clock -= dt
        interval = max(1.35, 5.2 - self.elapsed * .012 - self.level * .05)

        if self.spawn <= 0:
            self.spawn_zombie()
            self.spawn = interval * random.uniform(.78, 1.18)
            if self.kills and self.kills % 8 == 0:
                self.wave += 1

        if self.sun_clock <= 0:
            self.suns.append(SunDrop(
                random.uniform(self.bx + self.cellw, self.bx + self.bw - self.cellw),
                self.by + self.bh * .72
            ))
            self.sun_clock = random.uniform(7, 10)

        for s in self.suns[:]:
            s.ttl -= dt
            s.phase += dt
            if s.ttl <= 0:
                self.suns.remove(s)

        for p in self.plants[:]:
            p.anim += dt
            p.cooldown -= dt

            if p.kind == "bloom":
                if p.cooldown <= 0:
                    self.suns.append(SunDrop(self.px(p.col), self.py(p.row) + self.cellh * .28))
                    p.cooldown = PLANTS[p.kind]["cool"]
                continue

            if p.kind == "bark":
                continue

            if p.kind == "burst":
                target = next((
                    z for z in self.zombies
                    if z.row == p.row and abs(z.x - self.px(p.col)) < self.cellw * 1.25
                ), None)
                if target:
                    for z in self.zombies:
                        if abs(z.row - p.row) <= 1 and abs(z.x - self.px(p.col)) < self.cellw * 1.6:
                            z.hp -= PLANTS["burst"]["damage"]
                    self.plants.remove(p)
                    continue

            if p.kind == "snare":
                target = next((
                    z for z in self.zombies
                    if z.row == p.row and abs(z.x - self.px(p.col)) < self.cellw * .65
                ), None)
                if target:
                    target.hp -= 80
                    target.slow = 4.
                    self.plants.remove(p)
                    continue

            targets = [z for z in self.zombies if z.row == p.row and z.x > self.px(p.col)]
            if targets and p.cooldown <= 0:
                y = self.py(p.row) + self.cellh * .12
                x = self.px(p.col) + self.cellw * .2
                if p.kind == "twin":
                    self.shots.append(Shot(p.row, x, y, 14, self.cellw * 2.6, "twin"))
                    self.shots.append(Shot(p.row, x, y + self.cellh * .08, 14, self.cellw * 2.6, "twin"))
                else:
                    self.shots.append(Shot(
                        p.row, x, y, PLANTS[p.kind]["damage"],
                        self.cellw * (2.1 if p.kind == "frost" else 2.7), p.kind
                    ))
                p.cooldown = PLANTS[p.kind]["cool"]

        for sh in self.shots[:]:
            sh.x += sh.speed * dt
            hit = next((
                z for z in self.zombies
                if z.row == sh.row and abs(z.x - sh.x) < self.cellw * .22
            ), None)
            if hit:
                hit.hp -= sh.damage
                if sh.kind == "frost":
                    hit.slow = max(hit.slow, 3.)
                self.shots.remove(sh)
            elif sh.x > self.bx + self.bw + self.cellw:
                self.shots.remove(sh)

        for z in self.zombies[:]:
            z.anim += dt
            z.slow = max(0, z.slow - dt)
            block = next((
                p for p in self.plants
                if p.row == z.row and abs(z.x - self.px(p.col)) < self.cellw * .34
            ), None)

            if block:
                z.attack -= dt
                if z.attack <= 0:
                    block.hp -= ZOMBIES[z.kind]["damage"]
                    z.attack = .8
                    if block.hp <= 0 and block in self.plants:
                        self.plants.remove(block)
            else:
                z.x -= z.speed * (.48 if z.slow > 0 else 1) * dt

            if z.hp <= 0:
                self.zombies.remove(z)
                self.kills += 1
                self.suns.append(SunDrop(z.x, self.py(z.row), ZOMBIES[z.kind]["reward"]))
                continue

            if z.x < self.bx - self.cellw * .2:
                self.state = "lost"

        if self.mode != "survival" and self.kills >= self.goal and not self.zombies:
            self.state = "won"
            self.app.on_level_won(self.mode, self.level)

        self.draw()
        self.app.refresh()

    def diamond(self, cx, cy, hw, hh, base):
        Color(*base)
        Triangle(points=[cx, cy+hh, cx-hw, cy, cx, cy-hh])
        Color(min(1,base[0]*1.12), min(1,base[1]*1.12), min(1,base[2]*1.12), 1)
        Triangle(points=[cx, cy+hh, cx+hw, cy, cx, cy-hh])
        Color(.38, .58, .30, .65)
        Line(points=[cx,cy+hh,cx+hw,cy,cx,cy-hh,cx-hw,cy,cx,cy+hh],width=.65)

    def draw_plant(self, p, cx, cy, s):
        bob = abs(math.sin(p.anim * 4)) * s * .025
        k = p.kind
        Color(.04,.08,.03,.35)
        Ellipse(pos=(cx-s*.31,cy-s*.28),size=(s*.62,s*.16))

        if k == "bark":
            Color(.36,.22,.12,1)
            Rectangle(pos=(cx-s*.25,cy-s*.28),size=(s*.5,s*.58))
            Color(.62,.42,.23,1)
            Rectangle(pos=(cx-s*.19,cy+s*.01),size=(s*.38,s*.20))
            Color(.13,.1,.07,1)
            Rectangle(pos=(cx-s*.13,cy-s*.02),size=(s*.06,s*.06))
            Rectangle(pos=(cx+s*.06,cy-s*.02),size=(s*.06,s*.06))
            return

        if k == "bloom":
            for a in range(8):
                ang = a * math.pi / 4
                Color(1,.68,.12,1)
                Rectangle(pos=(cx+math.cos(ang)*s*.15-s*.07,
                               cy+s*.27+bob+math.sin(ang)*s*.15-s*.07),
                          size=(s*.14,s*.14))
            Color(1,.88,.25,1)
            Rectangle(pos=(cx-s*.12,cy+s*.20+bob),size=(s*.24,s*.24))
            Color(.18,.62,.22,1)
            Rectangle(pos=(cx-s*.055,cy-s*.25),size=(s*.11,s*.49))
            return

        Color(.12,.5,.19,1)
        Rectangle(pos=(cx-s*.055,cy-s*.27),size=(s*.11,s*.35))
        Rectangle(pos=(cx-s*.29,cy-s*.15),size=(s*.23,s*.1))
        Rectangle(pos=(cx+s*.06,cy-s*.10),size=(s*.22,s*.1))
        col = PLANTS[k]["color"]
        Color(*col)
        Rectangle(pos=(cx-s*.23,cy+s*.02+bob),size=(s*.46,s*.39))
        Color(min(1,col[0]+.22),min(1,col[1]+.18),min(1,col[2]+.1),1)
        Rectangle(pos=(cx-s*.15,cy+s*.22+bob),size=(s*.15,s*.12))
        Color(.06,.15,.08,1)
        Rectangle(pos=(cx-s*.11,cy+s*.14+bob),size=(s*.055,s*.07))
        Rectangle(pos=(cx+s*.065,cy+s*.14+bob),size=(s*.055,s*.07))
        if k in ("sprout","twin"):
            Color(.13,.48,.16,1)
            Rectangle(pos=(cx+s*.15,cy+s*.10+bob),size=(s*.2,s*.14))
        if k == "burst":
            Color(1,.86,.32,1)
            Rectangle(pos=(cx-s*.07,cy+s*.06+bob),size=(s*.14,s*.12))
        if k == "snare":
            Color(.36,.44,.17,1)
            Rectangle(pos=(cx-s*.24,cy-s*.04),size=(s*.48,s*.10))

    def draw_zombie(self, z, cx, cy, s):
        walk = math.sin(z.anim * 7) * s * .035
        col = ZOMBIES[z.kind]["color"]
        Color(.03,.04,.025,.35)
        Ellipse(pos=(cx-s*.31,cy-s*.28),size=(s*.62,s*.14))
        Color(.25,.28,.23,1)
        Rectangle(pos=(cx-s*.18+walk,cy-s*.27),size=(s*.14,s*.27))
        Rectangle(pos=(cx+s*.04-walk,cy-s*.27),size=(s*.14,s*.27))
        Color(*col)
        Rectangle(pos=(cx-s*.22,cy-s*.02),size=(s*.44,s*.43))
        Rectangle(pos=(cx-s*.19,cy+s*.22),size=(s*.38,s*.29))
        Color(.22,.27,.20,1)
        Rectangle(pos=(cx-s*.30,cy+s*.02),size=(s*.11,s*.24))
        Rectangle(pos=(cx+s*.19,cy+s*.02),size=(s*.11,s*.24))
        Color(.91,.91,.65,1)
        Rectangle(pos=(cx-s*.12,cy+s*.34),size=(s*.09,s*.08))
        Rectangle(pos=(cx+s*.04,cy+s*.34),size=(s*.09,s*.08))
        Color(.07,.08,.05,1)
        Rectangle(pos=(cx-s*.09,cy+s*.36),size=(s*.04,s*.04))
        Rectangle(pos=(cx+s*.07,cy+s*.36),size=(s*.04,s*.04))
        if z.kind == "helmet":
            Color(.58,.65,.67,1)
            Rectangle(pos=(cx-s*.22,cy+s*.45),size=(s*.44,s*.12))
            Rectangle(pos=(cx-s*.18,cy+s*.55),size=(s*.36,s*.06))
        if z.kind == "brute":
            Color(.25,.28,.21,1)
            Rectangle(pos=(cx-s*.28,cy+s*.02),size=(s*.56,s*.22))
        bw, bh = s*.64, max(dp(2),s*.04)
        Color(.06,.07,.06,1)
        Rectangle(pos=(cx-bw/2,cy+s*.62),size=(bw,bh))
        Color(.85,.19,.14,1)
        Rectangle(pos=(cx-bw/2,cy+s*.62),size=(bw*max(0,z.hp/z.max_hp),bh))

    def draw(self, *_):
        self.geom()
        self.canvas.clear()
        with self.canvas:
            Color(.025,.06,.065,1)
            Rectangle(pos=self.pos,size=self.size)
            Color(.07,.17,.12,1)
            Rectangle(pos=(self.bx,self.by),size=(self.bw,self.bh))
            for r in range(LANES):
                for c in range(COLS):
                    cx=self.bx+(c+.5)*self.cellw
                    cy=self.by+(r+.5)*self.cellh
                    base=(.13,.34,.18,1) if (r+c)%2 else (.17,.41,.22,1)
                    self.diamond(cx,cy,self.cellw*.51,self.cellh*.50,base)
            for p in self.plants:
                self.draw_plant(p,self.px(p.col),self.py(p.row),
                                min(self.cellw*.74,self.cellh*.88))
            for sh in self.shots:
                rad=max(dp(3),self.cellh*.065)
                Color((.48,.9,1,1) if sh.kind=="frost" else (.65,1,.25,1))
                Rectangle(pos=(sh.x-rad,sh.y-rad),size=(rad*2,rad*2))
            for z in self.zombies:
                self.draw_zombie(z,z.x,self.py(z.row),
                                 min(self.cellw*.72,self.cellh*.84))
            for s in self.suns:
                pulse=abs(math.sin(s.phase*3))*dp(2)
                Color(1,.76,.18,1)
                Ellipse(pos=(s.x-dp(10)-pulse,s.y-dp(10)-pulse),
                        size=(dp(20)+pulse*2,dp(20)+pulse*2))
                Color(1,.94,.53,1)
                Ellipse(pos=(s.x-dp(4),s.y-dp(4)),size=(dp(8),dp(8)))
            Color(.64,.85,.48,.85)
            Line(rectangle=(self.bx,self.by,self.bw,self.bh),width=1.1)
            if self.paused or self.state in ("won","lost"):
                Color(.015,.025,.02,.72)
                Rectangle(pos=self.pos,size=self.size)


class PlantDefenseApp(App):
    def build(self):
        self.title=TITLE
        Window.clearcolor=(.025,.06,.065,1)
        self.save_path=os.path.join(self.user_data_dir,SAVE_FILE)
        self.progress={"level":1,"best_survival":0,"sound":True}
        self.load_progress()
        self.sm=ScreenManager(transition=FadeTransition(duration=.15))
        self.make_menu()
        self.make_game()
        self.make_codex()
        self.show_menu()
        return self.sm

    def load_progress(self):
        try:
            with open(self.save_path,"r",encoding="utf-8") as f:
                self.progress.update(json.load(f))
        except Exception:
            pass

    def save_progress(self):
        try:
            os.makedirs(os.path.dirname(self.save_path),exist_ok=True)
            with open(self.save_path,"w",encoding="utf-8") as f:
                json.dump(self.progress,f)
        except Exception:
            pass

    def button(self,text,cb,color=(.15,.37,.24,1),height=dp(46)):
        b=Button(text=text,size_hint_y=None,height=height,font_size="15sp",
                 bold=True,background_normal="",background_color=color,
                 color=(.94,1,.88,1))
        b.bind(on_release=lambda *_:cb())
        return b

    def make_menu(self):
        s=Screen(name="menu")
        root=BoxLayout(orientation="vertical",padding=dp(18),spacing=dp(10))
        root.add_widget(Widget(size_hint_y=.15))
        root.add_widget(Label(text="[b]PLANT DEFENSE[/b]",markup=True,
                              font_size="32sp",color=(.72,1,.57,1),
                              size_hint_y=None,height=dp(55)))
        root.add_widget(Label(text="PIXEL GARDEN • OFFLINE STRATEGY",
                              font_size="12sp",color=(.65,.82,.68,1),
                              size_hint_y=None,height=dp(26)))
        root.add_widget(Widget(size_hint_y=.06))
        root.add_widget(self.button("PETUALANGAN",self.show_levels,(.16,.45,.23,1)))
        root.add_widget(self.button("SURVIVAL",lambda:self.start_game("survival",1),(.14,.37,.48,1)))
        root.add_widget(self.button("TANTANGAN",lambda:self.start_game("challenge",1),(.49,.33,.13,1)))
        root.add_widget(self.button("ENSIKLOPEDIA UNIT",self.show_codex,(.29,.30,.20,1)))
        root.add_widget(self.button("PENGATURAN",self.show_settings,(.25,.28,.27,1)))
        root.add_widget(Label(text="Versi 0.3 • Dunia taman orisinal",
                              font_size="10sp",color=(.45,.60,.49,1),
                              size_hint_y=None,height=dp(24)))
        root.add_widget(Widget(size_hint_y=.12))
        s.add_widget(root)
        self.sm.add_widget(s)

    def make_game(self):
        self.game_screen=Screen(name="game")
        root=BoxLayout(orientation="vertical",padding=dp(5),spacing=dp(4))
        header=BoxLayout(size_hint_y=None,height=dp(34),spacing=dp(5))
        self.hud=Label(text="SUN 175",font_size="14sp",color=(1,.82,.29,1))
        self.levelhud=Label(text="LEVEL 1 • 0/21",font_size="13sp",color=(.84,.97,.81,1))
        header.add_widget(self.hud)
        header.add_widget(self.levelhud)
        header.add_widget(self.button("Ⅱ",self.pause_game,(.29,.34,.26,1),dp(34)))
        header.add_widget(self.button("MENU",self.show_menu,(.42,.22,.18,1),dp(34)))
        root.add_widget(header)

        self.cards=GridLayout(cols=7,spacing=dp(3),size_hint_y=None,height=dp(58))
        self.card_buttons={}
        for k,d in PLANTS.items():
            b=Button(text="{}\n{}".format(d["name"].split()[0],d["cost"]),
                     font_size="10sp",background_normal="",background_color=d["color"])
            b.bind(on_release=lambda _b,key=k:self.select_plant(key))
            self.cards.add_widget(b)
            self.card_buttons[k]=b
        root.add_widget(self.cards)

        tools=BoxLayout(size_hint_y=None,height=dp(31),spacing=dp(4))
        tools.add_widget(self.button("SEKOP",self.toggle_shovel,(.36,.27,.18,1),dp(31)))
        self.status=Label(text="Pilih kartu lalu sentuh petak. Sentuh matahari untuk mengumpulkan energi.",
                          font_size="10sp",color=(.75,.88,.77,1))
        tools.add_widget(self.status)
        root.add_widget(tools)
        self.board=PixelBoard(self,size_hint_y=1)
        root.add_widget(self.board)
        self.overlay=Label(text="",markup=True,font_size="22sp",
                           color=(.88,1,.71,1),size_hint_y=None,height=dp(28))
        root.add_widget(self.overlay)
        self.game_screen.add_widget(root)
        self.sm.add_widget(self.game_screen)

    def make_codex(self):
        s=Screen(name="codex")
        root=BoxLayout(orientation="vertical",padding=dp(12),spacing=dp(7))
        root.add_widget(Label(text="[b]ENSIKLOPEDIA TAMAN[/b]",markup=True,
                              font_size="22sp",size_hint_y=None,height=dp(42)))
        for k,d in PLANTS.items():
            root.add_widget(Label(text="[b]{} — {} energi[/b] | {}".format(
                d["name"],d["cost"],d["desc"]),markup=True,font_size="12sp",
                halign="left",valign="middle"))
        root.add_widget(Label(text="Zombie: Walker (normal), Runner (cepat), Brute (kuat), Helmet (berzirah).",
                              font_size="12sp",halign="left"))
        root.add_widget(self.button("KEMBALI",self.show_menu))
        s.add_widget(root)
        self.sm.add_widget(s)

    def show_menu(self):
        if not self.sm.has_screen("menu"):
            return
        screen=self.sm.get_screen("menu")
        root=screen.children[0] if screen.children else None
        if root is not None:
            root.clear_widgets()
            root.add_widget(Widget(size_hint_y=.12))
            root.add_widget(Label(text="[b]PLANT DEFENSE[/b]",markup=True,
                                  font_size="32sp",color=(.72,1,.57,1),
                                  size_hint_y=None,height=dp(55)))
            root.add_widget(Label(text="PIXEL GARDEN • OFFLINE STRATEGY",
                                  font_size="12sp",color=(.65,.82,.68,1),
                                  size_hint_y=None,height=dp(26)))
            root.add_widget(Widget(size_hint_y=.05))
            root.add_widget(self.button("PETUALANGAN",self.show_levels,(.16,.45,.23,1)))
            root.add_widget(self.button("SURVIVAL",lambda:self.start_game("survival",1),(.14,.37,.48,1)))
            root.add_widget(self.button("TANTANGAN",lambda:self.start_game("challenge",1),(.49,.33,.13,1)))
            root.add_widget(self.button("ENSIKLOPEDIA UNIT",self.show_codex,(.29,.30,.20,1)))
            root.add_widget(self.button("PENGATURAN",self.show_settings,(.25,.28,.27,1)))
            root.add_widget(Label(text="Versi 0.3 • Dunia taman orisinal",
                                  font_size="10sp",color=(.45,.60,.49,1),
                                  size_hint_y=None,height=dp(24)))
            root.add_widget(Widget(size_hint_y=.08))
        self.sm.current="menu"

    def show_levels(self):
        screen=self.sm.get_screen("menu")
        root=screen.children[0]
        root.clear_widgets()
        root.add_widget(Label(text="[b]PILIH TAHAP[/b]",markup=True,
                              font_size="26sp",size_hint_y=None,height=dp(55)))
        unlocked=int(self.progress.get("level",1))
        for lv in range(1,7):
            locked=lv>unlocked
            b=self.button("LEVEL {} {}".format(lv,"• TERKUNCI" if locked else "• TERBUKA"),
                          lambda n=lv:self.start_game("adventure",n),
                          (.22,.30,.20,1) if locked else (.15,.43,.24,1))
            b.disabled=locked
            root.add_widget(b)
        root.add_widget(self.button("KEMBALI",self.show_menu,(.35,.25,.20,1)))
        self.sm.current="menu"

    def show_codex(self):
        self.sm.current="codex"

    def show_settings(self):
        screen=self.sm.get_screen("menu")
        root=screen.children[0]
        root.clear_widgets()
        root.add_widget(Label(text="[b]PENGATURAN[/b]",markup=True,
                              font_size="25sp",size_hint_y=None,height=dp(55)))
        root.add_widget(Label(text="Plant Defense dimainkan offline. Progres tersimpan otomatis di perangkat.",
                              font_size="14sp"))
        root.add_widget(self.button("HAPUS PROGRES",self.clear_progress,(.48,.20,.17,1)))
        root.add_widget(self.button("KEMBALI",self.show_menu))
        self.sm.current="menu"

    def clear_progress(self):
        self.progress={"level":1,"best_survival":0,"sound":True}
        self.save_progress()
        self.show_menu()

    def start_game(self,mode,level):
        self.board.start(mode,level)
        self.overlay.text=""
        self.select_plant("sprout")
        self.sm.current="game"
        descriptions={
            "adventure":"Petualangan • selesaikan gelombang untuk membuka tahap berikutnya.",
            "survival":"Survival • bertahan selama mungkin.",
            "challenge":"Tantangan • kalahkan 12 zombie dengan sumber daya terbatas."
        }
        self.set_status(descriptions.get(mode,"Mulai bertahan!"))

    def select_plant(self,k):
        self.board.selected=k
        self.board.shovel=False
        for key,b in self.card_buttons.items():
            b.opacity=1 if key==k else .72
        self.set_status("{} • biaya {} energi".format(PLANTS[k]["name"],PLANTS[k]["cost"]))

    def toggle_shovel(self):
        self.board.shovel=not self.board.shovel
        self.set_status("Pilih tanaman yang akan dihapus." if self.board.shovel else "Sekop dibatalkan.")

    def pause_game(self):
        self.board.paused=not self.board.paused
        self.overlay.text="[b]PAUSED[/b]" if self.board.paused else ""
        self.set_status("Sentuh tombol jeda untuk melanjutkan." if self.board.paused else "Permainan dilanjutkan.")

    def set_status(self,msg):
        if hasattr(self,"status"):
            self.status.text=msg

    def refresh(self):
        if not hasattr(self,"board"):
            return
        self.hud.text="SUN {}".format(self.board.sun)
        goal="∞" if self.board.mode=="survival" else str(self.board.goal)
        self.levelhud.text="{} • KILLS {}/{} • WAVE {}".format(
            self.board.mode.upper(),self.board.kills,goal,self.board.wave)
        for k,b in self.card_buttons.items():
            b.disabled=self.board.sun<PLANTS[k]["cost"]
            b.background_color=(*PLANTS[k]["color"][:3],1 if not b.disabled else .38)
        if self.board.state=="won":
            self.overlay.text="[b]LEVEL CLEAR![/b]"
        elif self.board.state=="lost":
            self.overlay.text="[b]GARDEN OVERRUN[/b] • MENU lalu coba lagi"
        elif not self.board.paused:
            self.overlay.text=""

    def on_level_won(self,mode,level):
        if mode=="adventure":
            self.progress["level"]=max(
                int(self.progress.get("level",1)),min(6,level+1))
            self.save_progress()
        elif mode=="survival":
            self.progress["best_survival"]=max(
                int(self.progress.get("best_survival",0)),self.board.kills)
            self.save_progress()
        self.set_status("Progres tersimpan. Kembali ke menu untuk memilih tahap berikutnya.")


if __name__ == "__main__":
    PlantDefenseApp().run()

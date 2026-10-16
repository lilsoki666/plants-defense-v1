import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line

# ==========================================
# 1. MANAGEMENT STATE: UTILS & DATA TEMPLATE
# ==========================================

# Template Jenis Tanaman Nusantara
DAFTAR_TANAMAN = {
    "melati":  {"nama": "Melati Suci", "harga": 50,  "darah": 200,  "tipe": "produsen", "warna": (1, 1, 1, 1)},      # Penghasil Surya
    "sawit":   {"nama": "Kelapa Sawit", "harga": 100, "darah": 300,  "tipe": "penembak", "warna": (0.1, 0.5, 0.1, 1)}, # Artileri Parabola
    "bambu":   {"nama": "Bambu Runcing", "harga": 50,  "darah": 3000, "tipe": "bertahan", "warna": (0.6, 0.8, 0.2, 1)}, # Tembok Alami
    "semar":   {"nama": "Kantong Semar", "harga": 150, "darah": 400,  "tipe": "pemakan",  "warna": (0.5, 0, 0.5, 1)}   # Instant Melee Killer
}

# Template Jenis Zombie Legend Indonesia
DAFTAR_ZOMBIE = {
    "pocong":   {"nama": "Pocong Meloncat", "darah": 200, "kecepatan": -1.2, "armor": 0, "warna": (0.8, 0.8, 0.8, 1)},
    "kuntilanak":{"nama": "Kunti Terbang",   "darah": 150, "kecepatan": -2.0, "armor": 0, "warna": (0.9, 0.5, 0.9, 1)}, # Cepat
    "genderuwo":{"nama": "Genderuwo Gede",   "darah": 800, "kecepatan": -0.6, "armor": 5, "warna": (0.2, 0.2, 0.2, 1)}  # Tanker/Tebal
}

# ==========================================
# 2. SISTEM LAYAR & MENU UTAMA (UI/UX)
# ==========================================
class MenuUtamaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Background Menu Utama sementara memakai teks besar
        self.add_widget(Label(text="PLANTS DEFENSE:\nNUSANTARA EDITION", font_size='40sp', pos_hint={'center_x': 0.5, 'center_y': 0.7}))
        
        # Tombol Mode Survival
        btn_survival = Button(text="SURVIVAL MODE", size_hint=(0.3, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.45})
        btn_survival.bind(on_press=self.pilih_survival)
        self.add_widget(btn_survival)
        
        # Tombol Mode Bonus / Minigames
        btn_bonus = Button(text="BONUS MINIGAMES", size_hint=(0.3, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.3})
        btn_bonus.bind(on_press=self.pilih_bonus)
        self.add_widget(btn_bonus)

    def pilih_survival(self, instance):
        self.manager.current = 'game_play'
        self.manager.get_screen('game_play').mulai_level("survival")

    def pilih_bonus(self, instance):
        self.manager.current = 'game_play'
        self.manager.get_screen('game_play').mulai_level("bonus")

# ==========================================
# 3. ENTITAS GAMEPLAY (PLANTS, ZOMBIES, PROJECTILES)
# ==========================================
class TanamanInstance(Widget):
    def __init__(self, data, baris, kolom, **kwargs):
        super().__init__(**kwargs)
        self.nama = data["nama"]
        self.darah = data["darah"]
        self.tipe = data["tipe"]
        self.baris = baris
        self.kolom = kolom
        self.waktu_aksi = 0
        
        with self.canvas:
            Color(*data["warna"])
            self.rect = Rectangle(pos=self.pos, size=(55, 65))
        self.bind(pos=self.update_rect)

    def update_rect(self, *args): self.rect.pos = self.pos

class ZombieInstance(Widget):
    def __init__(self, data, baris, **kwargs):
        super().__init__(**kwargs)
        self.nama = data["nama"]
        self.darah = data["darah"]
        self.kecepatan = data["kecepatan"]
        self.baris = baris
        
        with self.canvas:
            Color(*data["warna"])
            self.rect = Rectangle(pos=self.pos, size=(45, 75))
        self.bind(pos=self.update_rect)

    def update_rect(self, *args): self.rect.pos = self.pos
    def berjalan(self): self.x += self.kecepatan

class PeluruSawitParabola(Widget):
    def __init__(self, target_baris, **kwargs):
        super().__init__(**kwargs)
        self.kecepatan_x = 6
        self.kecepatan_y = 12  # Melesat ke atas
        self.gravitasi = 0.5
        self.baris = target_baris
        with self.canvas:
            Color(1, 0.4, 0, 1) # Oranye Sawit
            self.rect = Rectangle(pos=self.pos, size=(16, 16))
    def bergerak(self):
        self.x += self.kecepatan_x
        self.kecepatan_y -= self.gravitasi
        self.y += self.kecepatan_y
        self.rect.pos = self.pos

class EnergiMatahari(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 0.9, 0, 1) # Kuning Cerah Surya
            self.rect = Rectangle(pos=self.pos, size=(30, 30))
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Jika diklik, tambah poin energi pemain
            self.parent.poin_energi += 25
            self.parent.remove_widget(self)
            return True
        return super().on_touch_down(touch)

# ==========================================
# 4. ARENA UTAMA GAMEPLAY (5 BARIS x 9 KOLOM GRID)
# ==========================================
class GameplayWidget(Widget):
    poin_energi = NumericProperty(150)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode_game = "survival"
        self.tanaman_terpilih = None
        self.daftar_tanaman = []
        self.daftar_zombie = []
        self.daftar_peluru = []
        
        # Definisikan Ukuran Grid PvZ (Konstan)
        self.grid_awal_x = 120
        self.grid_awal_y = 80
        self.lebar_kotak = 70
        self.tinggi_kotak = 85
        
        # Gambar Batas Grid Kasar di Layar
        with self.canvas.before:
            Color(0.2, 0.4, 0.2, 1) # Lapangan Rumput Hijau
            self.bg = Rectangle(pos=(0,0), size=(1280, 720)) # Resolusi Virtual
            Color(0.3, 0.5, 0.3, 1)
            for b in range(6): # 5 Baris
                Line(points=[self.grid_awal_x, self.grid_awal_y + b*self.tinggi_kotak, self.grid_awal_x + 9*self.lebar_kotak, self.grid_awal_y + b*self.tinggi_kotak])
            for k in range(10): # 9 Kolom
                Line(points=[self.grid_awal_x + k*self.lebar_kotak, self.grid_awal_y, self.grid_awal_x + k*self.lebar_kotak, self.grid_awal_y + 5*self.tinggi_kotak])

        # Pembuat HUD Poin Matahari/Surya
        self.hud_label = Label(text=f"Energi: {self.poin_energi}", font_size='20sp', pos=(40, 600), color=(1,1,0,1))
        self.add_widget(self.hud_label)
        self.bind(poin_energi=self.update_hud)

        # Buat Tombol Kartu Pilihan Tanaman di Atas Layar (Seed Slots)
        self.buat_slot_kartu()

    def update_hud(self, *args):
        self.hud_label.text = f"Energi: {self.poin_energi}"

    def buat_slot_kartu(self):
        idx = 0
        for nama_id, data in DAFTAR_TANAMAN.items():
            btn = Button(text=f"{data['nama']}\n({data['harga']})", size=(100, 60), pos=(200 + idx*110, 620))
            btn.bind(on_press=lambda inst, nid=nama_id: self.pilih_kartu_tanaman(nid))
            self.add_widget(btn)
            idx += 1

    def pilih_kartu_tanaman(self, nama_id):
        self.tanaman_terpilih = nama_id

    def on_touch_down(self, touch):
        # Deteksi jika klik area grid untuk meletakkan tanaman
        if self.tanaman_terpilih and touch.y < 500:
            kolom = int((touch.x - self.grid_awal_x) // self.lebar_kotak)
            baris = int((touch.y - self.grid_awal_y) // self.tinggi_kotak)
            
            if 0 <= kolom < 9 and 0 <= baris < 5:
                # Cek apakah kotak kosong
                if not any(t.baris == baris and t.kolom == kolom for t in self.daftar_tanaman):
                    data_t = DAFTAR_TANAMAN[self.tanaman_terpilih]
                    if self.poin_energi >= data_t["harga"]:
                        self.poin_energi -= data_t["harga"]
                        
                        # Hitung koordinat presisi di tengah kotak grid
                        pos_x = self.grid_awal_x + (kolom * self.lebar_kotak) + 5
                        pos_y = self.grid_awal_y + (baris * self.tinggi_kotak) + 5
                        
                        t_baru = TanamanInstance(data_t, baris, kolom, pos=(pos_x, pos_y))
                        self.add_widget(t_baru)
                        self.daftar_tanaman.append(t_baru)
                        self.tanaman_terpilih = None # Reset pilihan tangan
                        return True
        return super().on_touch_down(touch)

    def mulai_gameplay_loop(self, mode):
        self.mode_game = mode
        self.poin_energi = 150
        # Schedule Engine Update 60 FPS (Gerakan Halus)
        Clock.schedule_interval(self.loop_utama, 1.0 / 60.0)
        # Schedule Spawning Musuh Berdasarkan Mode
        waktu_spawn = 4.0 if mode == "survival" else 2.5
        Clock.schedule_interval(self.spawn_zombie_wave, waktu_spawn)
        # Sky Surya Dropper Berkala
        Clock.schedule_interval(self.drop_surya_langit, 7.0)

    def drop_surya_langit(self, dt):
        x_acak = random.randint(200, 800)
        surya = EnergiMatahari(pos=(x_acak, 600))
        self.add_widget(surya)
        # Animasi jatuh pelan ke area rumput
        Clock.schedule_interval(lambda _dt: setattr(surya, 'y', surya.y - 2) if surya.y > random.randint(150, 400) else False, 1.0/60.0)

    def spawn_zombie_wave(self, dt):
        baris_acak = random.randint(0, 4)
        jenis_zombie = random.choice(list(DAFTAR_ZOMBIE.keys()))
        data_z = DAFTAR_ZOMBIE[jenis_zombie]
        
        pos_y = self.grid_awal_y + (baris_acak * self.tinggi_kotak) + 5
        z_baru = ZombieInstance(data_z, baris_acak, pos=(1000, pos_y))
        self.add_widget(z_baru)
        self.daftar_zombie.append(z_baru)

    def loop_utama(self, dt):
    # Update projectiles
    for peluru in self.daftar_peluru[:]:
        try:
            peluru.bergerak()
        except Exception:
            # If projectile has different interface, move by kecepatan_x if available
            peluru.x += getattr(peluru, 'kecepatan_x', 0)

        # Remove projectile if off-screen
        if peluru.x > self.width + 50 or peluru.x < -50 or peluru.y < -50 or peluru.y > self.height + 50:
            if peluru.parent:
                self.remove_widget(peluru)
            if peluru in self.daftar_peluru:
                self.daftar_peluru.remove(peluru)
            continue

        # Check collision with zombies (same row)
        for z in self.daftar_zombie[:]:
            if getattr(z, 'baris', None) == getattr(peluru, 'baris', None) and peluru.collide_widget(z):
                # Apply damage — adjust value per weapon
                z.darah -= 50
                if peluru.parent:
                    self.remove_widget(peluru)
                if peluru in self.daftar_peluru:
                    self.daftar_peluru.remove(peluru)
                break

    # Update zombies
    for z in self.daftar_zombie[:]:
        z.berjalan()
        # Remove zombies that passed left edge
        if z.x < -100:
            if z.parent:
                self.remove_widget(z)
            if z in self.daftar_zombie:
                self.daftar_zombie.remove(z)
            continue

        # If zombie collides with a plant in same row, damage plant and handle removal
        for t in self.daftar_tanaman[:]:
            if getattr(t, 'baris', None) == getattr(z, 'baris', None) and z.collide_widget(t):
                # Damage plant
                t.darah -= 10
                if t.darah <= 0:
                    if t.parent:
                        self.remove_widget(t)
                    if t in self.daftar_tanaman:
                        self.daftar_tanaman.remove(t)

                # If zombie died due to plant interaction
                if z.darah <= 0:
                    if z.parent:
                        self.remove_widget(z)
                    if z in self.daftar_zombie:
                        self.daftar_zombie.remove(z)
                break

        # Remove dead zombies (from projectile damage above)
        if z.darah <= 0:
            if z.parent:
                self.remove_widget(z)
            if z in self.daftar_zombie:
                self.daftar_zombie.remove(z)

    # Update HUD (energy label already bound to poin_energi, but ensure it's refreshed)
    self.update_hud()

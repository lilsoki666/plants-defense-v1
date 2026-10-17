import json, os, random
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

SAVE_FILE = 'plant_defense_save.json'
PLANTS = {
 'melati': {'name':'Melati Suci','cost':50,'hp':180,'kind':'sun','color':(0.95,0.92,0.72,1)},
 'sawit': {'name':'Sawit Penembak','cost':100,'hp':220,'kind':'shoot','color':(0.15,0.55,0.22,1)},
 'bambu': {'name':'Bambu Runcing','cost':75,'hp':950,'kind':'wall','color':(0.55,0.72,0.25,1)},
 'semar': {'name':'Kantong Semar','cost':150,'hp':300,'kind':'bite','color':(0.58,0.22,0.62,1)},
}
ZOMBIES = [
 {'name':'Pocong','hp':180,'speed':17,'color':(0.82,0.82,0.82,1),'damage':18},
 {'name':'Kunti Terbang','hp':125,'speed':29,'color':(0.86,0.48,0.78,1),'damage':14},
 {'name':'Genderuwo','hp':520,'speed':9,'color':(0.25,0.23,0.21,1),'damage':35},
]

def btn(text, fn, height=46):
 b=Button(text=text,size_hint_y=None,height=dp(height),font_size=sp(16),background_normal='',background_color=(.12,.42,.22,1))
 b.bind(on_release=fn); return b

class SaveSystem:
 @staticmethod
 def load():
  path=os.path.join(App.get_running_app().user_data_dir,SAVE_FILE)
  try:
   with open(path,'r',encoding='utf-8') as f: data=json.load(f)
   if not isinstance(data,dict): data={}
  except Exception: data={}
  data.setdefault('player_name','Pemain Nusantara'); data.setdefault('unlocked_level',1); data.setdefault('coins',0); data.setdefault('completed_levels',[])
  return data
 @staticmethod
 def save(data):
  try:
   with open(os.path.join(App.get_running_app().user_data_dir,SAVE_FILE),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
  except Exception as e: print('Save gagal:',e)

class HomeScreen(Screen):
 def __init__(self,**kw):
  super().__init__(name='home',**kw); root=BoxLayout(orientation='vertical',padding=dp(18),spacing=dp(9))
  with root.canvas.before:
   Color(.08,.19,.13,1); self.bg=Rectangle(pos=root.pos,size=root.size)
  root.bind(pos=self._bg,size=self._bg)
  root.add_widget(Label(text='[b]PLANT DEFENSE[/b]\n[color=ffcf55]NUSANTARA EDITION[/color]',markup=True,font_size=sp(30),halign='center',size_hint_y=.34))
  self.info=Label(text='',font_size=sp(16),size_hint_y=None,height=dp(28)); root.add_widget(self.info)
  root.add_widget(btn('PETUALANGAN',lambda *_:setattr(self.manager,'current','levels')))
  root.add_widget(btn('SURVIVAL',lambda *_:self.start('survival')))
  root.add_widget(btn('MINI GAMES',lambda *_:self.start('minigame')))
  root.add_widget(btn('PROFIL PEMAIN',lambda *_:self.profile()))
  root.add_widget(btn('KELUAR',lambda *_:App.get_running_app().stop(),40)); self.add_widget(root); self.bind(on_enter=self.refresh)
 def _bg(self,o,*a): self.bg.pos=o.pos; self.bg.size=o.size
 def refresh(self,*a):
  d=App.get_running_app().save_data; self.info.text=f"{d['player_name']}  •  Koin: {d['coins']}  •  Level: {d['unlocked_level']}"
 def start(self,mode): self.manager.get_screen('game').begin(mode,1); self.manager.current='game'
 def profile(self):
  app=App.get_running_app(); box=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(8)); field=TextInput(text=app.save_data.get('player_name',''),multiline=False,size_hint_y=None,height=dp(44)); box.add_widget(Label(text='Nama pemain')); box.add_widget(field)
  pop=Popup(title='Profil Pemain',content=box,size_hint=(.85,.4),auto_dismiss=False)
  row=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(6)); row.add_widget(btn('SIMPAN',lambda *_:self.save_profile(field.text,pop),40)); row.add_widget(btn('BATAL',lambda *_:pop.dismiss(),40)); box.add_widget(row); pop.open()
 def save_profile(self,name,pop):
  app=App.get_running_app(); app.save_data['player_name']=name.strip()[:24] or 'Pemain Nusantara'; app.persist(); pop.dismiss(); self.refresh()

class LevelScreen(Screen):
 def __init__(self,**kw):
  super().__init__(name='levels',**kw); root=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(8)); root.add_widget(Label(text='[b]PETA PETUALANGAN[/b]',markup=True,font_size=sp(24),size_hint_y=None,height=dp(45)))
  self.grid=GridLayout(cols=5,spacing=dp(6)); root.add_widget(self.grid); root.add_widget(btn('KEMBALI',lambda *_:setattr(self.manager,'current','home'))); self.add_widget(root); self.bind(on_enter=self.refresh)
 def refresh(self,*a):
  self.grid.clear_widgets(); d=App.get_running_app().save_data
  for n in range(1,26):
   open_level=n<=int(d.get('unlocked_level',1)); b=Button(text=str(n) if open_level else 'LOCK',background_normal='',background_color=(.18,.52,.25,1) if open_level else (.3,.3,.3,1),font_size=sp(15))
   if open_level: b.bind(on_release=lambda _b,l=n:self.play(l))
   self.grid.add_widget(b)
 def play(self,l): self.manager.get_screen('game').begin('adventure',l); self.manager.current='game'

class Plant(Widget):
 def __init__(self,key,row,col,pos,**kw):
  super().__init__(**kw); d=PLANTS[key]; self.key=key; self.row=row; self.col=col; self.hp=d['hp']; self.kind=d['kind']; self.timer=random.uniform(.5,1.2); self.size=(dp(42),dp(48)); self.pos=pos
  with self.canvas:
   Color(*d['color']); self.body=Ellipse(pos=self.pos,size=self.size); Color(.08,.16,.08,1); self.eye=Ellipse(pos=(self.x+dp(26),self.y+dp(27)),size=(dp(4),dp(4)))
  self.bind(pos=self.sync)
 def sync(self,*a): self.body.pos=self.pos; self.eye.pos=(self.x+dp(26),self.y+dp(27))

class Zombie(Widget):
 def __init__(self,data,row,pos,**kw):
  super().__init__(**kw); self.row=row; self.hp=data['hp']; self.speed=data['speed']; self.damage=data['damage']; self.attack_timer=0; self.size=(dp(34),dp(54)); self.pos=pos
  with self.canvas:
   Color(*data['color']); self.body=Rectangle(pos=self.pos,size=self.size); Color(.08,.08,.08,1); self.eye=Ellipse(pos=(self.x+dp(8),self.y+dp(35)),size=(dp(5),dp(5)))
  self.bind(pos=self.sync)
 def sync(self,*a): self.body.pos=self.pos; self.eye.pos=(self.x+dp(8),self.y+dp(35))

class Shot(Widget):
 def __init__(self,row,pos,**kw):
  super().__init__(**kw); self.row=row; self.damage=45; self.size=(dp(13),dp(13)); self.pos=pos
  with self.canvas: Color(1,.68,.1,1); self.shape=Ellipse(pos=self.pos,size=self.size)
  self.bind(pos=lambda *_:setattr(self.shape,'pos',self.pos))

class Sun(Widget):
 def __init__(self,pos,**kw):
  super().__init__(**kw); self.size=(dp(27),dp(27)); self.pos=pos; self.age=0
  with self.canvas: Color(1,.82,.12,1); self.shape=Ellipse(pos=self.pos,size=self.size)
  self.bind(pos=lambda *_:setattr(self.shape,'pos',self.pos))

class GameScreen(Screen):
 sun=NumericProperty(150); mode=StringProperty('adventure'); level=NumericProperty(1)
 def __init__(self,**kw):
  super().__init__(name='game',**kw); self.plants=[]; self.zombies=[]; self.shots=[]; self.suns=[]; self.selected=None; self.event=None; self.spawn_t=0; self.sun_t=0; self.kills=0
  root=BoxLayout(orientation='vertical',padding=dp(4),spacing=dp(3)); hud=BoxLayout(size_hint_y=None,height=dp(40),spacing=dp(4)); self.hud_label=Label(text='Surya: 150',font_size=sp(15)); hud.add_widget(self.hud_label); hud.add_widget(btn('SEKOP',lambda *_:self.select('shovel'),36)); hud.add_widget(btn('JEDA',lambda *_:self.pause(),36)); hud.add_widget(btn('MENU',lambda *_:self.leave(),36)); root.add_widget(hud)
  self.cards=BoxLayout(size_hint_y=None,height=dp(60),spacing=dp(3)); root.add_widget(self.cards); self.board=Widget(); root.add_widget(self.board); self.add_widget(root)
  self.board.bind(pos=self.draw_grid,size=self.draw_grid,on_touch_down=self.board_touch); self.bind(sun=self.update_hud)
 def draw_grid(self,*a):
  self.board.canvas.before.clear()
  with self.board.canvas.before:
   Color(.23,.48,.21,1); Rectangle(pos=self.board.pos,size=self.board.size); Color(.39,.62,.31,1)
   for r in range(1,5):
    y=self.board.y+self.board.height*r/5; Line(points=[self.board.x,y,self.board.right,y],width=1)
   for c in range(1,9):
    x=self.board.x+self.board.width*c/9; Line(points=[x,self.board.y,x,self.board.top],width=1)
 def update_hud(self,*a): self.hud_label.text=f'Surya: {int(self.sun)}   Musuh dikalahkan: {self.kills}'
 def begin(self,mode='adventure',level=1):
  self.stop(); self.clear_entities(); self.mode=mode; self.level=level; self.sun=200 if mode=='survival' else 150; self.spawn_t=self.sun_t=0; self.kills=0; self.selected=None; self.cards.clear_widgets()
  for key,d in PLANTS.items():
   b=Button(text=f"{d['name']}\n{d['cost']}",font_size=sp(10),background_normal='',background_color=d['color']); b.bind(on_release=lambda _b,k=key:self.select(k)); self.cards.add_widget(b)
  self.event=Clock.schedule_interval(self.tick,1/30); self.update_hud()
 def select(self,key): self.selected=key; self.hud_label.text='Pilih petak kosong' if key!='shovel' else 'Ketuk tanaman untuk menghapus'
 def board_touch(self,board,touch):
  if not board.collide_point(*touch.pos): return False
  # Koleksi surya diperiksa lebih dahulu agar tidak dianggap sebagai klik petak.
  for sun in self.suns[:]:
   if sun.collide_point(*touch.pos):
    self.sun += 25
    self.remove(sun,self.suns)
    return True
  col=int((touch.x-board.x)/max(1,board.width/9)); row=int((touch.y-board.y)/max(1,board.height/5))
  if not (0<=col<9 and 0<=row<5): return True
  old=next((p for p in self.plants if p.row==row and p.col==col),None)
  if self.selected=='shovel':
   if old: self.remove(old,self.plants)
   self.selected=None; return True
  if not self.selected: return True
  key=self.selected; cost=PLANTS[key]['cost']
  if old is None and self.sun>=cost:
   cw=self.board.width/9; ch=self.board.height/5; pos=(self.board.x+col*cw+(cw-dp(42))/2,self.board.y+row*ch+(ch-dp(48))/2); p=Plant(key,row,col,pos); self.board.add_widget(p); self.plants.append(p); self.sun-=cost; self.selected=None
  return True
 def tick(self,dt):
  self.spawn_t+=dt; self.sun_t+=dt
  if self.spawn_t>=max(1.5,4.2-self.level*.07): self.spawn_t=0; self.spawn_zombie()
  if self.sun_t>=7: self.sun_t=0; self.spawn_sun()
  for p in self.plants[:]:
   p.timer-=dt
   if p.kind=='sun' and p.timer<=0: self.spawn_sun((p.center_x,p.top)); p.timer=8
   elif p.kind=='shoot' and p.timer<=0 and any(z.row==p.row and z.x>p.x for z in self.zombies):
    s=Shot(p.row,(p.right,p.center_y)); self.board.add_widget(s); self.shots.append(s); p.timer=1.25
   elif p.kind=='bite' and p.timer<=0:
    z=next((z for z in self.zombies if z.row==p.row and z.x<=p.right+dp(30) and z.right>=p.x),None)
    if z: z.hp-=120; p.timer=2
  for s in self.shots[:]:
   s.x+=dp(250)*dt; z=next((z for z in self.zombies if z.row==s.row and s.collide_widget(z)),None)
   if z: z.hp-=s.damage; self.remove(s,self.shots)
   elif s.x>self.board.right: self.remove(s,self.shots)
  for z in self.zombies[:]:
   p=next((p for p in self.plants if p.row==z.row and z.x<=p.right and z.right>=p.x),None)
   if p:
    z.attack_timer+=dt
    if z.attack_timer>=.7: p.hp-=z.damage; z.attack_timer=0
    if p.hp<=0: self.remove(p,self.plants)
   else: z.x-=dp(z.speed)*dt
   if z.hp<=0: self.kills+=1; self.remove(z,self.zombies)
   elif z.right<self.board.x: self.game_over(); return
  for s in self.suns[:]:
   s.age+=dt
   if s.age<1.5: s.y=max(self.board.y+dp(10),s.y-dp(20)*dt)
   elif s.age>12: self.remove(s,self.suns)
  self.update_hud()
  if self.mode=='adventure' and self.kills>=8+self.level*2: self.win()
 def spawn_zombie(self):
  d=dict(random.choice(ZOMBIES)); d['hp']+=self.level*10; row=random.randrange(5); ch=self.board.height/5; z=Zombie(d,row,(self.board.right-dp(35),self.board.y+row*ch+(ch-dp(54))/2)); self.board.add_widget(z); self.zombies.append(z)
 def spawn_sun(self,pos=None):
  if self.board.width<=0 or self.board.height<=0:return
  x,y=pos if pos else (random.uniform(self.board.x+dp(12),self.board.right-dp(35)),self.board.top-dp(35)); s=Sun((x,y)); self.board.add_widget(s); self.suns.append(s)
 def remove(self,obj,items):
  if obj in items: items.remove(obj)
  if obj.parent: obj.parent.remove_widget(obj)
 def clear_entities(self):
  for arr in (self.plants,self.zombies,self.shots,self.suns):
   for o in arr[:]:
    if o.parent:o.parent.remove_widget(o)
   arr.clear()
 def stop(self):
  if self.event: self.event.cancel(); self.event=None
 def pause(self):
  if self.event: self.event.cancel(); self.event=None
  box=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(8)); pop=Popup(title='Permainan dijeda',content=box,size_hint=(.8,.35)); box.add_widget(Label(text='Lanjutkan permainan?')); box.add_widget(btn('LANJUTKAN',lambda *_:(pop.dismiss(),self.resume()),40)); box.add_widget(btn('KELUAR KE MENU',lambda *_:(pop.dismiss(),self.leave()),40)); pop.open()
 def resume(self):
  if not self.event:self.event=Clock.schedule_interval(self.tick,1/30)
 def leave(self): self.stop(); self.clear_entities(); self.manager.current='home'
 def win(self):
  self.stop(); app=App.get_running_app(); d=app.save_data; d['coins']=int(d.get('coins',0))+25; d['completed_levels']=sorted(set(d.get('completed_levels',[])+[int(self.level)])); d['unlocked_level']=max(int(d.get('unlocked_level',1)),int(self.level)+1); app.persist(); self.result('LEVEL SELESAI!','Kebun berhasil dipertahankan.\n+25 koin')
 def game_over(self): self.stop(); self.result('KEBUN DISERBU!','Musuh melewati pertahanan. Coba susun tanaman di lebih banyak baris.')
 def result(self,title,message):
  box=BoxLayout(orientation='vertical',padding=dp(10),spacing=dp(8)); box.add_widget(Label(text=message,halign='center')); pop=Popup(title=title,content=box,size_hint=(.82,.4),auto_dismiss=False); box.add_widget(btn('KEMBALI KE MENU',lambda *_:(pop.dismiss(),self.leave()),42)); pop.open()

class PlantDefenseApp(App):
 def build(self):
  self.title='Plant Defense: Nusantara'; self.save_data=SaveSystem.load(); manager=ScreenManager(transition=FadeTransition(duration=.15)); manager.add_widget(HomeScreen()); manager.add_widget(LevelScreen()); manager.add_widget(GameScreen()); return manager
 def persist(self): SaveSystem.save(self.save_data)
 def on_pause(self): self.persist(); return True
 def on_stop(self): self.persist()

if __name__=='__main__': PlantDefenseApp().run()

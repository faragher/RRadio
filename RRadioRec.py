import RCodec2 as RC
import simpleaudio as SA
import LXMF
from LXMF import LXMessage
import time
import curses as C
import RNS
import os


targetmode = 1200
playing_object = None
message_queue = []
seen_messages = []
should_quit = False
target_message = 0
message_offset = 0
displayname = "Radio Test"
local_hash = ""
message_dir = "."
log_dir = "."
last_played = 0

## Test LXM
with open('packed.c2','rb') as input:
  B = input.read()
P = {'CODEC':'Codec2','MODE': targetmode, 'BYTES': B}
F = {LXMF.FIELD_AUDIO: P}
TLXM = LXMF.LXMessage(None,None, fields = F, destination_hash = 0x1234, source_hash = 0x0123456789abcdef0123456789abcdef)

class update_container:
  def __init__(self):
    self.Message = False
    self.MessageUI = False
    self.Header = False

  def reset(self):
    self.Message = False
    self.MessageUI = False
    self.Header = False


def PlayMessage(LM):
  if LXMF.FIELD_AUDIO in LM.fields:
    F = LM.fields[LXMF.FIELD_AUDIO]
    if 'CODEC' in F and F['CODEC'] == 'Codec2':
      if 'MODE' in F:
        if RC.CheckMode(F['MODE']):
          if 'BYTES' in F:
            global playing_object
            # Data, channels, bytes per sample, sample rate (X,1,2,8000)
            playing_object = SA.play_buffer(RC.DecodeC2(F['MODE'],F['BYTES']),1,2,8000)

def sweep_input(stdscr):
  c = stdscr.getch()
  if c != -1:
#    stdscr.addstr(str(c)+' ')
#    stdscr.refresh()
#    stdscr.move(0,0)
    global target_message, seen_messages, message_offset, dirty, playing_object, should_quit, message_queue, last_played
    match c:
      case 114: #R
        replay_message_index(last_played)
      case 115: #s
        playing_object.stop()
      case 120:
        message_queue.clear()
        playing_object.stop()
      case 27:
        should_quit = True
      case C.KEY_UP:
#        global target_message
        target_message -= 1
        if target_message < 0:
          target_message = 0
        dirty.MessageUI = True
      case C.KEY_DOWN:
#        global target_message, messages_seen
        target_message += 1
        if target_message > len(seen_messages) -1:
          target_message = len(seen_messages) -1
        if target_message > 9:
          target_message = 9
        if target_message < 0:
          target_message = 0
        dirty.MessageUI = True
      case C.KEY_LEFT:
        if message_offset > 0:
          message_offset -= 1
        target_message = 0
        dirty.MessageUI = True
        dirty.Message = True
      case C.KEY_RIGHT:
        message_offset += 1
        target_message = 0
        dirty.MessageUI = True
        dirty.Message = True
      case 10:
        mIndex = 10*message_offset+target_message
        if len(seen_messages) > 0 and mIndex < len(seen_messages):
          last_played = mIndex
          replay_message(seen_messages[mIndex])
      case _:
        pass
  # 114 - R
  # 27 - esc
  # 259 up
  # 258 down
  # 32 space

def replay_message_index(I):
  global message_queue, seen_messages
  message_queue.append(seen_messages[I])

def replay_message(M):
  global message_queue
  message_queue.append(M)

def add_message(M):
  global message_queue, seen_messages, dirty
  message_queue.append(M)
  seen_messages.insert(0,M)

#for i in range(25):
#  add_message(TLXM)


def render_header(H):
  H.move(2,0)
  H.addstr("*******************************************************************************")
  H.move(1,57)
  H.addstr("MESSAGES")
  H.move(0,2)
  H.addstr("Receiving on: "+local_hash)
  H.refresh()

def render_messages(W):
  global seen_messages, message_offset
  W.clear()
  num_messages = len(seen_messages)-(10*message_offset)
  shown_messages = num_messages
  if num_messages < 1:
    if message_offset == 0:
      return
    else:
      message_offset -= 1
      num_messages = len(seen_messages)-(10*message_offset)
      shown_messages = num_messages

  if num_messages > 10:
    shown_messages = 10
  for i in range(0, shown_messages):
    W.move(2*i,1)
    mIndex = 10*message_offset+i
    L = seen_messages[mIndex]
    W.addstr(RNS.hexrep(L.source_hash,delimit = ""))
    W.move(2*i+1,14)
    timestamp = time.localtime(L.timestamp)
    friendlytime = time.strftime('%H:%M %d%b%Y%z',timestamp)
    W.addstr(str(friendlytime))
  W.refresh()

def render_message_UI(W):
  global target_message
  W.clear()
  W.move(2*target_message,0)
  W.addstr(">")
  W.refresh()

def render_help(W):
  W.clear()
  W.addstr(4,2,"Arrows navigate messages")
  W.addstr(5,2,"Enter plays selected")
  W.addstr(6,2,"R - Replay Last")
  W.addstr(7,2,"S - Stop Playing")
  W.addstr(8,2,"X - Clear Queue")
  W.addstr(9,2,"Esc - Close")
  W.refresh()

def ReceiveLXM(L):
  global dirty, message_dir, last_played
  dirty.Message = True
  add_message(L)
  last_played = 0
  L.write_to_directory(message_dir)

def LoadAllFromDirectory(path):
  global seen_messages
  for file in os.listdir(path):
    handle = os.path.join(path,file)
    if os.path.isfile(handle):
      try:
        LoadLXMFromFile(handle)
      except Exception as e:
       Log("File "+str(handle)+" cannot be loaded: "+str(e))
  seen_messages.sort(key = lambda L: L.timestamp, reverse = True )

def LoadLXMFromFile(P):
  fileonly = bytes.fromhex(P.split("/")[-1])
  with open(P,"rb") as f:
    #print(f)
    L = LXMessage.unpack_from_file(f)
#    if not L.signature_validated:
#      Log("Reject "+RNS.hexrep(L.hash,delimit = "")+": Signature not validated")
#      return
    try:
      hashhex = bytes.fromhex(RNS.hexrep(L.hash,delimit = ""))
    except:
      hashhex = bytes.fromhex("0")
    if fileonly != hashhex:
      Log("Reject "+str(P)+": Message hash does not match file name.")
      return
  global seen_messages
  seen_messages.append(L)

def Log(M):
  global log_dir
  with open(log_dir,'a') as L:
    L.write(M)


def main(stdscr):
  global message_dir, should_quit, dirty, log_dir
  R = RNS.Reticulum()
  userdir = os.path.expanduser("~")
  configdir = userdir+"/.RRadio"
  identitypath = configdir+"/identity"
  log_dir = configdir+"/storage/log"
  message_dir = configdir+"/storage/messages"
  os.makedirs(message_dir,exist_ok=True)
  if os.path.exists(identitypath):
    ID = RNS.Identity.from_file(identitypath)
  else:
    ID = RNS.Identity()
    ID.to_file(identitypath)
  L = LXMF.LXMRouter(identity = ID, storagepath = userdir+"/storage/messages")
  L_dest = L.register_delivery_identity(ID,display_name = displayname)
  L.register_delivery_callback(ReceiveLXM)
  L_dest.announce()
  LoadAllFromDirectory(message_dir)
  global local_hash
  local_hash = RNS.hexrep(L_dest.hash, delimit = "")

  stdscr.nodelay(1)
  stdscr.keypad(True)
  stdscr.refresh()
  C.curs_set(0)
#  global should_quit, dirty
  MW = C.newwin(21,39,3,41)
  MWUI = C.newwin(21,1,3,40)
  SW = C.newwin(10,40,3,0)
  HW = C.newwin(10,40,13,0)
  Header = C.newwin(3,80,0,0)
  render_header(Header)
  render_messages(MW)
  render_message_UI(MWUI)
  render_help(HW)
  while not should_quit:
    sweep_input(stdscr)
    if not playing_object or not playing_object.is_playing():
      if len(message_queue)>0:
        PlayMessage(message_queue.pop())
    if dirty.Header: 
      render_header(Header)
    if dirty.Message:
      render_messages(MW)
    if dirty.MessageUI:
      render_message_UI(MWUI)
    dirty.reset()
    time.sleep(0.1)

dirty = update_container()
C.wrapper(main)

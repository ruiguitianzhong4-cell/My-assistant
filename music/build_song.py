"""「スキップ・ビート」を生成する: song.json / MIDI / MP3（全体・伴奏のみ）"""
import json, subprocess, numpy as np, mido, pathlib, wave

OUT = pathlib.Path(__file__).parent
BPM = 150
TITLE = "スキップ・ビート"
NOTE = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def midi_of(n): return 12*(int(n[-1])+1)+NOTE[n[0]]

# メロディ: 音名+オクターブ:長さ(8分音符単位)。R=休符。1小節=8
INTRO = ["R:8","R:8"]
A = ["E5:1 G5:1 R:1 G5:1 A5:1 G5:1 E5:2", "C5:1 E5:1 R:1 E5:1 D5:2 C5:2",
     "A5:1 A5:1 R:1 A5:1 C6:1 A5:1 G5:2", "F5:1 E5:1 D5:4 R:2",
     "E5:1 G5:1 R:1 G5:1 A5:1 G5:1 E5:2", "C5:1 E5:1 R:1 E5:1 G5:2 A5:2",
     "C6:1 A5:1 G5:1 A5:1 G5:1 F5:1 E5:1 D5:1", "C5:4 R:4"]
B = ["R:1 A5:1 R:1 A5:1 G5:1 A5:1 R:1 C6:1", "R:1 B5:1 R:1 B5:1 A5:1 G5:2 D5:1",
     "R:1 G5:1 R:1 G5:1 E5:1 G5:1 R:1 B5:1", "A5:6 R:2",
     "R:1 A5:1 R:1 A5:1 G5:1 A5:1 R:1 C6:1", "R:1 B5:1 R:1 B5:1 C6:1 D6:1 C6:1 B5:1",
     "C6:2 A5:2 E5:2 A5:2", "G5:2 R:1 G5:1 G5:1 A5:1 B5:2"]
S = ["C6:2 C6:1 A5:1 R:1 A5:1 C6:2", "D6:2 B5:1 G5:1 R:1 G5:1 B5:2",
     "B5:1 B5:1 R:1 G5:1 B5:1 C6:1 B5:2", "A5:3 E5:1 A5:2 B5:2",
     "C6:2 C6:1 A5:1 R:1 A5:1 C6:2", "D6:2 B5:1 G5:1 R:1 D6:1 C6:1 B5:1",
     "A5:1 C6:1 R:1 A5:1 G5:1 B5:1 R:1 D6:1", "C6:1 R:1 G5:1 C6:1 R:4"]
CH_I = [["C"],["G"]]
CH_A = [["C"],["Am"],["F"],["G"],["C"],["Am"],["F","G"],["C"]]
CH_B = [["F"],["G"],["Em"],["Am"],["F"],["G"],["Am"],["G"]]
CH_S = [["F"],["G"],["Em"],["Am"],["F"],["G"],["F","G"],["C"]]
SECTIONS = [("イントロ",INTRO,CH_I),("Aメロ",A,CH_A),("Bメロ",B,CH_B),("サビ",S,CH_S)]
CHORD = {'C':[48,52,55],'Am':[45,48,52],'F':[41,45,48],'G':[43,47,50],'Em':[40,43,47]}
ROOT  = {'C':36,'Am':33,'F':29,'G':31,'Em':28}

bars = []
for name, mel, chs in SECTIONS:
    for i,(m,c) in enumerate(zip(mel,chs)):
        notes = []
        for tok in m.split():
            p,d = tok.split(':')
            notes.append([None if p=='R' else p, int(d)])
        assert sum(d for _,d in notes)==8, (name,i,m)
        bars.append({"section": name if i==0 else None, "chords": c, "notes": notes})
LAST = len(bars)-1

# ---- イベント列（拍=8分音符単位） ----
mel_ev, bass_ev, chord_ev, drum_ev = [], [], [], []   # (start8, len8, midi, vel)
for b,bar in enumerate(bars):
    t0 = b*8; t = t0
    for p,d in bar["notes"]:
        if p: mel_ev.append((t, d, midi_of(p), 100))
        t += d
    nch = len(bar["chords"])
    for ci,ch in enumerate(bar["chords"]):
        span = 8//nch; s = t0+ci*span
        if b==LAST:   # エンディング「ジャン」
            for n in CHORD['C']: chord_ev.append((t0, 1, n+12, 90))
            for n in CHORD['C']: chord_ev.append((t0+3, 1, n+12, 100))
            bass_ev += [(t0,1,36,110),(t0+3,1,36,110)]
            continue
        for k in range(span):            # ベース: 8分でオクターブ跳ね
            bass_ev.append((s+k, 1, ROOT[ch] + (12 if k%2 else 0), 100 if k%2==0 else 80))
        for k in range(1, span, 2):      # コード: 裏拍で刻む
            for n in CHORD[ch]: chord_ev.append((s+k, 1, n+12, 70))
    if b==LAST:
        drum_ev += [(t0,1,36,120),(t0,1,49,110),(t0+3,1,36,120),(t0+3,1,49,120)]
        continue
    for k in range(8):
        drum_ev.append((t0+k, 1, 42, 70 if k%2 else 90))         # ハイハット
    for k in (0,3,4): drum_ev.append((t0+k, 1, 36, 115))          # キック(1, 2の裏, 3)
    for k in (2,6):   drum_ev.append((t0+k, 1, 38, 110))          # スネア 2,4
    if b in (1, 9, 17): drum_ev.append((t0,1,49,110))             # セクション頭にシンバル
    if b in (8, 16):                                              # フィル
        for k in (5,6,7): drum_ev.append((t0+k,1,38,100))

# ---- song.json ----
json.dump({"title":TITLE,"bpm":BPM,"bars":bars}, open(OUT/"song.json","w"), ensure_ascii=False, indent=1)

# ---- MIDI ----
TPB = 480; E8 = TPB//2
mf = mido.MidiFile(ticks_per_beat=TPB)
def track(events, ch, prog, name):
    tr = mido.MidiTrack(); mf.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name=name))
    if ch==0: tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
    if prog is not None: tr.append(mido.Message('program_change', channel=ch, program=prog))
    msgs=[]
    for s,l,n,v in events:
        msgs.append((s*E8, 1, n, v)); msgs.append(((s+l)*E8 - (10 if ch!=9 else 0), 0, n, 0))
    msgs.sort(key=lambda x:(x[0], x[1]))
    now=0
    for t,on,n,v in msgs:
        tr.append(mido.Message('note_on' if on else 'note_off', channel=ch, note=n, velocity=v, time=t-now)); now=t
track(mel_ev, 0, 74, "Recorder")
track(chord_ev, 1, 4, "E.Piano")
track(bass_ev, 2, 33, "Bass")
track(drum_ev, 9, None, "Drums")
mf.save(OUT/"skip_beat.mid")

# ---- 簡易シンセで音声化 ----
SR = 44100; sec8 = 60/BPM/2
total = int((len(bars)*8 + 4)*sec8*SR)
def hz(m): return 440*2**((m-69)/12)
def env(n, a, r):
    e = np.ones(n); a=min(a,n); r=min(r,n)
    e[:a] = np.linspace(0,1,a); e[n-r:] *= np.linspace(1,0,r); return e
def render(events, kind):
    buf = np.zeros(total)
    rng = np.random.default_rng(1)
    for s,l,n,v in events:
        st = int(s*sec8*SR); amp = v/127
        if kind=='drum':
            if n==36: L=int(.25*SR); t=np.arange(L)/SR; w=np.sin(2*np.pi*(50+90*np.exp(-t*30))*t)*np.exp(-t*12)*1.0
            elif n==38: L=int(.18*SR); t=np.arange(L)/SR; w=(rng.standard_normal(L)*.6+np.sin(2*np.pi*190*t)*.4)*np.exp(-t*22)*.7
            elif n==42: L=int(.05*SR); t=np.arange(L)/SR; x=rng.standard_normal(L); w=np.diff(x,prepend=0)*np.exp(-t*80)*.18
            else: L=int(1.2*SR); t=np.arange(L)/SR; x=rng.standard_normal(L); w=np.diff(x,prepend=0)*np.exp(-t*3)*.2
        else:
            L = int(l*sec8*SR*0.92); t = np.arange(L)/SR; f = hz(n)
            if kind=='mel':
                vib = 1+0.004*np.sin(2*np.pi*5.5*t)*np.clip(t*4,0,1)
                ph = 2*np.pi*f*np.cumsum(vib)/SR
                w = (np.sin(ph)+.25*np.sin(2*ph)+.1*np.sin(3*ph)+.015*rng.standard_normal(L))*env(L,int(.015*SR),int(.03*SR))*.45
            elif kind=='bass':
                ph = 2*np.pi*f*t; w = (np.sin(ph)+.5*np.sin(2*ph)+.2*np.sin(3*ph))*np.exp(-t*3)*env(L,200,800)*.5
            else:
                ph = 2*np.pi*f*t; w = (np.sin(ph)+.3*np.sin(2*ph)+.1*np.sin(4*ph))*np.exp(-t*6)*env(L,100,1500)*.16
        w = w*amp; e = min(total, st+len(w)); buf[st:e] += w[:e-st]
    return buf
mel = render(mel_ev,'mel'); acc = render(bass_ev,'bass')+render(chord_ev,'chord')+render(drum_ev,'drum')
def save(x, name):
    x = x/np.max(np.abs(x))*0.9; pcm = (x*32767).astype(np.int16)
    wav = OUT/(name+'.wav')
    with wave.open(str(wav),'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(wav),'-b:a','128k',str(OUT/(name+'.mp3'))],check=True); wav.unlink()
save(mel*1.1+acc, "skip_beat_full")
save(acc, "skip_beat_karaoke")
print("bars", len(bars), "length", round(len(bars)*8*sec8,1), "s")

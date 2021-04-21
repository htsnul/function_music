import wave, struct, math

def beatTimeDelta():
    tempo = 120
    return 60 / tempo

def timeFromBeat(beat):
    return beat* beatTimeDelta()

def beatFromTime(t):
    return t / beatTimeDelta()

def envelopeAR(t, at, rt):
    if t < 0 or (at + rt) <= t: return 0
    if t < at: return t / at
    if at < t: return 1 - (t - at) / rt
    return 1

def envelopeASR(t, duration, at, rt):
    st = max(0, duration - at)
    if t < 0 or (at + st + rt) <= t: return 0
    if t < at: return t / at
    if t < at + st: return 1
    if at + st < t: return 1 - (t - (at + st)) / rt
    return 1

def noteNumberFromString(str):
    octaveOffset = 12 * (ord(str[0]) - ord("4"))
    scaleOffset = {"c": -9, "d": -7, "e": -5, "f": -4, "g":-2, "a": 0, "b": 2}[str[1]]
    sharpFlatOffset = 0
    if len(str) >= 3: sharpFlatOffset = (1 if str[2] == "+" else 0) + (-1 if str[2] == "-" else 0)
    return 69 + octaveOffset + scaleOffset + sharpFlatOffset

def angularVelocityByNoteNumber(nn):
    return 440 * math.pow(2, (nn - 69) / 12) * math.pi

def toneSine(t, nn, duration):
    e = envelopeASR(t, duration, 0.001, 0.01)
    if e == 0: return 0
    return 0.125 * e * math.sin(t * angularVelocityByNoteNumber(nn))

def tonePiano(t, nn, duration):
    e = 0.5 * envelopeASR(t, duration, 0.001, 0.01)
    if e == 0: return 0
    return 0.040 * e * math.sin(
        t * angularVelocityByNoteNumber(nn) +
        2.0 * math.sin(t * angularVelocityByNoteNumber(nn))
    )

def toneCymbal(t, nn, duration):
    e = envelopeAR(t, 0.0005, 1)
    if e == 0: return 0
    n = 8
    d = 0
    for j in range(n):
        d += 0.080 / n * \
            math.sin(440 * math.pow(2, 2.9) * (1 + 1.5 * j / n) * 2 * math.pi * (
                t + 0.0002 * math.sin((50 + 10 * (j / n)) * 2 * math.pi * t)
            ))
    return d * math.pow(e, 4)

def toneHihat(t, nn, duration):
    e = envelopeAR(t, 0.0005, 0.05)
    n = 8
    d = 0
    for j in range(n):
        d += 0.060 / n * \
            math.sin(440 * math.pow(2, 3.2) * (1 + 1.5 * j / n) * 2 * math.pi * (
                t + 0.0002 * math.sin((50 + 10 * (j / n)) * 2 * math.pi * t)
            ))
    return d * e

def toneBassDrum(t, nn, duration):
    e = envelopeAR(t, 0, 0.4)
    if e == 0: return 0
    d = 0.25 * math.sin(
        t * 40 * 2 * math.pi +
        t * 120 * 2 * math.pi * math.pow(max(0, 1 - (t / 0.4)), 2) +
        0.5 * math.sin(t * 40 * 2 * math.pi)
    )
    return d * math.pow(e, 2)

def note(t, toneFunc, beat, gateBeat, number):
    btd = beatTimeDelta()
    timeBeat = beatFromTime(t)
    margin = 4
    if timeBeat < beat or beat + gateBeat + margin < timeBeat: return 0
    return toneFunc(t - timeFromBeat(beat), number, gateBeat * btd)

def notes(t, toneFunc, startBeat, params):
    d = 0
    beat = startBeat
    for param in params:
        noteStr = param[0]
        gateBeat = param[1]
        stepBeat = param[2] if len(param) >= 3 else gateBeat
        d += note(t, toneFunc, beat, gateBeat, noteNumberFromString(noteStr))
        beat += stepBeat
    return d

def sample(t):
    d = 0
    b = beatFromTime(t)
    beat = 0;
    block_beats = 1 * 4
    if b < beat + block_beats:
        d += notes(t, tonePiano, beat + 0.5, [
            ["5b-", 0.25, 0], ["6d", 0.25, 0], ["6a", 0.25],
            ["5b-", 0.25, 0], ["6d", 0.25, 0], ["6a", 0.25],
            ["5b-", 0.25, 0], ["6d", 0.25, 0], ["6a", 0.25],
            ["5b-", 0.25, 0], ["6d", 0.25, 0], ["6a", 0.25, 0.25 + 0.5],
            ["5b-", 0.25, 0], ["6d", 0.25, 0], ["6a", 0.25],
        ])
        d += notes(t, tonePiano, beat + 2.5, [
            ["4g", 0.5],
            ["5f", 0.5],
            ["5c", 0.5],
        ])
        return d
    beat += block_beats
    block_beats = 4 * 4
    if b < beat + block_beats:
        d += notes(t, tonePiano, beat, [
            ["5d", 2, 2 + 0.5],
            ["4b-", 0.5],
            ["5c", 0.5],
            ["5d", 0.5 + 0.75], ["5c", 0.75], ["4b-", 0.5],
            ["4a", 0.75], ["4b-", 0.75], ["5c", 0.5],
        ])
        d += notes(t, tonePiano, beat, [
            ["2g", 0.5], ["3g", 0.25], ["3g", 0.25],
            ["2g", 0.5], ["3g", 0.25], ["3g", 0.25],
            ["2g", 0.5], ["3g", 0.25], ["3g", 0.25],
            ["2g", 0.5], ["3g", 0.25], ["3g", 0.25],
            ["2e-", 0.5], ["3e-", 0.25], ["3e-", 0.25],
            ["2e-", 0.5], ["3e-", 0.25], ["3e-", 0.25],
            ["2f", 0.5], ["3f", 0.25], ["3f", 0.25],
            ["2f", 0.5], ["3f", 0.25], ["3f", 0.25],
        ])
        d += notes(t, toneBassDrum, beat, [
            ["4c", 1], ["4c", 1], ["4c", 1], ["4c", 1],
            ["4c", 1], ["4c", 1], ["4c", 1], ["4c", 1],
            ["4c", 1], ["4c", 1], ["4c", 1], ["4c", 1],
            ["4c", 1], ["4c", 1], ["4c", 1], ["4c", 1],
        ])
        d += notes(t, toneHihat, beat, [
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
            ["4c", 0.25], ["4c", 0.25], ["4c", 0.5],
        ])
        return d
    return d

sample_rate = 44100.0
duration = 8.0
wavef = wave.open("music.wav", "w")
wavef.setnchannels(1)
wavef.setsampwidth(2) 
wavef.setframerate(sample_rate)
for i in range(int(duration * sample_rate)):
    data = struct.pack("<h", int(32767 * sample(i / sample_rate)))
    wavef.writeframesraw( data )
wavef.close()

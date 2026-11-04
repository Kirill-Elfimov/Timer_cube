from pyTwistyScrambler import (scrambler333, scrambler222, scrambler444, scrambler555,
                               scrambler666, scrambler777, pyraminxScrambler, megaminxScrambler,
                               squareOneScrambler, skewbScrambler, clockScrambler, ftoScrambler)

def scramble_333():
    scramble = scrambler333.get_WCA_scramble()
    return scramble

def scramble_222():
    scramble = scrambler222.get_WCA_scramble()
    return scramble

def scramble_444():
    scramble = scrambler444.get_WCA_scramble()
    return scramble

def scramble_555():
    scramble = scrambler555.get_WCA_scramble()
    return scramble

def scramble_666():
    scramble = scrambler666.get_WCA_scramble()
    return scramble

def scramble_777():
    scramble = scrambler777.get_WCA_scramble()
    return scramble

def scramble_pyraminx():
    scramble = pyraminxScrambler.get_WCA_scramble()
    return scramble

def scramble_megaminx():
    scramble = megaminxScrambler.get_WCA_scramble()
    return scramble

def scramble_squareOne():
    scramble = squareOneScrambler.get_WCA_scramble()
    return scramble

def scramble_skewb():
    scramble = skewbScrambler.get_WCA_scramble()
    return scramble

def scramble_clock():
    scramble = clockScrambler.get_WCA_scramble()
    return scramble

def scramble_fto():
    scramble = ftoScrambler.get_random_state_scramble()
    return scramble
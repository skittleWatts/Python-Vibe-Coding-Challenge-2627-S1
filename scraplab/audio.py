"""Quiet, optional procedural tones. No files or sound device are required."""
from array import array
import math
import pygame as pg


class Audio:
    def __init__(self):
        self.enabled = False
        self.available = True
        self.sounds = {}

    def enable(self, enabled):
        if enabled and not self.sounds:
            try:
                pg.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
                for name, frequencies, duration in [("click", (650,), .045), ("impact", (85, 133), .08), ("success", (523, 659, 784), .33), ("finish", (294, 220), .24)]:
                    samples = array("h")
                    length = round(22050*duration)
                    for i in range(length):
                        phase = i/length
                        freq = frequencies[min(len(frequencies)-1, int(phase*len(frequencies)))]
                        envelope = min(1, phase*30)*(1-phase)**2
                        samples.append(round(4000*envelope*math.sin(math.tau*freq*i/22050)))
                    self.sounds[name] = pg.mixer.Sound(buffer=samples)
            except (pg.error, OSError):
                self.available = False
                enabled = False
        self.enabled = enabled and self.available
        return self.enabled

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

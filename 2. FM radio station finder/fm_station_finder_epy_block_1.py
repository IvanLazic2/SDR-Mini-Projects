import numpy as np
from gnuradio import gr
import pmt

from collections import Counter

class station_handler(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self,
            name="station_handler",
            in_sig=None,
            out_sig=None)

        self.message_port_register_in(pmt.intern("stations_in"))
        self.set_msg_handler(pmt.intern("stations_in"), self.handle_stations)

        self.message_port_register_in(pmt.intern("cmd_in"))
        self.set_msg_handler(pmt.intern("cmd_in"), self.handle_command)

        self.stations = []
        self.last_stations = []
        self.current_index = 0

        self.current_freq = 0
        self.last_freq = 0

        self.message_port_register_out(pmt.intern("freq_out"))


    def handle_stations(self, msg):
        if pmt.is_f32vector(msg):
            freqs = sorted(set(pmt.to_python(msg)))
        else:
            return

        if not freqs:
            return

        self.last_freq = self.current_freq
        self.current_freq = self.stations[self.current_index] if self.stations else None

        self.last_stations = self.stations
        self.stations = freqs

        if Counter(self.last_stations) == Counter(self.stations):
            return

        if self.last_freq == self.current_freq:
            return

        if self.current_freq in self.stations:
            self.current_index = self.stations.index(self.current_freq)
        
        if self.current_index >= len(self.stations):
            return
        
        self.set_freq(self.stations[self.current_index])


    def handle_command(self, msg):
        if pmt.is_pair(msg):
            key = pmt.symbol_to_string(pmt.car(msg))
            val = pmt.cdr(msg)

            if key == "cmd":
                if pmt.is_symbol(val):
                    cmd = pmt.symbol_to_string(val)
                elif pmt.is_string(val):
                    cmd = pmt.to_python(val)
                else:
                    return

                if cmd == "next":
                    self.step_next()
                elif cmd == "prev":
                    self.step_prev()


    def step_next(self):
        if not self.stations:
            return
        self.current_index = (self.current_index + 1) % len(self.stations)
        self.set_freq(self.stations[self.current_index])

    def step_prev(self):
        if not self.stations:
            return
        self.current_index = (self.current_index - 1) % len(self.stations)
        self.set_freq(self.stations[self.current_index])


    def set_freq(self, freq):
        msg = pmt.cons(pmt.intern("freq"), pmt.from_double(freq))
        self.message_port_pub(pmt.intern("freq_out"), msg)
        print(f"Station {self.current_index + 1}/{len(self.stations)}: {freq / .1e7} MHz")

    def get_freq(self):
        return self.current_freq



import numpy as np
from scipy.signal import find_peaks
from gnuradio import gr
import pmt 

from collections import Counter

class StationFinder(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="station_finder",
            in_sig=[(np.float32, 1024)],
            out_sig=[]
        )

        self.fft_size = 1024
        self.samp_rate = 20e6
        self.center_freq = 98e6
        self.frames_per_scan = 20000  # 1 sec at 20k vectors/sec
        self.accumulator = np.zeros(self.fft_size, dtype=np.float64)
        self.frame_count = 0

        self.station_freqs = []
        self.last_station_freqs = []

        self.message_port_register_out(pmt.intern("stations_out"))

    def work(self, input_items, output_items):
        in0 = input_items[0]
        n = len(in0)

        for i in range(n):
            self.accumulator += in0[i]
            self.frame_count += 1

            if self.frame_count >= self.frames_per_scan:
                avg_spectrum = self.accumulator / self.frames_per_scan
                self.accumulator[:] = 0
                self.frame_count = 0

                center_bin = self.fft_size // 2
                avg_spectrum[center_bin-2:center_bin+3] = 0

                norm_spectrum = avg_spectrum / np.max(avg_spectrum)

                peaks, _ = find_peaks(
                    norm_spectrum,
                    #    P_dB = 10 * log10(P_linear)
                    # => P_linear = 10 ** (p_dB / 10)
                    # Noise: -71dB
                    # Weak: -67dB => 4dB above noise
                    # Strong: -49dB
                    prominence=0.05, # 0.07
                    distance=10
                )

                if len(peaks) > 0:
                    freqs = np.linspace(
                        self.center_freq - self.samp_rate / 2,
                        self.center_freq + self.samp_rate / 2,
                        self.fft_size
                    )
                    peak_freqs = freqs[peaks]
                    peak_freqs_khz = np.round(peak_freqs / 1000) * 1000

                    self.last_station_freqs = self.station_freqs
                    self.station_freqs = np.unique(peak_freqs_khz.astype(np.float32))

                    if Counter(self.last_station_freqs) == Counter(self.station_freqs):
                        break

                    self.station_freqs = np.sort(self.station_freqs)

                    # Send as PMT f32vector
                    pmt_msg = pmt.init_f32vector(len(self.station_freqs), self.station_freqs)
                    self.message_port_pub(pmt.intern("stations_out"), pmt_msg)

        return n
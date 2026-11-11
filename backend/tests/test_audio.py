import struct

import pytest

from mesa_voice.audio import AudioError, RATE, decode_wav, encode_wav, resample_piper


def test_canonical_roundtrip_and_maximum():
    pcm = struct.pack("<h", -1234) * (RATE * 8)
    assert decode_wav(encode_wav(pcm)) == pcm
    assert len(encode_wav(pcm)) == 256044


@pytest.mark.parametrize("mutate", [
    lambda x: x[:-1],
    lambda x: x + b"00",
    lambda x: b"RIFX" + x[4:],
    lambda x: x[:22] + b"\x02\x00" + x[24:],
    lambda x: x[:24] + struct.pack("<I", 48000) + x[28:],
    lambda x: x[:40] + struct.pack("<I", 0) + x[44:],
])
def test_rejects_corrupt_format_and_lengths(mutate):
    with pytest.raises(AudioError):
        decode_wav(mutate(encode_wav(b"\0\0" * RATE)))


@pytest.mark.parametrize("samples", [0, 1599, RATE * 8 + 1])
def test_rejects_input_duration(samples):
    with pytest.raises(AudioError):
        decode_wav(encode_wav(b"\0\0" * samples))


def test_resample_rate_length_gain_fade_and_bound():
    import numpy as np
    source = np.full(22050, 20000, dtype="<i2").tobytes()
    pcm = decode_wav(resample_piper(source, 22050))
    values = np.frombuffer(pcm, dtype="<i2")
    assert len(values) == RATE
    assert values[0] == values[-1] == 0
    assert 12900 < values[RATE // 2] < 13100
    long_pcm = np.zeros(22050 * 21, dtype="<i2").tobytes()
    assert len(decode_wav(resample_piper(long_pcm, 22050), maximum_seconds=20)) == RATE * 20 * 2


def test_downsampling_filters_ultrasonic_alias():
    import numpy as np
    # 12 kHz input must not alias to an audible 4 kHz output after 48->16 kHz.
    t = np.arange(48000) / 48000
    source = (15000 * np.sin(2 * np.pi * 12000 * t)).astype("<i2").tobytes()
    out = np.frombuffer(decode_wav(resample_piper(source, 48000)), dtype="<i2")
    assert np.sqrt(np.mean(out[100:-100].astype(float) ** 2)) < 30

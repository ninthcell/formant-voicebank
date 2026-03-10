"""Core additive formant synthesis engine.

Voice character: Breathy/Airy (subtle)
- 88% sine harmonics + 12% formant-filtered noise
- Steeper harmonic rolloff (1/n^1.5)
- Slightly wider formant bandwidths
- Gentle attack envelopes
"""

import math
import random
import struct
import wave

from .phonemes import ConsonantParams, FormantSet, GLIDE_FORMANTS, VOWELS

SAMPLE_RATE = 44100
F0 = 277.183  # C#4 base pitch
BREATHINESS = 0.12  # reduced from 0.3 — subtle air, not noise
MAX_HARMONICS = 40


def _lorentzian(freq: float, center: float, bandwidth: float) -> float:
    """Lorentzian resonance peak."""
    half_bw = bandwidth / 2.0
    return (half_bw * half_bw) / ((freq - center) ** 2 + half_bw * half_bw)


def formant_amplitude(freq: float, formants: FormantSet) -> float:
    """Compute amplitude at a given frequency from formant resonance peaks."""
    a = _lorentzian(freq, formants.f1, formants.bw1)
    b = _lorentzian(freq, formants.f2, formants.bw2)
    c = _lorentzian(freq, formants.f3, formants.bw3)
    return a + b * 0.7 + c * 0.4


def synthesize_voiced(formants: FormantSet, duration_s: float,
                      f0: float = F0, breathiness: float = BREATHINESS) -> list[float]:
    """Synthesize a voiced sound: sine harmonics + noise, shaped by formants."""
    n_samples = int(duration_s * SAMPLE_RATE)
    if n_samples == 0:
        return []
    samples = [0.0] * n_samples

    # Pre-compute harmonic amplitudes
    harmonic_amps = []
    for n in range(1, MAX_HARMONICS + 1):
        freq = f0 * n
        if freq > SAMPLE_RATE / 2:
            break
        rolloff = 1.0 / (n ** 1.5)
        formant_gain = formant_amplitude(freq, formants)
        harmonic_amps.append((n, freq, rolloff * formant_gain))

    # Generate harmonics
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        val = 0.0
        for n, freq, amp in harmonic_amps:
            val += amp * math.sin(2.0 * math.pi * freq * t)
        samples[i] = val

    # Normalize harmonic part
    peak = max(abs(s) for s in samples) or 1.0
    for i in range(n_samples):
        samples[i] /= peak

    # Generate formant-filtered noise (with unique seed per formant set)
    noise = _formant_filtered_noise(formants, n_samples)

    # Blend
    harm_weight = 1.0 - breathiness
    for i in range(n_samples):
        samples[i] = harm_weight * samples[i] + breathiness * noise[i]

    return samples


def synthesize_noise_only(formants: FormantSet, duration_s: float) -> list[float]:
    """Synthesize pure noise shaped by formant envelope (for whisper/breath)."""
    n_samples = int(duration_s * SAMPLE_RATE)
    return _formant_filtered_noise(formants, n_samples)


def _formant_filtered_noise(formants: FormantSet, n_samples: int) -> list[float]:
    """Generate noise filtered through formant resonance."""
    if n_samples == 0:
        return []
    result = [0.0] * n_samples

    for idx, (center, bw) in enumerate([(formants.f1, formants.bw1),
                                         (formants.f2, formants.bw2),
                                         (formants.f3, formants.bw3)]):
        # Each resonator gets a different seed for uncorrelated noise
        seed = int(center * 100 + bw * 10 + idx * 7)
        filtered = _bandpass_filter_noise(center, bw, n_samples, seed)
        gain = [1.0, 0.7, 0.4][idx]
        for i in range(n_samples):
            result[i] += filtered[i] * gain

    peak = max(abs(s) for s in result) or 1.0
    for i in range(n_samples):
        result[i] /= peak

    return result


def _bandpass_filter_noise(center_freq: float, bandwidth: float,
                           n_samples: int, seed: int = 42) -> list[float]:
    """2nd-order IIR bandpass filter on white noise. Fixed Q-factor formula."""
    if n_samples == 0 or center_freq <= 0:
        return [0.0] * n_samples

    w0 = 2.0 * math.pi * center_freq / SAMPLE_RATE
    sin_w0 = math.sin(w0)
    if abs(sin_w0) < 1e-10:
        return [0.0] * n_samples

    # Correct Q-factor calculation: Q = center / bandwidth
    Q = center_freq / max(bandwidth, 1.0)
    alpha = sin_w0 / (2.0 * Q)

    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * math.cos(w0)
    a2 = 1.0 - alpha

    b0 /= a0; b1 /= a0; b2 /= a0
    a1 /= a0; a2 /= a0

    output = [0.0] * n_samples
    x1 = x2 = y1 = y2 = 0.0

    rng = random.Random(seed)
    for i in range(n_samples):
        x0 = rng.gauss(0, 1)
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        output[i] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0

    return output


def apply_envelope(samples: list[float], attack_ms: float = 20.0,
                   decay_ms: float = 10.0, sustain: float = 0.85,
                   release_ms: float = 30.0) -> list[float]:
    """Apply ADSR envelope."""
    n = len(samples)
    if n == 0:
        return []
    attack_samples = int(attack_ms * SAMPLE_RATE / 1000)
    decay_samples = int(decay_ms * SAMPLE_RATE / 1000)
    release_samples = int(release_ms * SAMPLE_RATE / 1000)
    sustain_samples = max(0, n - attack_samples - decay_samples - release_samples)

    result = list(samples)
    idx = 0

    for i in range(min(attack_samples, n)):
        t = i / max(attack_samples, 1)
        result[idx] *= 0.5 * (1.0 - math.cos(math.pi * t))
        idx += 1

    for i in range(min(decay_samples, n - idx)):
        t = i / max(decay_samples, 1)
        result[idx] *= 1.0 - (1.0 - sustain) * t
        idx += 1

    for i in range(min(sustain_samples, n - idx)):
        result[idx] *= sustain
        idx += 1

    for i in range(min(release_samples, n - idx)):
        t = i / max(release_samples, 1)
        result[idx] *= sustain * 0.5 * (1.0 + math.cos(math.pi * t))
        idx += 1

    while idx < n:
        result[idx] = 0.0
        idx += 1

    return result


def synthesize_consonant_burst(params: ConsonantParams, duration_s: float) -> list[float]:
    """Synthesize consonant portion with clear frequency differentiation."""
    n_samples = int(duration_s * SAMPLE_RATE)
    if n_samples == 0:
        return []
    samples = [0.0] * n_samples

    if params.ctype == 'plosive':
        # Silence gap then gentle burst
        burst_samples = int(params.burst_dur_ms * SAMPLE_RATE / 1000)
        silence_samples = max(0, n_samples - burst_samples)

        center = (params.noise_freq_low + params.noise_freq_high) / 2
        bw = params.noise_freq_high - params.noise_freq_low
        if bw > 0 and burst_samples > 0:
            seed = int(center + params.noise_freq_low * 3)
            burst = _bandpass_filter_noise(center, max(bw, 200), burst_samples, seed)
            # Smooth cosine attack (30% of burst) + gentle decay
            for i in range(burst_samples):
                ramp = min(1.0, i / max(burst_samples * 0.3, 1))
                attack_env = 0.5 * (1.0 - math.cos(math.pi * ramp))
                decay_env = max(0.0, 1.0 - (i / burst_samples) * 0.4)
                if silence_samples + i < n_samples:
                    samples[silence_samples + i] = burst[i] * attack_env * decay_env * 0.7

        if params.voiced:
            buzz = _generate_buzz(n_samples, F0, 0.4)
            for i in range(n_samples):
                samples[i] = samples[i] * 0.5 + buzz[i] * 0.5

    elif params.ctype in ('fricative', 'affricate'):
        center = (params.noise_freq_low + params.noise_freq_high) / 2
        bw = params.noise_freq_high - params.noise_freq_low
        seed = int(center * 7 + bw)
        filtered = _bandpass_filter_noise(center, max(bw, 200), n_samples, seed)

        # Slow cosine ramp-in (25% of duration) for smoother onset
        for i in range(n_samples):
            ramp = min(1.0, i / max(n_samples * 0.25, 1))
            attack_t = 0.5 * (1.0 - math.cos(math.pi * ramp))
            samples[i] = filtered[i] * attack_t

        if params.ctype == 'affricate':
            # Mild emphasis on initial burst
            burst_len = int(8 * SAMPLE_RATE / 1000)
            for i in range(min(burst_len, n_samples)):
                samples[i] *= 1.3

        if params.voiced:
            buzz = _generate_buzz(n_samples, F0, 0.35)
            for i in range(n_samples):
                samples[i] = samples[i] * 0.55 + buzz[i] * 0.45

    elif params.ctype == 'nasal':
        nasal_formants = FormantSet(
            f1=250, f2=1400, f3=2500,
            bw1=100, bw2=150, bw3=200  # narrower for clearer nasal
        )
        samples = synthesize_voiced(nasal_formants, duration_s, breathiness=0.08)

    elif params.ctype == 'liquid':
        tap_formants = FormantSet(f1=400, f2=1600, f3=2600, bw1=120, bw2=150, bw3=200)
        samples = synthesize_voiced(tap_formants, duration_s, breathiness=0.1)
        tap_len = int(params.burst_dur_ms * SAMPLE_RATE / 1000)
        for i in range(min(tap_len, len(samples))):
            t = i / max(tap_len, 1)
            samples[i] *= t

    elif params.ctype == 'glide':
        pass

    if samples:
        peak = max(abs(s) for s in samples) or 1.0
        for i in range(len(samples)):
            samples[i] /= peak

    return samples


def _generate_buzz(n_samples: int, f0: float, amplitude: float) -> list[float]:
    """Generate voiced buzz (sum of first 8 harmonics for richer voicing)."""
    if n_samples == 0:
        return []
    result = [0.0] * n_samples
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        for n in range(1, 9):
            result[i] += math.sin(2 * math.pi * f0 * n * t) / (n ** 1.2)
    peak = max(abs(s) for s in result) or 1.0
    for i in range(n_samples):
        result[i] = result[i] / peak * amplitude
    return result


def synthesize_cv(consonant: ConsonantParams, vowel: FormantSet,
                  total_duration_s: float, is_whisper: bool = False) -> list[float]:
    """Synthesize consonant-vowel with clear consonant onset."""
    cons_dur = consonant.burst_dur_ms / 1000.0
    trans_dur = consonant.transition_ms / 1000.0

    if consonant.ctype == 'glide':
        cons_dur = 0.0
        trans_dur = min(trans_dur, total_duration_s * 0.4)

    # Give consonant more time for clarity
    if consonant.ctype in ('fricative', 'affricate'):
        cons_dur = max(cons_dur, 0.06)  # at least 60ms for friction
    elif consonant.ctype == 'plosive':
        cons_dur = max(cons_dur, 0.02)  # at least 20ms for burst

    vowel_dur = max(0.05, total_duration_s - cons_dur - trans_dur)

    # Generate consonant
    cons_samples = synthesize_consonant_burst(consonant, cons_dur) if cons_dur > 0 else []

    # Generate transition
    if consonant.ctype == 'glide' and consonant.voiced:
        cons_key = 'y' if consonant.transition_ms == 60 and consonant.noise_freq_low == 0 else 'w'
        glide_start = GLIDE_FORMANTS.get(cons_key, GLIDE_FORMANTS['y'])
        trans_samples = _interpolate_formants(glide_start, vowel, trans_dur, is_whisper)
    elif consonant.ctype == 'nasal':
        # Nasal → vowel: start from nasal formants
        nasal_start = FormantSet(
            f1=250, f2=1400, f3=2500, bw1=100, bw2=150, bw3=200
        )
        trans_samples = _interpolate_formants(nasal_start, vowel, trans_dur, is_whisper)
    elif consonant.ctype == 'liquid':
        tap_start = FormantSet(f1=400, f2=1600, f3=2600, bw1=120, bw2=150, bw3=200)
        trans_samples = _interpolate_formants(tap_start, vowel, trans_dur, is_whisper)
    else:
        # For plosives/fricatives: transition from a locus near consonant place
        # Use different F2 locus by consonant frequency range
        f2_locus = (params_noise_center(consonant) * 0.3 + vowel.f2 * 0.7)
        mid_formants = FormantSet(
            f1=vowel.f1 * 0.6 + 300 * 0.4,
            f2=f2_locus,
            f3=vowel.f3,
            bw1=vowel.bw1 * 1.5,
            bw2=vowel.bw2 * 1.3,
            bw3=vowel.bw3,
        )
        trans_samples = _interpolate_formants(mid_formants, vowel, trans_dur, is_whisper)

    # Generate vowel steady state
    if is_whisper:
        vowel_samples = synthesize_noise_only(vowel, vowel_dur)
    else:
        vowel_samples = synthesize_voiced(vowel, vowel_dur)

    # Concatenate with wide crossfades for smooth joins
    result = cons_samples + trans_samples + vowel_samples
    if cons_samples:
        _crossfade(result, len(cons_samples), 8)
    _crossfade(result, len(cons_samples) + len(trans_samples), 10)

    return result


def params_noise_center(params: ConsonantParams) -> float:
    """Get the center noise frequency of a consonant."""
    return (params.noise_freq_low + params.noise_freq_high) / 2


def synthesize_vowel_transition(v1: FormantSet, v2: FormantSet,
                                 duration_s: float, is_whisper: bool = False) -> list[float]:
    """Synthesize a vowel-to-vowel transition."""
    return _interpolate_formants(v1, v2, duration_s, is_whisper)


def _interpolate_formants(start: FormantSet, end: FormantSet,
                          duration_s: float, is_whisper: bool = False) -> list[float]:
    """Smoothly interpolate between two formant sets with continuous phase.

    Voiced mode maintains phase accumulators across the entire duration to
    prevent buzzing artifacts from phase discontinuities at chunk boundaries.
    """
    n_samples = int(duration_s * SAMPLE_RATE)
    if n_samples == 0:
        return []

    chunk_size = max(1, SAMPLE_RATE // 100)  # 10ms formant update rate

    if is_whisper:
        # Noise-based: no phase continuity needed, chunk approach is fine
        result = []
        for start_idx in range(0, n_samples, chunk_size):
            end_idx = min(start_idx + chunk_size, n_samples)
            chunk_len = end_idx - start_idx
            t = start_idx / max(n_samples - 1, 1)
            t_smooth = 0.5 * (1.0 - math.cos(math.pi * t))
            current = FormantSet(
                f1=start.f1 + (end.f1 - start.f1) * t_smooth,
                f2=start.f2 + (end.f2 - start.f2) * t_smooth,
                f3=start.f3 + (end.f3 - start.f3) * t_smooth,
                bw1=start.bw1 + (end.bw1 - start.bw1) * t_smooth,
                bw2=start.bw2 + (end.bw2 - start.bw2) * t_smooth,
                bw3=start.bw3 + (end.bw3 - start.bw3) * t_smooth,
            )
            chunk = synthesize_noise_only(current, chunk_len / SAMPLE_RATE)
            result.extend(chunk[:chunk_len])
        return result[:n_samples]

    # Voiced mode: continuous phase across all chunks
    # Determine which harmonics are in audible range
    harmonic_info = []
    for h in range(1, MAX_HARMONICS + 1):
        freq = F0 * h
        if freq > SAMPLE_RATE / 2:
            break
        phase_inc = 2.0 * math.pi * freq / SAMPLE_RATE
        rolloff = 1.0 / (h ** 1.5)
        harmonic_info.append((h, freq, phase_inc, rolloff))

    # Phase accumulators — persist across all chunks
    phases = [0.0] * len(harmonic_info)
    result = []

    for chunk_start in range(0, n_samples, chunk_size):
        chunk_end = min(chunk_start + chunk_size, n_samples)
        chunk_len = chunk_end - chunk_start

        # Update formants for this chunk
        t = chunk_start / max(n_samples - 1, 1)
        t_smooth = 0.5 * (1.0 - math.cos(math.pi * t))
        cur_f1 = start.f1 + (end.f1 - start.f1) * t_smooth
        cur_f2 = start.f2 + (end.f2 - start.f2) * t_smooth
        cur_f3 = start.f3 + (end.f3 - start.f3) * t_smooth
        cur_bw1 = start.bw1 + (end.bw1 - start.bw1) * t_smooth
        cur_bw2 = start.bw2 + (end.bw2 - start.bw2) * t_smooth
        cur_bw3 = start.bw3 + (end.bw3 - start.bw3) * t_smooth

        # Pre-compute harmonic amplitudes for this chunk's formants
        amps = []
        for idx, (h, freq, _, rolloff) in enumerate(harmonic_info):
            half1 = cur_bw1 / 2.0
            a = (half1 * half1) / ((freq - cur_f1) ** 2 + half1 * half1)
            half2 = cur_bw2 / 2.0
            b = (half2 * half2) / ((freq - cur_f2) ** 2 + half2 * half2)
            half3 = cur_bw3 / 2.0
            c = (half3 * half3) / ((freq - cur_f3) ** 2 + half3 * half3)
            gain = a + b * 0.7 + c * 0.4
            amps.append(rolloff * gain)

        # Generate samples with continuous phase
        for j in range(chunk_len):
            val = 0.0
            for idx in range(len(harmonic_info)):
                phases[idx] += harmonic_info[idx][2]  # phase_inc
                val += amps[idx] * math.sin(phases[idx])
            result.append(val)

    result = result[:n_samples]

    # Normalize harmonic part
    peak = max(abs(s) for s in result) or 1.0
    for i in range(len(result)):
        result[i] /= peak

    # Blend breathiness noise (using midpoint formants)
    mid = FormantSet(
        f1=(start.f1 + end.f1) / 2, f2=(start.f2 + end.f2) / 2,
        f3=(start.f3 + end.f3) / 2, bw1=(start.bw1 + end.bw1) / 2,
        bw2=(start.bw2 + end.bw2) / 2, bw3=(start.bw3 + end.bw3) / 2,
    )
    noise = _formant_filtered_noise(mid, n_samples)
    harm_weight = 1.0 - BREATHINESS
    for i in range(len(result)):
        result[i] = harm_weight * result[i] + BREATHINESS * noise[i]

    return result


def _crossfade(samples: list[float], boundary: int, ms: float = 5.0) -> None:
    """Apply crossfade around a boundary point in-place."""
    fade_samples = int(ms * SAMPLE_RATE / 1000)
    half = fade_samples // 2

    start = max(0, boundary - half)
    end = min(len(samples), boundary + half)
    span = max(end - start - 1, 1)

    for i in range(start, end):
        t = (i - start) / span
        factor = 0.5 * (1.0 - math.cos(math.pi * t))
        if i < boundary:
            samples[i] *= 0.7 + 0.3 * factor
        else:
            samples[i] *= 0.3 + 0.7 * factor


def synthesize_breath(duration_s: float) -> list[float]:
    """Synthesize a breath sound: wide-band filtered noise."""
    breath_formants = FormantSet(
        f1=400, f2=1500, f3=3000,
        bw1=400, bw2=500, bw3=600
    )
    samples = synthesize_noise_only(breath_formants, duration_s)
    return apply_envelope(samples, attack_ms=50, decay_ms=20, sustain=0.6, release_ms=80)


def normalize_and_convert(samples: list[float], target_peak: float = 0.85) -> bytes:
    """Normalize to target peak and convert to 16-bit PCM bytes.

    Applies a short safety fade at both ends to guarantee zero-crossing
    and prevent clicks/pops at sample boundaries.
    """
    if not samples:
        return b''

    n = len(samples)
    peak = max(abs(s) for s in samples) or 1.0
    scale = target_peak / peak

    # Safety fade: 3ms cosine fade-in/out to guarantee zero at boundaries
    fade_samples = min(int(0.003 * SAMPLE_RATE), n // 2)  # 3ms = ~132 samples

    result = bytearray()
    for i, s in enumerate(samples):
        val = s * scale

        # Fade-in at start
        if i < fade_samples:
            t = i / max(fade_samples, 1)
            val *= 0.5 * (1.0 - math.cos(math.pi * t))

        # Fade-out at end
        elif i >= n - fade_samples:
            t = (n - 1 - i) / max(fade_samples, 1)
            val *= 0.5 * (1.0 - math.cos(math.pi * t))

        ival = int(val * 32767)
        ival = max(-32768, min(32767, ival))
        result.extend(struct.pack('<h', ival))
    return bytes(result)


def write_wav(filepath: str, samples: list[float]) -> None:
    """Write samples to a WAV file (16-bit, 44100 Hz, mono)."""
    pcm_data = normalize_and_convert(samples)
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)

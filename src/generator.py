"""Sample generation orchestrator.

Maps each oto.ini entry to the appropriate synthesis function.
"""

import os
import sys

from .oto_parser import OtoEntry
from .phonemes import (
    VOWELS, VOWEL_TRANSITIONS, VCV_TRANSITIONS, ROMAJI_MAP,
    parse_kana_name, FormantSet,
)
from .synth import (
    synthesize_voiced, synthesize_noise_only, synthesize_cv,
    synthesize_vowel_transition, synthesize_consonant_burst,
    synthesize_breath, apply_envelope, write_wav,
)


def _estimate_duration(entry: OtoEntry, default_ms: float = 600.0) -> float:
    """Estimate the needed WAV duration in seconds from oto.ini parameters."""
    # The WAV needs to be long enough to cover offset + consonant + some vowel + cutoff margin
    needed_ms = entry.offset + entry.consonant + 200  # 200ms vowel minimum
    if entry.cutoff > 0:
        needed_ms += entry.cutoff
    needed_ms = max(needed_ms, default_ms)
    # Cap at reasonable length
    needed_ms = min(needed_ms, 1500.0)
    return needed_ms / 1000.0


def generate_sample(entry: OtoEntry) -> list[float] | None:
    """Generate audio samples for a single oto.ini entry.

    Returns float samples, or None if entry can't be synthesized.
    """
    fname = entry.filename
    base = fname.replace('.wav', '')

    # Check for breath entries
    if '息' in base:
        duration = _estimate_duration(entry, 400.0)
        return synthesize_breath(duration)

    # Check for romaji entries
    if base in ROMAJI_MAP:
        return _generate_romaji(base, entry)

    # Check for vowel transitions (あい, あう, etc.)
    if base in VOWEL_TRANSITIONS:
        v1_key, v2_key = VOWEL_TRANSITIONS[base]
        v1 = VOWELS[v1_key]
        v2 = VOWELS[v2_key]
        duration = _estimate_duration(entry)
        samples = synthesize_vowel_transition(v1, v2, duration)
        return apply_envelope(samples, attack_ms=15, release_ms=25)

    # Check for あいうえお (special 5-vowel sequence)
    if base == 'あいうえお':
        return _generate_aiueo(entry)

    # Parse kana name
    info = parse_kana_name(base)

    duration = _estimate_duration(entry)

    # Pure vowel (no consonant)
    if info.consonant is None and info.vowel is not None:
        if info.is_whisper:
            samples = synthesize_noise_only(info.vowel, duration)
        elif info.is_voiced_variant:
            # Voiced variant: more buzz, less breathiness
            samples = synthesize_voiced(info.vowel, duration, breathiness=0.15)
        else:
            samples = synthesize_voiced(info.vowel, duration)
        return apply_envelope(samples, attack_ms=15, release_ms=25)

    # Consonant + vowel
    if info.consonant is not None and info.vowel is not None:
        samples = synthesize_cv(info.consonant, info.vowel, duration, info.is_whisper)
        if info.is_voiced_variant and not info.consonant.voiced:
            # Add voicing buzz to normally unvoiced consonant
            _add_voicing(samples, duration)
        return apply_envelope(samples, attack_ms=10, release_ms=25)

    # Consonant only (子音)
    if info.consonant is not None and info.vowel is None:
        cons_dur = max(info.consonant.burst_dur_ms * 2, 80) / 1000.0
        total_dur = max(cons_dur, duration * 0.4)
        samples = synthesize_consonant_burst(info.consonant, total_dur)
        return apply_envelope(samples, attack_ms=5, decay_ms=10, sustain=0.7, release_ms=20)

    # Fallback: generate a generic vowel /a/
    samples = synthesize_voiced(VOWELS['a'], duration)
    return apply_envelope(samples)


def _generate_romaji(name: str, entry: OtoEntry) -> list[float]:
    """Generate samples for romaji-named entries (b.wav, k.wav, etc.)."""
    from .phonemes import CONSONANTS
    cons_key, vowel_key = ROMAJI_MAP[name]
    duration = _estimate_duration(entry, 400.0)

    if cons_key and vowel_key:
        # CV like 'ce', 'zi'
        cons = CONSONANTS[cons_key]
        vowel = VOWELS[vowel_key]
        samples = synthesize_cv(cons, vowel, duration)
    elif cons_key and not vowel_key:
        # Consonant only
        cons = CONSONANTS[cons_key]
        cons_dur = max(cons.burst_dur_ms * 2, 80) / 1000.0
        samples = synthesize_consonant_burst(cons, max(cons_dur, duration * 0.4))
    elif vowel_key:
        # Pure vowel
        vowel = VOWELS[vowel_key]
        samples = synthesize_voiced(vowel, duration)
    else:
        samples = synthesize_voiced(VOWELS['a'], duration)

    return apply_envelope(samples, attack_ms=10, release_ms=20)


def _generate_aiueo(entry: OtoEntry) -> list[float]:
    """Generate the あいうえお (a-i-u-e-o) sequence."""
    segment_dur = 0.15
    vowel_keys = ['a', 'i', 'u', 'e', 'o']
    result = []
    for i, key in enumerate(vowel_keys):
        v = VOWELS[key]
        if i < len(vowel_keys) - 1:
            v_next = VOWELS[vowel_keys[i + 1]]
            seg = synthesize_vowel_transition(v, v_next, segment_dur)
        else:
            seg = synthesize_voiced(v, segment_dur)
        result.extend(seg)
    return apply_envelope(result, attack_ms=15, release_ms=25)


def generate_vcv_long_file(vcv_entries: list[OtoEntry]) -> list[float]:
    """Generate the long VCV WAV file containing all vowel transitions.

    Each VCV entry has an offset into this single long file.
    """
    if not vcv_entries:
        return []

    # Sort entries by offset to build the file sequentially
    sorted_entries = sorted(vcv_entries, key=lambda e: e.offset)

    # Calculate total duration from last entry's offset + some extra
    last = sorted_entries[-1]
    total_duration_ms = last.offset + last.consonant + 300  # extra tail
    total_samples = int(total_duration_ms * 44100 / 1000)

    result = [0.0] * total_samples

    for entry in sorted_entries:
        alias = entry.alias
        if alias not in VCV_TRANSITIONS:
            continue

        v1_key, v2_key = VCV_TRANSITIONS[alias]
        v1 = VOWELS[v1_key]
        v2 = VOWELS[v2_key]

        # Each segment: ~500ms total
        segment_dur = 0.5
        segment = synthesize_vowel_transition(v1, v2, segment_dur)
        segment = apply_envelope(segment, attack_ms=10, release_ms=15)

        # Place at the entry's offset position
        start_sample = int(entry.offset * 44100 / 1000)
        for i, s in enumerate(segment):
            idx = start_sample + i
            if 0 <= idx < total_samples:
                result[idx] += s

    # Normalize
    peak = max(abs(s) for s in result) or 1.0
    if peak > 1.0:
        for i in range(len(result)):
            result[i] /= peak

    return result


def _add_voicing(samples: list[float], duration_s: float) -> None:
    """Add voicing buzz to samples in-place (for voiced variants of unvoiced consonants)."""
    import math
    f0 = 277.183
    n = len(samples)
    for i in range(n):
        t = i / 44100
        buzz = 0.0
        for h in range(1, 4):
            buzz += math.sin(2 * math.pi * f0 * h * t) / h
        buzz *= 0.15
        samples[i] = samples[i] * 0.8 + buzz * 0.2


def generate_all_samples(entries: list[OtoEntry], output_dir: str,
                         progress_callback=None) -> dict[str, bool]:
    """Generate WAV files for all entries.

    Returns dict of {filename: success}.
    Groups entries by filename (multiple oto entries can share one WAV).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Group entries by filename
    file_groups: dict[str, list[OtoEntry]] = {}
    for e in entries:
        file_groups.setdefault(e.filename, []).append(e)

    # Identify VCV entries (all from the long file)
    vcv_filename = None
    vcv_entries = []
    for fname, group in file_groups.items():
        if 'ああいあうあえ' in fname:
            vcv_filename = fname
            vcv_entries = group
            break

    results = {}
    total = len(file_groups)
    done = 0

    for filename, group in file_groups.items():
        done += 1

        # Skip VCV long file (handle separately)
        if filename == vcv_filename:
            continue

        filepath = os.path.join(output_dir, filename)

        try:
            # Use the first entry for synthesis parameters
            entry = group[0]
            samples = generate_sample(entry)
            if samples:
                write_wav(filepath, samples)
                results[filename] = True
            else:
                results[filename] = False
        except Exception as e:
            print(f"  Error generating {filename}: {e}", file=sys.stderr)
            results[filename] = False

        if progress_callback and done % 50 == 0:
            progress_callback(done, total)

    # Generate VCV long file
    if vcv_filename and vcv_entries:
        try:
            vcv_samples = generate_vcv_long_file(vcv_entries)
            if vcv_samples:
                filepath = os.path.join(output_dir, vcv_filename)
                write_wav(filepath, vcv_samples)
                results[vcv_filename] = True
            else:
                results[vcv_filename] = False
        except Exception as e:
            print(f"  Error generating VCV file: {e}", file=sys.stderr)
            results[vcv_filename] = False

    return results

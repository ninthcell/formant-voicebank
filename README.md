# FormantVoice — Formant-Synthesized UTAU Voice Bank Generator

Pure Python formant synthesis engine that generates a complete UTAU/OpenUTAU voice bank from scratch — no audio samples, no external dependencies, just math.

## Demo

**あいうえお (a-i-u-e-o) vowel sequence:**

> [demo/aiueo.wav](demo/aiueo.wav) — generated entirely by additive sine synthesis + formant filtering

## What It Does

Takes a reference `oto.ini` (from Adachi Rei ver3.5.0) and generates:

- **551 WAV files** — vowels, consonant-vowel pairs, transitions, breaths
- **585 oto.ini entries** — timing parameters copied from reference
- Ready-to-use ZIP package for OpenUTAU

All audio is synthesized using additive harmonics shaped by formant resonance peaks. No recordings involved.

## Voice Character

**Breathy / Airy** — distinct from Adachi Rei's clean sine tone:

- 88% sine harmonics + 12% formant-filtered noise
- Steeper harmonic rolloff (1/n^1.5) for softer timbre
- Wider formant bandwidths for breathier resonance
- Gentle cosine attack envelopes

Base pitch: C#4 (277.183 Hz)

## Architecture

```
main.py              # Entry point — parse → generate → package
src/
├── phonemes.py      # Japanese phoneme → formant parameter database
├── synth.py         # Additive synthesis engine (sine + noise + envelopes)
├── oto_parser.py    # Reference oto.ini parser (Shift-JIS)
├── generator.py     # Maps oto entries to synthesis functions
└── packager.py      # ZIP packaging with oto.ini + metadata
```

### Synthesis Pipeline

1. **Parse** reference `oto.ini` → extract entry names, timing parameters
2. **Classify** each entry (vowel, CV, VCV, consonant-only, breath, etc.)
3. **Synthesize** using the appropriate method:
   - **Vowels**: Steady-state formant harmonics
   - **CV syllables**: Consonant burst/friction → formant transition → vowel
   - **Transitions**: Continuous-phase formant interpolation
   - **Consonants**: Filtered noise bursts (plosive, fricative, affricate)
   - **Breaths**: Wide-band filtered noise with gentle envelope
4. **Package** into ZIP with `oto.ini`, `character.txt`, `character.yaml`

### Phoneme Coverage

| Category | Count |
|----------|-------|
| Vowels (plain/voiced/whisper) | 15 |
| CV plain + palatalized + extended | 193 |
| CV whisper | 158 |
| Consonant-only | 107 |
| Vowel transitions | 12 |
| VCV transitions | 35 |
| Romaji entries | 20 |
| Breaths | 3 |
| ん (nasal) entries | 11 |

## Usage

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Place reference oto.ini at reference/足立レイver3.5.0/oto.ini
uv run python main.py
```

Output: `output/FormantVoice.zip` (~24 MB)

Load the ZIP in [OpenUTAU](https://www.openutau.com/) as a voice bank.

## Technical Details

- **Sample format**: 16-bit, 44100 Hz, mono WAV
- **Synthesis**: Additive sine harmonics with Lorentzian formant envelope
- **Noise**: IIR biquad bandpass filtered white noise per formant
- **Transitions**: Continuous phase accumulation across formant interpolation chunks
- **Envelopes**: Cosine ADSR + 3ms safety fade at WAV boundaries
- **No external dependencies** — stdlib only (`math`, `wave`, `struct`, `zipfile`, `random`)

## License

MIT

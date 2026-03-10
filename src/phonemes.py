"""Japanese phoneme database: kana → formant parameters mapping."""

from dataclasses import dataclass


@dataclass
class FormantSet:
    """Formant frequencies (Hz) and bandwidths (Hz) for F1, F2, F3."""
    f1: float
    f2: float
    f3: float
    bw1: float = 150.0  # wider bandwidths for breathy quality
    bw2: float = 170.0
    bw3: float = 200.0


@dataclass
class ConsonantParams:
    """Parameters for consonant synthesis."""
    ctype: str          # 'plosive','fricative','affricate','nasal','liquid','glide','none'
    voiced: bool
    burst_dur_ms: float       # duration of burst/friction
    noise_freq_low: float     # noise band low freq
    noise_freq_high: float    # noise band high freq
    transition_ms: float      # transition to vowel duration


@dataclass
class PhonemeInfo:
    """Complete phoneme info: consonant + vowel."""
    consonant: ConsonantParams | None
    vowel: FormantSet | None
    is_whisper: bool = False
    is_voiced_variant: bool = False
    is_consonant_only: bool = False


# === Vowel formants (Japanese, tuned for breathy/airy character) ===
VOWELS = {
    'a': FormantSet(f1=800, f2=1200, f3=2500, bw1=150, bw2=170, bw3=200),
    'i': FormantSet(f1=300, f2=2300, f3=3000, bw1=130, bw2=160, bw3=200),
    'u': FormantSet(f1=300, f2=1500, f3=2300, bw1=140, bw2=160, bw3=200),
    'e': FormantSet(f1=500, f2=1800, f3=2500, bw1=140, bw2=170, bw3=200),
    'o': FormantSet(f1=500, f2=1000, f3=2500, bw1=150, bw2=160, bw3=200),
    'n': FormantSet(f1=300, f2=1400, f3=2500, bw1=200, bw2=200, bw3=250),  # syllabic n
}

# === Consonant definitions ===
CONSONANTS = {
    # Plosives: soft burst with longer transition for smoothness
    'k': ConsonantParams('plosive', False, 18.0, 2000, 4500, 55),
    'g': ConsonantParams('plosive', True, 15.0, 1500, 3500, 55),
    't': ConsonantParams('plosive', False, 15.0, 3000, 6000, 50),
    'd': ConsonantParams('plosive', True, 12.0, 2000, 4500, 50),
    'p': ConsonantParams('plosive', False, 15.0, 500, 2500, 50),
    'b': ConsonantParams('plosive', True, 12.0, 400, 2000, 50),

    # Fricatives: well-separated bands, longer transitions
    's': ConsonantParams('fricative', False, 100.0, 5000, 11000, 50),
    'z': ConsonantParams('fricative', True, 80.0, 3500, 9000, 50),
    'sh': ConsonantParams('fricative', False, 100.0, 2500, 7000, 55),
    'j': ConsonantParams('fricative', True, 70.0, 2000, 6000, 55),
    'h': ConsonantParams('fricative', False, 80.0, 800, 5000, 40),
    'f': ConsonantParams('fricative', False, 80.0, 2000, 7000, 50),

    # Affricates: gentle stop+release
    'ch': ConsonantParams('affricate', False, 70.0, 2500, 7500, 55),
    'ts': ConsonantParams('affricate', False, 70.0, 4000, 10000, 50),

    # Nasals: clear resonance
    'n': ConsonantParams('nasal', True, 50.0, 200, 400, 40),
    'ny': ConsonantParams('nasal', True, 55.0, 250, 500, 45),
    'm': ConsonantParams('nasal', True, 50.0, 200, 350, 40),
    'my': ConsonantParams('nasal', True, 55.0, 250, 400, 45),

    # Palatalized fricatives
    'hy': ConsonantParams('fricative', False, 80.0, 2000, 7000, 45),

    # Glides: pure transition
    'y': ConsonantParams('glide', True, 0.0, 0, 0, 70),
    'w': ConsonantParams('glide', True, 0.0, 0, 0, 70),

    # Liquids
    'r': ConsonantParams('liquid', True, 18.0, 1000, 3000, 35),
    'ry': ConsonantParams('liquid', True, 20.0, 1200, 3500, 40),
    'l': ConsonantParams('liquid', True, 20.0, 800, 2500, 40),

    # Palatalized plosives
    'ky': ConsonantParams('plosive', False, 18.0, 2500, 5500, 50),
    'gy': ConsonantParams('plosive', True, 15.0, 2000, 4500, 50),
    'py': ConsonantParams('plosive', False, 15.0, 1000, 3500, 45),
    'by': ConsonantParams('plosive', True, 12.0, 800, 3000, 45),
    'dy': ConsonantParams('plosive', True, 12.0, 2000, 4500, 45),
    'ty': ConsonantParams('plosive', False, 15.0, 2500, 5500, 45),

    # V
    'v': ConsonantParams('fricative', True, 50.0, 300, 2000, 40),
}

# Glide formant targets (transition start point)
GLIDE_FORMANTS = {
    'y': FormantSet(f1=280, f2=2300, f3=3100, bw1=100, bw2=140, bw3=180),
    'w': FormantSet(f1=300, f2=700, f3=2400, bw1=120, bw2=140, bw3=180),
}


# === Kana → (consonant_key, vowel_key) mapping ===
# This is the complete mapping for all hiragana used in the voice bank.

KANA_MAP: dict[str, tuple[str | None, str | None]] = {
    # Pure vowels
    'あ': (None, 'a'), 'い': (None, 'i'), 'う': (None, 'u'),
    'え': (None, 'e'), 'お': (None, 'o'),

    # Ka row
    'か': ('k', 'a'), 'き': ('k', 'i'), 'く': ('k', 'u'),
    'け': ('k', 'e'), 'こ': ('k', 'o'),
    'きゃ': ('ky', 'a'), 'きゅ': ('ky', 'u'), 'きょ': ('ky', 'o'),
    'きぇ': ('ky', 'e'),

    # Ga row
    'が': ('g', 'a'), 'ぎ': ('g', 'i'), 'ぐ': ('g', 'u'),
    'げ': ('g', 'e'), 'ご': ('g', 'o'),
    'ぎゃ': ('gy', 'a'), 'ぎゅ': ('gy', 'u'), 'ぎょ': ('gy', 'o'),
    'ぎぇ': ('gy', 'e'),

    # Sa row
    'さ': ('s', 'a'), 'し': ('sh', 'i'), 'す': ('s', 'u'),
    'せ': ('s', 'e'), 'そ': ('s', 'o'),
    'しゃ': ('sh', 'a'), 'しゅ': ('sh', 'u'), 'しょ': ('sh', 'o'),
    'しぇ': ('sh', 'e'),

    # Za row
    'ざ': ('z', 'a'), 'じ': ('j', 'i'), 'ず': ('z', 'u'),
    'ぜ': ('z', 'e'), 'ぞ': ('z', 'o'),
    'じゃ': ('j', 'a'), 'じゅ': ('j', 'u'), 'じょ': ('j', 'o'),
    'じぇ': ('j', 'e'),

    # Ta row
    'た': ('t', 'a'), 'ち': ('ch', 'i'), 'つ': ('ts', 'u'),
    'て': ('t', 'e'), 'と': ('t', 'o'),
    'ちゃ': ('ch', 'a'), 'ちゅ': ('ch', 'u'), 'ちょ': ('ch', 'o'),
    'ちぇ': ('ch', 'e'),

    # Da row
    'だ': ('d', 'a'), 'ぢ': ('j', 'i'), 'づ': ('z', 'u'),
    'で': ('d', 'e'), 'ど': ('d', 'o'),
    'ぢゃ': ('j', 'a'), 'ぢゅ': ('j', 'u'), 'ぢょ': ('j', 'o'),
    'ぢぇ': ('j', 'e'),

    # Na row
    'な': ('n', 'a'), 'に': ('ny', 'i'), 'ぬ': ('n', 'u'),
    'ね': ('n', 'e'), 'の': ('n', 'o'),
    'にゃ': ('ny', 'a'), 'にゅ': ('ny', 'u'), 'にょ': ('ny', 'o'),
    'にぇ': ('ny', 'e'),

    # Ha row
    'は': ('h', 'a'), 'ひ': ('hy', 'i'), 'ふ': ('f', 'u'),
    'へ': ('h', 'e'), 'ほ': ('h', 'o'),
    'ひゃ': ('hy', 'a'), 'ひゅ': ('hy', 'u'), 'ひょ': ('hy', 'o'),
    'ひぇ': ('hy', 'e'),

    # Ba row
    'ば': ('b', 'a'), 'び': ('b', 'i'), 'ぶ': ('b', 'u'),
    'べ': ('b', 'e'), 'ぼ': ('b', 'o'),
    'びゃ': ('by', 'a'), 'びゅ': ('by', 'u'), 'びょ': ('by', 'o'),
    'びぇ': ('by', 'e'),

    # Pa row
    'ぱ': ('p', 'a'), 'ぴ': ('p', 'i'), 'ぷ': ('p', 'u'),
    'ぺ': ('p', 'e'), 'ぽ': ('p', 'o'),
    'ぴゃ': ('py', 'a'), 'ぴゅ': ('py', 'u'), 'ぴょ': ('py', 'o'),
    'ぴぇ': ('py', 'e'),

    # Ma row
    'ま': ('m', 'a'), 'み': ('m', 'i'), 'む': ('m', 'u'),
    'め': ('m', 'e'), 'も': ('m', 'o'),
    'みゃ': ('my', 'a'), 'みゅ': ('my', 'u'), 'みょ': ('my', 'o'),
    'みぇ': ('my', 'e'),

    # Ya row
    'や': ('y', 'a'), 'ゆ': ('y', 'u'), 'よ': ('y', 'o'),

    # Ra row
    'ら': ('r', 'a'), 'り': ('r', 'i'), 'る': ('r', 'u'),
    'れ': ('r', 'e'), 'ろ': ('r', 'o'),
    'りゃ': ('ry', 'a'), 'りゅ': ('ry', 'u'), 'りょ': ('ry', 'o'),
    'りぇ': ('ry', 'e'),

    # Wa row + archaic
    'わ': ('w', 'a'), 'ゐ': ('w', 'i'), 'ゑ': ('w', 'e'), 'を': ('w', 'o'),

    # N
    'ん': (None, 'n'),

    # Extended combinations with small kana
    # ku + small vowels
    'くぁ': ('k', 'a'), 'くぃ': ('k', 'i'), 'くぇ': ('k', 'e'), 'くぉ': ('k', 'o'),
    'ぐぁ': ('g', 'a'), 'ぐぃ': ('g', 'i'), 'ぐぇ': ('g', 'e'), 'ぐぉ': ('g', 'o'),

    # su + small vowels
    'すぁ': ('s', 'a'), 'すぃ': ('s', 'i'), 'すぇ': ('s', 'e'), 'すぉ': ('s', 'o'),
    'ずぁ': ('z', 'a'), 'ずぃ': ('z', 'i'), 'ずぇ': ('z', 'e'), 'ずぉ': ('z', 'o'),
    'すぅぃ': ('s', 'i'), 'ずぅぃ': ('z', 'i'),

    # tsu + small vowels
    'つぁ': ('ts', 'a'), 'つぃ': ('ts', 'i'), 'つぇ': ('ts', 'e'), 'つぉ': ('ts', 'o'),

    # te/de + small vowels (ti/di sounds)
    'てぃ': ('t', 'i'), 'でぃ': ('d', 'i'),
    'てぃぁ': ('t', 'a'), 'てぃぇ': ('t', 'e'),
    'てゃ': ('ty', 'a'), 'てゅ': ('ty', 'u'), 'てょ': ('ty', 'o'),
    'でゃ': ('dy', 'a'), 'でゅ': ('dy', 'u'), 'でょ': ('dy', 'o'),
    'でぃぇ': ('d', 'e'),

    # to/do + small u
    'とぅ': ('t', 'u'), 'どぅ': ('d', 'u'),
    'どぅぁ': ('d', 'a'), 'どぅぃ': ('d', 'i'), 'どぅぇ': ('d', 'e'), 'どぅぉ': ('d', 'o'),

    # hu/fu + small vowels
    'ふぁ': ('f', 'a'), 'ふぃ': ('f', 'i'), 'ふぇ': ('f', 'e'), 'ふぉ': ('f', 'o'),
    'ぶぁ': ('b', 'a'), 'ぶぃ': ('b', 'i'), 'ぶぇ': ('b', 'e'), 'ぶぉ': ('b', 'o'),
    'ぷぁ': ('p', 'a'), 'ぷぃ': ('p', 'i'), 'ぷぇ': ('p', 'e'), 'ぷぉ': ('p', 'o'),
    'ふぃぇ': ('f', 'e'),
    'ふゃ': ('f', 'a'), 'ふゅ': ('f', 'u'), 'ふょ': ('f', 'o'),

    # ho + small a
    'ほぁ': ('h', 'a'),

    # u + glides (vu sounds)
    'うぁ': ('v', 'a'), 'うぃ': ('v', 'i'), 'うぇ': ('v', 'e'), 'うぉ': ('v', 'o'),
    'うゃ': ('v', 'a'), 'うゅ': ('v', 'u'), 'うょ': ('v', 'o'),

    # vu (ヴ mapped from う゛)
    'う゛ぁ': ('v', 'a'), 'う゛ぃ': ('v', 'i'), 'う゛ぇ': ('v', 'e'), 'う゛ぉ': ('v', 'o'),

    # n + vowels
    'んぁ': ('n', 'a'), 'んぇ': ('n', 'e'), 'んぉ': ('n', 'o'),
    'んな': ('n', 'a'),

    # Vowel transitions (two-character vowel combos)
    'あい': (None, 'a'),  # handled specially as vowel transition
    'あう': (None, 'a'),
    'あえ': (None, 'a'),
    'あお': (None, 'a'),
    'あん': (None, 'a'),
    'いう': (None, 'i'),
    'いえ': (None, 'i'),
    'いお': (None, 'i'),
    'いん': (None, 'i'),
    'うえ': (None, 'u'),
    'うお': (None, 'u'),
    'えお': (None, 'e'),
    'あいうえお': (None, 'a'),

    # ye
    'いぇ': ('y', 'e'),

    # mo + yo
    'もょ': ('m', 'o'),

    # Special long sound
    'じゃーん': ('j', 'a'),
}

# Romaji consonant-only entries mapping
ROMAJI_MAP: dict[str, tuple[str | None, str | None]] = {
    'a': (None, 'a'),
    'ae': (None, 'a'),  # a→e transition
    'ay': (None, 'a'),  # a→y transition
    'b': ('b', None),
    'ce': ('s', 'e'),
    'ch': ('ch', None),
    'd': ('d', None),
    'f': ('f', None),
    'g': ('g', None),
    'h': ('h', None),
    'k': ('k', None),
    'l': ('l', None),
    'o': (None, 'o'),
    'p': ('p', None),
    'ry': ('ry', None),
    'sh': ('sh', None),
    't': ('t', None),
    'ts': ('ts', None),
    'z': ('z', None),
    'zi': ('z', 'i'),
}

# Voiced (゛) modifier mapping for vowels — adds rough buzzy quality
# Whisper (・) modifier — uses noise-based source instead of harmonics

# Vowel transition pairs
VOWEL_TRANSITIONS: dict[str, tuple[str, str]] = {
    'あい': ('a', 'i'),
    'あう': ('a', 'u'),
    'あえ': ('a', 'e'),
    'あお': ('a', 'o'),
    'あん': ('a', 'n'),
    'いう': ('i', 'u'),
    'いえ': ('i', 'e'),
    'いお': ('i', 'o'),
    'いん': ('i', 'n'),
    'うえ': ('u', 'e'),
    'うお': ('u', 'o'),
    'えお': ('e', 'o'),
}

# VCV alias → (vowel1, vowel2) for the long VCV file
VCV_TRANSITIONS: dict[str, tuple[str, str]] = {
    'a あ': ('a', 'a'), 'a い': ('a', 'i'), 'i あ': ('i', 'a'),
    'a う': ('a', 'u'), 'u あ': ('u', 'a'), 'a え': ('a', 'e'),
    'e あ': ('e', 'a'), 'a お': ('a', 'o'), 'o あ': ('o', 'a'),
    'a ん': ('a', 'n'), 'n い': ('n', 'i'), 'i い': ('i', 'i'),
    'i う': ('i', 'u'), 'u い': ('u', 'i'), 'i え': ('i', 'e'),
    'e い': ('e', 'i'), 'i お': ('i', 'o'), 'o い': ('o', 'i'),
    'i ん': ('i', 'n'), 'n う': ('n', 'u'), 'u う': ('u', 'u'),
    'u え': ('u', 'e'), 'e う': ('e', 'u'), 'u お': ('u', 'o'),
    'o う': ('o', 'u'), 'u ん': ('u', 'n'), 'n え': ('n', 'e'),
    'e え': ('e', 'e'), 'e お': ('e', 'o'), 'o え': ('o', 'e'),
    'e ん': ('e', 'n'), 'n お': ('n', 'o'), 'o お': ('o', 'o'),
    'o ん': ('o', 'n'), 'n ん': ('n', 'n'),
}


def parse_kana_name(name: str) -> PhonemeInfo:
    """Parse a kana-based filename (without .wav) into PhonemeInfo.

    Handles suffixes: ゛ (voiced variant), ・ (whisper), 子音 (consonant only)
    """
    is_whisper = False
    is_voiced_variant = False
    is_consonant_only = False

    # Strip suffixes
    base = name
    if base.endswith('子音'):
        is_consonant_only = True
        base = base[:-2]

    if base.endswith('・'):
        is_whisper = True
        base = base[:-1]

    # Check for ゛ (dakuten as modifier on vowels/specific chars)
    if '゛' in base:
        is_voiced_variant = True
        # For entries like な゛, ま゛ etc, strip the ゛
        base = base.replace('゛', '')

    # Check for ゜ (handakuten modifier)
    if '゜' in base:
        is_voiced_variant = True
        base = base.replace('゜', '')

    # Look up in kana map
    if base in KANA_MAP:
        cons_key, vowel_key = KANA_MAP[base]
    elif len(base) >= 2 and base in KANA_MAP:
        cons_key, vowel_key = KANA_MAP[base]
    else:
        # Try single-char lookup for compound names
        if len(base) == 1 and base in KANA_MAP:
            cons_key, vowel_key = KANA_MAP[base]
        else:
            # Fallback: treat as generic vowel /a/
            cons_key, vowel_key = None, 'a'

    consonant = CONSONANTS.get(cons_key) if cons_key else None
    vowel = VOWELS.get(vowel_key) if vowel_key else None

    if is_consonant_only:
        vowel = None

    return PhonemeInfo(
        consonant=consonant,
        vowel=vowel,
        is_whisper=is_whisper,
        is_voiced_variant=is_voiced_variant,
        is_consonant_only=is_consonant_only,
    )

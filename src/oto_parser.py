"""Parse UTAU oto.ini files (Shift-JIS encoded)."""

from dataclasses import dataclass


@dataclass
class OtoEntry:
    """A single oto.ini entry."""
    filename: str       # WAV filename (e.g. 'あ.wav')
    alias: str          # alias (empty string if same as filename base)
    offset: float       # ms - start offset
    consonant: float    # ms - consonant length
    cutoff: float       # ms - end cutoff (negative = from end)
    preutterance: float # ms - preutterance point
    overlap: float      # ms - overlap with previous note
    raw_line: str       # original line for reference


# Instrument/SFX keywords to filter out
_INSTRUMENT_KEYWORDS = [
    'オルガン', 'ギター', 'シンバル', 'スネア', 'トランペット', 'ドラム',
    'ノコギリ波', 'ノック', 'ハーモニカ', 'ハイタム', 'ハイハット', 'バイオリン',
    'バスドラム', 'バチ', 'ビーム', 'ビー玉', 'ピアノ', 'ピンポン玉', 'フロアタム',
    'ベル', 'ホームラン', 'マシンガン', 'ロータム', 'ロボット', '殴打', '音の出ない',
    '乾いた', '金属', '矩形波', '軽く叩く', '硬質', '雑音', '心音', '振動',
    '正弦波', '太鼓', '中ドラム', '破裂', '爆発', '発砲', '木琴', '有声摩擦',
]


def parse_oto_ini(filepath: str) -> list[OtoEntry]:
    """Parse an oto.ini file. Returns all entries."""
    entries = []
    with open(filepath, 'r', encoding='shift_jis') as f:
        for line in f:
            line = line.strip()
            if not line or '=' not in line:
                continue

            # Split: filename.wav=alias,offset,consonant,cutoff,preutterance,overlap
            filename_part, params_part = line.split('=', 1)
            parts = params_part.split(',')
            if len(parts) < 6:
                continue

            entries.append(OtoEntry(
                filename=filename_part,
                alias=parts[0],
                offset=float(parts[1]),
                consonant=float(parts[2]),
                cutoff=float(parts[3]),
                preutterance=float(parts[4]),
                overlap=float(parts[5]),
                raw_line=line,
            ))

    return entries


def filter_speech_entries(entries: list[OtoEntry]) -> list[OtoEntry]:
    """Filter out instrument/SFX entries, keep speech + breath only."""
    result = []
    for e in entries:
        if any(kw in e.filename for kw in _INSTRUMENT_KEYWORDS):
            continue
        # Also filter out ヴァ/ヴぃ etc (katakana vu - these are aliases to う゛ entries)
        if e.filename.startswith('ヴ') and e.alias:
            continue
        # Keep 江.wav (いぇ alias)
        result.append(e)
    return result


def get_unique_filenames(entries: list[OtoEntry]) -> list[str]:
    """Get unique WAV filenames from entries (some files have multiple entries)."""
    seen = set()
    filenames = []
    for e in entries:
        if e.filename not in seen:
            seen.add(e.filename)
            filenames.append(e.filename)
    return filenames

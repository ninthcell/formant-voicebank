"""Package generated voice bank into ZIP with oto.ini and metadata."""

import os
import zipfile


VOICEBANK_NAME = "FormantVoice"

CHARACTER_TXT = """\
備考：フォルマント合成ボイスバンク
身長：不明
-------------------------:
name=FormantVoice
image=
"""

CHARACTER_YAML = """\
singer_type: classic
portrait_opacity: 0.67
portrait_height: 0
default_phonemizer: OpenUtau.Plugin.Builtin.JapanesePresampPhonemizer
use_filename_as_alias: false
"""


def generate_oto_ini(reference_entries: list, generated_files: set[str]) -> str:
    """Generate oto.ini content, copying timings from reference for entries we generated.

    Only includes entries whose WAV files were actually generated.
    """
    lines = []
    for entry in reference_entries:
        if entry.filename in generated_files:
            lines.append(entry.raw_line)
    return '\n'.join(lines) + '\n'


def create_zip(output_dir: str, zip_path: str, oto_content: str) -> str:
    """Create ZIP file containing the voice bank.

    Args:
        output_dir: Directory containing generated WAV files
        zip_path: Output ZIP file path
        oto_content: Content for oto.ini

    Returns:
        Path to created ZIP file
    """
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add oto.ini (Shift-JIS encoded)
        oto_bytes = oto_content.encode('shift_jis', errors='replace')
        zf.writestr(f'{VOICEBANK_NAME}/oto.ini', oto_bytes)

        # Add character files
        zf.writestr(f'{VOICEBANK_NAME}/character.txt',
                     CHARACTER_TXT.encode('shift_jis', errors='replace'))
        zf.writestr(f'{VOICEBANK_NAME}/character.yaml',
                     CHARACTER_YAML.encode('utf-8'))

        # Add all WAV files
        wav_count = 0
        for fname in sorted(os.listdir(output_dir)):
            if fname.endswith('.wav'):
                fpath = os.path.join(output_dir, fname)
                zf.write(fpath, f'{VOICEBANK_NAME}/{fname}')
                wav_count += 1

    return zip_path

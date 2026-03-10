"""Main entry point: generate formant-synthesized UTAU voice bank."""

import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

from src.oto_parser import parse_oto_ini, filter_speech_entries, get_unique_filenames
from src.generator import generate_all_samples
from src.packager import generate_oto_ini, create_zip


REFERENCE_OTO = os.path.join('reference', '足立レイver3.5.0', 'oto.ini')
OUTPUT_DIR = os.path.join('output', 'wav')
ZIP_PATH = os.path.join('output', 'FormantVoice.zip')


def main():
    print("=== Formant Voice Bank Generator ===")
    print()

    # Step 1: Parse reference oto.ini
    print(f"Parsing reference oto.ini: {REFERENCE_OTO}")
    all_entries = parse_oto_ini(REFERENCE_OTO)
    print(f"  Total entries: {len(all_entries)}")

    # Step 2: Filter to speech + breath entries
    speech_entries = filter_speech_entries(all_entries)
    unique_files = get_unique_filenames(speech_entries)
    print(f"  Speech+breath entries: {len(speech_entries)}")
    print(f"  Unique WAV files to generate: {len(unique_files)}")
    print()

    # Step 3: Generate all samples
    print("Generating samples...")
    start_time = time.time()

    def progress(done, total):
        elapsed = time.time() - start_time
        print(f"  [{done}/{total}] {elapsed:.1f}s elapsed")

    results = generate_all_samples(speech_entries, OUTPUT_DIR, progress_callback=progress)

    elapsed = time.time() - start_time
    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"  Generated: {success} files, Failed: {failed} files ({elapsed:.1f}s)")
    print()

    # Step 4: Generate oto.ini and package
    print("Packaging voice bank...")
    generated_files = {f for f, ok in results.items() if ok}
    oto_content = generate_oto_ini(speech_entries, generated_files)

    os.makedirs(os.path.dirname(ZIP_PATH), exist_ok=True)
    create_zip(OUTPUT_DIR, ZIP_PATH, oto_content)

    zip_size = os.path.getsize(ZIP_PATH)
    print(f"  ZIP created: {ZIP_PATH} ({zip_size / 1024 / 1024:.1f} MB)")
    print()

    # Step 5: Summary
    print("=== Summary ===")
    print(f"  Voice bank: FormantVoice")
    print(f"  WAV files: {success}")
    print(f"  oto.ini entries: {len([e for e in speech_entries if e.filename in generated_files])}")
    print(f"  Output: {ZIP_PATH}")
    print()

    if failed > 0:
        print(f"  WARNING: {failed} files failed to generate:")
        for f, ok in results.items():
            if not ok:
                print(f"    - {f}")


if __name__ == '__main__':
    main()

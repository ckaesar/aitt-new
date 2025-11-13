import sys
from pathlib import Path
from pdfminer.high_level import extract_text


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_pdf.py <input_pdf> [output_txt]")
        sys.exit(1)

    input_pdf = Path(sys.argv[1])
    if not input_pdf.exists():
        print(f"Input PDF not found: {input_pdf}")
        sys.exit(2)

    if len(sys.argv) >= 3:
        output_txt = Path(sys.argv[2])
    else:
        output_txt = input_pdf.with_suffix('.txt')

    try:
        text = extract_text(str(input_pdf))
    except Exception as e:
        print(f"Failed to extract text: {e}")
        sys.exit(3)

    output_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"Text extracted to: {output_txt}")


if __name__ == '__main__':
    main()
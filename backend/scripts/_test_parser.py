import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.scraper.parsers.foodist_list_parser import parse_foodist_list_text

text = Path("foodist_card_sample.txt").read_text(encoding="utf-8").splitlines()[2]
result = parse_foodist_list_text(text, detail_url="brand/2a-akuzum-otomotiv-as")
Path("parser_test.txt").write_text(repr(result), encoding="utf-8")

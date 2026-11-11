"""Record hashes and provenance of the unmodified manufacturer reference files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sources = {
    'seeed-sense-v1.51.pdf': 'https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/new-res/202003753_XIAO%20ESP32S3%20Sense_V1.51_SCH_260611.pdf',
    'seeed-expansion-v1.2.pdf': 'https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/XIAO_ESP32S3_Exp_Board_v1.2_SCH_PDF_260810.pdf',
    'adafruit-3006.sch': 'https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout',
    'adafruit-3006.brd': 'https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout',
    'adafruit-license.txt': 'https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout',
}
folder = ROOT/'hardware/references'
report = {'consulted':'2026-11-09', 'modified':False,
          'files':{n:{'source':url,'sha256':hashlib.sha256((folder/n).read_bytes()).hexdigest()}
                   for n,url in sources.items()}}
(folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(sources)} manufacturer references recorded')

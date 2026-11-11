# Fuentes y trazabilidad

Consultadas el 9 de noviembre de 2026. Usar las revisiones indicadas y contrastar el material recibido. No se comprobó disponibilidad comercial ni se efectuaron compras. Las imágenes de referencia de fabricante no son renders del prototipo construido.

| Fuente primaria | Uso en el diseño |
|---|---|
| [Seeed XIAO ESP32S3: guía y recursos](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) | SKU, 8 MB PSRAM, dimensiones, USB, ensamblaje Sense y consumo orientativo |
| [Seeed: pines](https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/) | D0/GPIO1, D1/GPIO2, D3/GPIO4, D4/GPIO5, D5/GPIO6, D6/GPIO43 y salida 5 V |
| [Seeed: micrófono](https://wiki.seeedstudio.com/xiao_esp32s3_sense_mic/) | GPIO41/42 y captura PDM a 16 kHz |
| [Esquema XIAO Sense V1.51](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/new-res/202003753_XIAO%20ESP32S3%20Sense_V1.51_SCH_260611.pdf) | USB-C con CC1/CC2 de 5,1 kΩ, regulación, flash y cabeceras del módulo comprado |
| [Esquema expansión Sense V1.2](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/XIAO_ESP32S3_Exp_Board_v1.2_SCH_PDF_260810.pdf) | Circuito del micrófono y expansión; se conserva instalado |
| [Seeed: footprint DIP oficial](https://github.com/Seeed-Studio/OSHW-XIAO-Series/blob/main/Seeed%20Studio%20XIAO%20Series%20Library/XIAO-ESP32-S3-DIP.kicad_mod) | Numeración 1–14, paso y separación entre filas. Footprint propio simplificado para zócalos, no para montaje castellado |
| [Adafruit 3006](https://www.adafruit.com/product/3006) | Módulo amplificador elegido |
| [Adafruit: pinout MAX98357](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts) | GAIN 100 kΩ a VIN = 3 dB; pull-up SD 1 MΩ; BTL, niveles y alimentación |
| [Adafruit: PCB y esquema Eagle originales](https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout) | Orden de JP1, agujeros a ±6,35 / 13,97 mm respecto a centro de cabecera, condensadores internos |
| [onsemi BSS138](https://www.onsemi.com/pdf/datasheet/bss138-d.pdf) | Pinout G=1, S=2, D=3 y encapsulado SOT-23 |
| [Bourns MF-MSMF](https://bourns.com/docs/product-datasheets/mf-msmf.pdf) | F1 0,5 A hold/1 A trip a 23 °C; footprint estilo 1, pads 1,5×3,2, separación interna 2,7 |
| [Visaton K40, art.2840](https://www.visaton.de/en/products/drivers/miniature-speakers/k-40-8-ohm) y [plano 2023](https://www.visaton.de/sites/default/files/dd_product/K%2040_2840_2841_0.pdf) | 8 Ω/1 W; Ø40±0,2; cuerpo Ø36±0,3; reborde 1,3±0,2; profundidad 4,3±0,3 |
| [E-Switch PV6](https://configured-product-images.s3.amazonaws.com/Datasheets/PV6.pdf) | Versión momentánea sin iluminación PV6F240SS, M16 y profundidad |
| [Seeed antena A-02](https://www.seeedstudio.com/2-4GHz-FPC-Antenna-1-16dBi-for-XIAO-ESP32S3-p-6440.html) | SKU318020968; FPC 37,4×17,5; cable 65±2 |
| [Samtec SSW, plano oficial](https://suddendocs.samtec.com/prints/ssw-1xx-xx-xxx-x-xx-xxx-xx-mkt.pdf) | SSW-107-01-T-S: cuerpo de zócalo de 8,51 mm |
| [Samtec TSW, plano oficial](https://suddendocs.samtec.com/prints/tsw-xxx-xx-xxx-x-xx-xxx-mkt.pdf) | TSW-107-07-T-S: plástico de 2,54 mm; revisar longitud de terminales |
| [JST XH, ficha oficial](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf) | Paso 2,50 mm, B2B-XH-A, XHP-2 y contacto SXH-001T-P0.6 |
| [PlatformIO: XIAO ESP32S3](https://docs.platformio.org/en/stable/boards/espressif32/seeed_xiao_esp32s3.html) | Identificador de compilación y carga |
| [ESP-IDF 4.4.7: I²S S3](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/peripherals/i2s.html) | API utilizada con Arduino ESP32 2.0.17 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Ollama chat](https://docs.ollama.com/api/chat), [Piper CLI](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md) | Integración de modelos locales, versiones fijadas en requirements |
| [KiCad CLI](https://docs.kicad.org/9.0/en/cli/cli.html), [OpenSCAD](https://openscad.org/documentation.html) | Comprobaciones y exportación de CAD |

Los enlaces de recursos Seeed pueden actualizarse. Los dos PDF de referencia se archivan sin cambios en `hardware/references/` con hashes; no forman parte de los Gerber de la portadora. El fabricante publica el esquema principal bajo CC BY-SA 4.0. El esquema y PCB de Adafruit mantienen su licencia original, incluida con la copia. Los modelos de IA no están incluidos y tienen sus propias licencias.

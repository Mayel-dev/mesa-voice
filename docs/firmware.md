# Firmware Mesa Voice r1

El firmware corresponde a **Seeed Studio XIAO ESP32S3 Sense**, SKU 113991115, con 8 MB de PSRAM y la placa Sense con micrófono instalada. La cámara se retira y no se inicializa; no se monta tarjeta microSD. El modelo XIAO ESP32S3 sin Sense carece del micrófono necesario. Los números del código son GPIO del ESP32, no números de posición de cabecera.

| Función | GPIO | Uso |
|---|---:|---|
| Pulsador PTT | 1 / D0 | Activo bajo, pull-up externo 10 kΩ y debounce 30 ms |
| LED | 2 / D1 | Activo alto; resistencia en PCB |
| Silencio | 4 / D3 | Alto: transistor conduce y SD_MODE del amplificador queda bajo |
| I²S BCLK | 5 / D4 | Salida I2S1 |
| I²S LRCLK | 6 / D5 | Salida I2S1, 16 kHz |
| I²S datos | 43 / D6 | Salida I2S1, dos canales con el mismo PCM |
| Micrófono PDM DATA | 41 | Interno Sense; entrada I2S0 |
| Micrófono PDM CLK | 42 | Interno Sense; reloj I2S0 |

GPIO3, pines de USB y pines de cámara/SD no se utilizan como señales de la PCB. La consola usa USB CDC; no conectar UART0 a GPIO43, que se emplea para audio.

## Compilar y cargar

Requisitos reproducibles: Python 3.12, PlatformIO Core 6.1.18, plataforma `espressif32@6.12.0`. El manifiesto de compilación fija la plataforma; el registro en `validation/` identifica las versiones efectivamente instaladas. La plataforma usa Arduino ESP32 2.0.17 con el controlador I²S heredado de ESP-IDF 4.4, no las APIs Arduino 3.x. Ejecutar desde la raíz del repositorio.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install platformio==6.1.18
Copy-Item firmware/include/config.example.h firmware/include/secrets.h
# Editar secrets.h: SSID, contraseña, IPv4/DNS del servidor y el mismo token del backend.
$env:PLATFORMIO_CORE_DIR = Join-Path $env:USERPROFILE 'Documents/pio-mesa'
.\.venv\Scripts\python.exe -m platformio run -d firmware -e mesa_voice
.\.venv\Scripts\python.exe -m platformio run -d firmware -e mesa_voice -t upload --upload-port COM7
.\.venv\Scripts\python.exe -m platformio device monitor -d firmware --port COM7
```

Sustituir COM7 por el puerto real. Si el puerto no aparece, mantener BOOT al conectar USB-C y soltarlo después. Alimentar y programar por el mismo USB-C del XIAO. No introducir una segunda fuente por 5 V. `secrets.h` se ignora en Git; las credenciales quedan incluidas en el binario compilado, sin cifrado de flash.

Para repetir sólo la validación sin credenciales: `.\.venv\Scripts\python.exe tools/build_firmware.py --core-dir $env:PLATFORMIO_CORE_DIR`. Usa `-e validation` y `config.validation.h`, que contiene valores ficticios de formato válido y servidor TEST-NET `192.0.2.1`. Esto conserva Wi-Fi y audio en el enlace; no es una configuración utilizable. El entorno `mesa_voice` usa `secrets.h` si existe y, en su ausencia, el ejemplo vacío que se detiene por configuración inválida. No cargar la imagen de validación como firmware de uso.

La compilación completa de esta entrega terminó correctamente en PowerShell normal con una caché corta. Una ruta de caché muy larga produjo `CreateProcess: No such file or directory` por superar el límite de longitud de la orden de Windows. El GCC de esa versión tampoco arrancó dentro del entorno aislado de Codex. Si reaparece el problema, ejecutar el comando desde la terminal normal y conservar una ruta corta. Ningún script cambia la configuración de seguridad de Windows.

En Linux/macOS el ejecutable de la venv es `.venv/bin/python`; los comandos PlatformIO son iguales. El primer build descarga las herramientas. Después puede reconstruirse con la caché local.

## Operación

1. Conectar a USB-C y esperar a que deje de parpadear el LED de conexión.
2. Mantener pulsado PTT. El LED se enciende al terminar de vaciar los búferes del micrófono, aproximadamente 64 ms después; hablar entonces.
3. Soltar PTT para enviar. La captura dura como máximo 8 s; menos de 0,1 s se rechaza. Al llegar a 8 s se envía automáticamente y debe soltarse el botón antes de otra captura.
4. El LED permanece encendido durante la consulta y respuesta. No se admiten nuevas capturas mientras el servidor procesa o el altavoz reproduce.

Tres destellos indican fallo; la consola proporciona la causa general sin mostrar contraseña, token ni audio. Un destello corto cada 2 s indica ausencia de Wi-Fi. Un destello cada 1,2 s después de iniciar indica configuración inválida, ausencia de PSRAM o fallo de inicialización. No existe escucha continua ni palabra de activación en esta revisión.

## Comportamiento y límites

- Micrófono: PDM convertido por hardware a PCM16 mono a 16 kHz. Se activa el periférico únicamente durante PTT; esto no equivale a cortar físicamente la alimentación del micrófono.
- Captura máxima: 256.000 bytes de PCM + cabecera WAV de 44 bytes. Respuesta máxima: 640.000 bytes + 44. Ambos búferes se reservan en PSRAM al iniciar y se limpian tras una consulta. El borrado no es una garantía de eliminación segura de copias en DMA/pilas.
- Solicitud HTTP `POST /v1/voice`; respuesta exclusivamente WAV canónico PCM16 mono 16 kHz. Se rechazan tamaño excesivo, truncamiento, formato distinto, cabecera WAV incoherente, transferencia chunked, compresión, cabeceras duplicadas de longitud/tipo y respuestas que no sean HTTP 200.
- El servidor debe devolver `Content-Length` fijo y `Content-Type: audio/wav`. El cliente permite 5 s para conectar, 15 s para enviar, 150 s desde el fin del envío para las cabeceras y 30 s para el cuerpo. Son límites de etapas, no un plazo único de 150 s.
- No se reintenta automáticamente una consulta fallida; así una desconexión no repite una acción. Se reintenta la conexión Wi-Fi cada 10 s.
- HTTP transporta audio y token sin cifrar; usar sólo una LAN de confianza. Esta revisión no implementa TLS ni actualización remota de firmware.
- El amplificador sólo se habilita para reproducir, con reloj y datos válidos. Se envían muestras idénticas en los dos canales para que la mezcla mono del MAX98357A no reduzca el nivel. Se atenúa cada muestra a una cuarta parte y se limita a ±8192, con rampa de 5 ms al inicio y fin. Este límite digital no sustituye una medición de potencia o presión sonora.
- La resistencia externa de la señal de control debe mantener GPIO4 alto durante reset para silenciar el amplificador mediante el transistor; el software por sí solo no garantiza el silencio antes de arrancar.

## Verificación

`firmware/test/test_audio_protocol.cpp` ejecuta pruebas de límites WAV, tamaños, frecuencia, número de canales y formato; también recorre las 65.536 entradas PCM16 del atenuador. Se compiló con MSVC 19.51 y pasó. Es código C++ independiente del ESP32, compilable también con `c++ -std=c++17 -I firmware/include firmware/test/test_audio_protocol.cpp -o test_audio_protocol`. La evidencia se guarda en `validation/firmware-host-test.txt`.

La compilación ESP32-S3 del 2026-11-10 pasó: RAM estática 44.232/327.680 bytes y flash 705.129/3.342.336 bytes según PlatformIO; `firmware.bin` mide 705.488 bytes. `validation/firmware-build.json` contiene hashes de fuentes y artefactos. `validation/firmware-image.json` comprueba el ELF Xtensa y la presencia de las rutinas Wi-Fi e I²S. La reserva dinámica de PSRAM requiere comprobación en el dispositivo.

La compilación verifica enlaces y API; no verifica cableado, reloj real, PSRAM física, recepción acústica, alimentación, ruido, silenciamiento ni reproducción. Estos puntos requieren pruebas en la unidad montada. Antes del primer uso de voz, comprobar con osciloscopio BCLK/LRCLK, GPIO4/SD_MODE y 5 V/3,3 V; capturar un tono conocido y medir RMS/offset del micrófono. Confirmar que el micrófono está en el canal PDM esperado y que la placa Sense concreta mantiene el pinout descrito.

## Fuentes primarias

- [Seeed: uso del micrófono Sense](https://wiki.seeedstudio.com/xiao_esp32s3_sense_mic/) — GPIO41/42, PCM16, ejemplo a 16 kHz.
- [Seeed: multiplexación y alimentación](https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/) — señales de cabecera y salida de 5 V USB.
- [PlatformIO: XIAO ESP32S3](https://docs.platformio.org/en/stable/boards/espressif32/seeed_xiao_esp32s3.html) — ID de placa y procedimientos de carga.
- [Espressif: I²S ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/peripherals/i2s.html) — API heredada, modos y transferencia por DMA.

Referencias consultadas el 2026-11-09. El firmware conserva la versión de API fijada; ejemplos publicados para Arduino 3.x no se deben mezclar con este proyecto.

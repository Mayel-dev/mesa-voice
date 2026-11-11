# Reproducir y comprobar la entrega

Ejecutar desde la raíz de `mesa-voice`. Python 3.12 para herramientas generales y backend; Python incluido con KiCad 9.0.6 para `pcbnew`. OpenSCAD 2021.01 produjo los STL. El repositorio incluye fuentes y resultados, no las instalaciones de estas herramientas.

## Electrónica

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' tools/generate_hardware.py
python tools/generate_wiring.py
python tools/make_bom.py
python tools/release_hardware.py --kicad-cli 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' tools/check_interfaces.py
```

El generador sustituye el esquema, la PCB y sus bibliotecas. Para conservar cambios manuales en KiCad, omitir los generadores y volver a ejecutar las comprobaciones sobre los archivos editados. `release_hardware.py` comprueba estructura completa de los S-expressions, símbolos/pines esperados, ERC de ambos proyectos, DRC con paridad y las seis conexiones externas antes de exportar fabricación. No se desactivan infracciones para permitir una entrega. Algunas categorías no aplicables a la portadora, como ausencia de courtyard en puntos de prueba, están configuradas en el proyecto; consultar las reglas efectivas en `mesa-voice.kicad_pro`.

Los UUID, fechas y cabeceras de los exportadores pueden cambiar entre ejecuciones. Los hashes acreditan los archivos concretos comprobados; la reproducibilidad del diseño no implica identidad binaria de todos los archivos regenerados.

## Mecánica

```powershell
python -m pip install trimesh==4.6.8 numpy==2.2.6
python mechanical/export.py --openscad 'C:/Program Files/OpenSCAD/openscad.exe' --render
```

El exportador ejecuta CGAL, valida los tres STL y la intersección nominal de componentes con carcasa. Genera `validation/mechanical-meshes.json`, el log y las vistas PNG. No ejecuta un laminador ni modela los cables flexibles.

## Software

```powershell
python -m pip install -r backend/requirements-dev.txt
python tools/check_backend.py
python -m pip install platformio==6.1.18 pyelftools==0.33
python tools/build_firmware.py --core-dir C:/ruta/corta/pio-mesa
python tools/check_firmware_image.py
```

La ruta de caché es una carpeta escribible que el usuario elige; en Windows conviene que sea corta. Para el firmware de uso, seguir [firmware.md](firmware.md) y cargar el entorno `mesa_voice` con credenciales propias. El entorno `validation` sirve exclusivamente para probar la compilación completa con datos ficticios públicos.

Test C++ del protocolo, en Linux/macOS o una terminal con GCC:

```sh
c++ -std=c++17 -Wall -Wextra -Werror -I firmware/include firmware/test/test_audio_protocol.cpp -o test_audio_protocol
./test_audio_protocol
```

En Developer PowerShell de Visual Studio:

```powershell
cl /nologo /std:c++17 /EHsc /W4 /I firmware/include firmware/test/test_audio_protocol.cpp /Fe:test_audio_protocol.exe
./test_audio_protocol.exe
```

Para guardar también el informe y sus hashes, ejecutar `python tools/check_firmware_host.py` desde esa terminal con compilador disponible. La evidencia suministrada es de MSVC 19.51.36260. La compilación ESP32 se ejecutó desde PowerShell normal porque el GCC heredado no arrancaba en el entorno aislado del agente. Ningún script cambia la configuración de seguridad de Windows.

## Empaquetado

```powershell
python tools/package_release.py
```

Comprueba fuentes contra sus informes, resultados ERC/DRC, conexiones externas, archivos de fabricación, mallas, backend y compilación ESP32. También valida los enlaces locales Markdown. Crea `validation/release.json`, `SHA256SUMS.txt`, un ZIP de fuentes en la carpeta padre y su SHA256. Omite `.pio`, `.venv`, cachés, archivos temporales de KiCad, credenciales y registros de compilación auxiliares fuera de `validation/`.

La comprobación no vuelve a ejecutar los ensayos físicos ni la inferencia real. `validation/hardware-acceptance.csv` continúa pendiente por diseño. Si se modifica una fuente cubierta por un informe, hay que repetir esa comprobación antes de volver a empaquetar.

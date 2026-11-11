# Validación R1 y límites de la evidencia

Fecha de cierre digital: 2026-11-10. **Entrega para fabricar y probar una primera unidad experimental. No se ha construido ni validado un dispositivo físico.** La compilación, ERC, DRC y comprobaciones geométricas acreditan aspectos concretos del diseño; no demuestran funcionamiento conjunto.

| Área | Resultado automatizado | Lo que aún no demuestra |
|---|---|---|
| Esquema portadora | KiCad 9.0.6 ERC: 0 infracciones; estructura y 20 símbolos comprobados | Comportamiento eléctrico de la placa real |
| Cableado externo | ERC: 0; seis símbolos y seis conexiones exactas comprobadas contra la netlist exportada | Orientación física de conectores y soldaduras |
| PCB | DRC: 0 infracciones, 0 conexiones pendientes y 0 errores de paridad esquema/PCB; 31 conexiones enrutadas, 170 segmentos y 18 vías | Revisión CAM de un proveedor, integridad de señales y disipación medidas |
| Interfaces | 68 verificaciones: pinout, agujeros, GPIO, redes, BOM y separaciones nominales | Tolerancias completas y revisión de los módulos recibidos |
| Fabricación | Gerber X2, PTH/NPTH e IPC-2581 exportados después de las comprobaciones; manifiesto SHA256 | Placas recibidas y ensambladas |
| Carcasa | Tres STL cerrados, orientación coherente, volumen positivo y un sólido por pieza; intersección nominal CGAL vacía en el alcance modelado | Ajuste de impresión, cables, roscas y acústica |
| Backend | 41 pruebas Pytest y una petición HTTP real en localhost en modo mock | Inferencia real con faster-whisper/Ollama/Piper y latencia |
| Firmware de host | Test C++ compilado y ejecutado con MSVC; límites WAV y las 65.536 entradas PCM16 del atenuador | Periféricos y ejecución ESP32 |
| Firmware ESP32 | Compilación y enlace completos correctos con PlatformIO; ELF Xtensa contiene Wi-Fi, lectura I²S y salida I²S | Arranque, PSRAM, micrófono, Wi-Fi y altavoz reales |
| Sistema completo | Ninguna prueba física | Voz capturada, red Wi-Fi, respuesta audible, consumo, temperatura y fiabilidad |

Informes originales en `validation/`: `erc.json`, `wiring-erc.json`, `wiring-connectivity.json`, `drc.json`, `routing.json`, `interfaces.json`, `mechanical-meshes.json`, `backend-checks.json`, `backend-pytest.txt`, `transport.json`, `firmware-host.json`, `firmware-build.json` y `firmware-image.json`. `release.json` comprueba que las fuentes de la entrega coincidan con esos informes. `SHA256SUMS.txt` cubre los archivos distribuidos.

## Evidencia de compilación

El usuario ejecutó el comando de compilación desde PowerShell normal el 2026-11-10. Se inspeccionaron el registro, sus hashes y el ELF resultante. Entorno `validation`, plataforma `espressif32@6.12.0`, Arduino ESP32 2.0.17 y GCC Xtensa 8.4.0+2021r2-patch5. RAM estática: 44.232/327.680 bytes. Flash: 705.129/3.342.336 bytes. Imagen `firmware.bin`: 705.488 bytes; SHA256 `9810616dc4ed09a69a5215372291b7f3a64dda2b3429b755c2ac4f288de88176`.

La configuración de validación contiene SSID, contraseña y token ficticios públicos, más la dirección reservada TEST-NET `192.0.2.1`. Sus valores válidos en formato impiden que el optimizador elimine el código de red/audio por una configuración vacía. No sirve para operar el dispositivo. La entrega de fuentes no incorpora binarios del framework ni credenciales; hay que recompilar `mesa_voice` con `secrets.h` propio.

El bloqueo anterior del compilador quedó resuelto para esta compilación al ejecutarla desde PowerShell normal con una caché de ruta corta. Dentro del entorno aislado, el cargador de GCC seguía fallando. La evidencia satisfactoria procede del build posterior y corresponde a las fuentes actuales. El test de host se ejecutó por separado con MSVC.

## Correcciones durante la revisión

Se corrigió un paréntesis sobrante que hacía que KiCad interpretara el esquema de cableado como una hoja vacía y pasara ERC sin revisar sus conexiones. Se añadieron lectura estricta del archivo completo, conteo de contenido y comparación de las seis redes antes de exportar fabricación. Se creó su proyecto KiCad independiente para resolver correctamente la biblioteca local y se revisó visualmente la hoja exportada.

Se ajustaron las posiciones del altavoz, botón y LED y se reservó la tuerca Ø22 del pulsador. Se comprobaron envolventes nominales, agujeros y alturas de zócalos contra fuentes de fabricante. Se mejoraron las referencias del plano de montaje y se corrigieron el tamaño admitido del sobremolde USB y la longitud de cable en la BOM.

Pytest emite una advertencia de deprecación de `anyio.abc.BlockingPortal` utilizada por Starlette; no es un fallo de prueba. La repetición de pruebas requirió permitir localhost en el aislamiento de Windows para que `asyncio` pudiera crear su conexión interna. No se abrió un servicio hacia Internet ni se modificó el firewall del equipo.

## Qué falta para declarar funcional el prototipo

1. **Antes de fabricar:** contrastar las huellas a escala 1:1 y la altura de cabeceras con los módulos reales; revisar CAM con el fabricante elegido. La compatibilidad de clones no está asegurada.
2. **Preparación del PC:** descargar los modelos locales, configurar STT/Ollama/Piper, probar un WAV real y fijar SSID/IP/token del dispositivo. Esta integración con pesos reales está implementada, pero no fue ejecutada aquí.
3. **Primera placa:** soldar, verificar continuidad y medir 5 V/3,3 V, consumo, mute e I²S/PDM. Cargar el firmware configurado y verificar PSRAM y captura del micrófono.
4. **Primera impresión:** comprobar ajuste, acceso USB, alcance de la antena y guiado de cables. Ajustar holguras según impresora y componentes recibidos.
5. **Sistema completo:** ida y vuelta en modo mock, diez comandos con modelos reales, fallos de red, potencia/volumen y una hora en caja cerrada. Registrar temperatura y comportamiento acústico.

Registrar mediciones, instrumentos, fecha y revisión en `validation/hardware-acceptance.csv`. Todos los ensayos físicos siguen pendientes. Puede ser necesaria una revisión R2 si la primera unidad revela problemas de ajuste, alimentación, RF o audio. No existe una estimación responsable de esas correcciones antes de medirlas.

No quedan errores digitales conocidos que impidan entregar los archivos para un primer prototipo experimental. Esto no es una aprobación de producción ni una certificación. El sistema está limitado a pulsar para hablar, LAN de confianza, conversación sin domótica y operación semidúplex; no implementa wake word, TLS ni cancelación de eco.

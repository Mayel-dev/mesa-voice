# Fabricación y puesta en marcha

**Estado R1: diseño digital comprobado y firmware compilado; no existe una unidad física validada.** Revisar las dimensiones de los módulos recibidos antes de encargar una primera placa experimental. Los Gerber disponibles no constituyen una aprobación de producción en serie.

## Especificación de PCB

- 64 × 54 mm, contorno rectangular cerrado, dos capas de cobre, FR-4, 1,6 mm de espesor, cobre exterior 35 µm (1 oz).
- Pista mínima 0,25 mm; separación mínima 0,20 mm; cobre-borde mínimo 0,30 mm. Vías Ø0,70/0,30 mm.
- Máscara en ambas caras; serigrafía frontal; acabado HASL sin plomo o ENIG. Sin impedancia controlada ni vías ciegas.
- PTH: cabeceras Ø1,0 mm y vías Ø0,3 mm. NPTH: cuatro Ø3,2 mm y dos Ø2,7 mm. Respetar los archivos separados de perforación; no metalizar los NPTH.
- Montaje manual de R/C 0805, F1 1812, Q1 SOT-23 y conectores. Hay vías en algunos pads; no se ha cualificado reflow ni ensamblaje automatizado. La BOM identifica piezas, no un servicio PCBA aprobado.

Usar `hardware/mesa-voice-r1-fabrication.zip`. Incluye capas Gerber X2, Excellon, mapas de perforación e IPC-2581 de referencia. `manifest.json` liga los archivos a la revisión exacta y sus hashes. El archivo de ensamblaje `hardware/previews/assembly.svg` muestra contornos, referencias y pads. La serigrafía de la placa es deliberadamente reducida; conservar el plano al soldar.

Abrir `hardware/mesa-voice.kicad_pro` con KiCad 9.0.6 o posterior. Las librerías Mesa/Harness viajan dentro del proyecto. Si se cambia algo, volver a rellenar zonas y ejecutar `tools/release_hardware.py`; no mezclar Gerber de revisiones. El exportador exige ERC, ERC de cableado y DRC con paridad sin infracciones.

## Soldadura y orientación

1. Verificar contorno y taladros contra el plano a escala 1:1. Revisar al microscopio o lupa continuidad y ausencia de puentes.
2. Soldar R1–R7, C1/C2, F1 y Q1; después J1/J2 y tres zócalos hembra 1×7. No soldar componentes sobre TP1–TP4: son puntos de prueba.
3. Q1, visto desde arriba con USB hacia arriba: el pad aislado superior es pin 3 drenador/AMP_SD; abajo a la izquierda está pin 1 puerta y abajo a la derecha pin 2 fuente/GND. El BSS138 debe seguir esa orientación; comprobar el marcado con su hoja de datos.
4. U1 visto desde arriba: USB hacia el borde Y=0. La fila izquierda empieza en D0/pin1; la derecha empieza por 5V/pin14. No invertirlo.
5. U2: cabecera en Y=22, bornera hacia Y positiva. De izquierda a derecha: VIN, GND, SD, GAIN, DIN, BCLK, LRC. Encajar sólo el Adafruit 3006 compatible con ese pinout y dimensiones. No asumir compatibilidad de clones.
6. Montar el soporte de U2 y preparar cableados siguiendo [mechanical.md](mechanical.md) y el esquema `wiring.kicad_sch`. J1: pin1 PTT, pin2 GND. J2: pin1 ánodo LED, pin2 cátodo. El pad cuadrado marca pin1.

## Pruebas de banco por etapas

Registrar fecha, revisión, instrumentos, límites y resultados en una copia de `validation/hardware-acceptance.csv`. No marcar como aprobado algo sólo deducido del DRC.

1. **Sin módulos ni energía:** continuidad de cada red contra `hardware/netlist.xml`; comprobar ausencia de cortos entre 5 V, 3,3 V y GND. Los semiconductores y condensadores pueden alterar lecturas: no usar un umbral de resistencia arbitrario como única prueba.
2. **U1 solamente:** conectar USB a fuente limitada inicialmente a 150 mA para inspección con firmware vacío/sin Wi-Fi; si limita, desconectar e investigar, no elevar a ciegas. Verificar aproximadamente 5 V en U1 y 3,3 V en TP2 respecto a TP3. Para Wi-Fi aumentar el límite a 500 mA tras confirmar ausencia de fallo. No introducir una fuente paralela por cabecera.
3. **Firmware:** compilar con credenciales locales y cargar según [firmware.md](firmware.md). Verificar USB CDC y detección PSRAM. La compilación de validación pasó con datos ficticios; el firmware configurado y la unidad real todavía deben probarse.
4. **Mute:** antes de insertar U2, confirmar GPIO4 alto en reposo. Insertar U2 con alimentación desconectada. Energizar y medir TP4/AMP_SD: debe estar <0,16 V en reposo y durante grabación. Con GPIO4 bajo en reproducción debería estar aproximadamente 0,45 V por el divisor interno del módulo.
5. **Audio digital:** comprobar TX LRCLK=16 kHz y BCLK=512 kHz durante reproducción PCM16 estéreo. En PDM comprobar actividad del reloj GPIO42 y datos GPIO41; la frecuencia PDM exacta debe medirse. Revisar canal y nivel capturando un tono/voz conocida, sin muestras constantes ni saturación.
6. **Modo mock:** iniciar backend en modo mock y reservar IP del PC. Mantener PTT >0,2 s, soltar y confirmar tono corto. Probar Wi-Fi desconectado, token erróneo y servidor caído: mute debe permanecer activo y debe poder iniciarse una nueva consulta.
7. **Modelos reales:** instalar STT, Ollama y Piper, registrar versiones/hashes de pesos y probar primero con WAV desde el PC. Luego probar diez comandos en el dispositivo. Medir latencias; no atribuir las pruebas mock a reconocimiento real.
8. **Alimentación/acústica:** medir picos de corriente y caída en TP1 durante Wi-Fi y reproducción; comprobar resets, calentamiento del regulador, PTC y amplificador. Medir potencia/volumen con el altavoz de 8 Ω y mantenerla por debajo de su nominal de 1 W. No retirar la atenuación inicial sin repetir medidas.
9. **Caja cerrada:** una hora de funcionamiento con pruebas repetidas; registrar temperatura interior y de componentes, calidad de micrófono, cobertura Wi-Fi, vibración y fijación de cables. Confirmar que el USB no transmite esfuerzos al módulo y que se puede abrir sin arrancar conectores.

Para medir salida BTL, nunca unir SPK− a tierra. Usar instrumentación diferencial. Desconectar energía antes de cambiar conexiones. Esta guía trata sólo alimentación externa USB de baja tensión; no abrir ni modificar el cargador de red.

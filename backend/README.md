# Servidor local Mesa Voice

Python 3.12. Flujo: WAV del dispositivo → faster-whisper CPU/int8 → Ollama en loopback → Piper → WAV mono de 16 kHz. El modo `mock` devuelve únicamente un tono para probar transporte y reproducción. No reconoce voz ni responde preguntas.

## Instalación y prueba sin modelos

Desde `backend/`, crear un entorno virtual y ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:MESA_TOKEN = (python -c "import secrets; print(secrets.token_hex(24))")
$env:MESA_MODE = "mock"
python -m pytest -q
python -m uvicorn mesa_voice.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

En otra terminal con el mismo entorno y `MESA_TOKEN`:

```powershell
python -m scripts.smoke_client --output reply.wav
```

Linux/macOS: activar con `source .venv/bin/activate` y definir variables mediante `export`. Ejecutar siempre desde `backend/`; no hay instalación editable implícita. Las versiones directas están fijadas en `requirements*.txt`; `requirements-lock-tested.txt`, cuando está presente, registra las dependencias transitivas del entorno efectivamente probado. No incluye modelos.

## Inferencia real completamente local

Preparar los modelos una sola vez con conexión a Internet. No se incluyen pesos, voces ni ejecutables de terceros en el repositorio. Revisar sus licencias antes de redistribuirlos. La voz y el LLM son intercambiables; los nombres siguientes son una configuración inicial.

```powershell
python -m pip install -r requirements-local.txt
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-small', local_dir='models/faster-whisper-small')"
python -m piper.download_voices es_ES-davefx-medium --data-dir models
ollama pull qwen2.5:3b
```

Registrar el hash/revisión de los modelos descargados para repetir exactamente una prueba. `ollama list` muestra el identificador del LLM; conservar también SHA256 del ONNX y su JSON. Ningún modelo se descarga automáticamente durante una petición. `faster-whisper` usa una carpeta local y `local_files_only=True`.

Arrancar Ollama con `OLLAMA_NO_CLOUD=1` en **el entorno del proceso Ollama**, reiniciarlo y confirmar en su log `Ollama cloud disabled: true`. Mantener `127.0.0.1:11434` como escucha. La API de Mesa solo acepta un origen Ollama loopback; aun así, la desactivación de nube corresponde al proceso Ollama y debe comprobarse allí. [Configuración oficial de Ollama](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features).

```powershell
$env:MESA_MODE = "local"
$env:STT_MODEL = (Resolve-Path models/faster-whisper-small).Path
$env:STT_LANGUAGE = "es"
$env:OLLAMA_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "qwen2.5:3b"
$env:PIPER_MODEL = (Resolve-Path models/es_ES-davefx-medium.onnx).Path
python -m uvicorn mesa_voice.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 8 --no-access-log
```

Usar una red doméstica de confianza y limitar el firewall a la IP del dispositivo. La implementación inicial usa HTTP: el token y el audio no están cifrados dentro de la LAN. No abrir este puerto a Internet. Para redes compartidas, implementar TLS con validación de certificado también en el firmware; no basta cambiar la URL.

Configurar en el firmware la dirección IPv4 del PC y exactamente el mismo token. Una reserva DHCP evita cambios de dirección. Una petición real de prueba puede enviarse con `python -m scripts.smoke_client --input grabacion.wav --output respuesta.wav`. La entrada debe tener cabecera WAV canónica de 44 bytes, PCM16 mono a 16000 Hz, entre 0,1 y 8 segundos. Silencio de prueba en modo local puede producir `422 No speech detected`, lo cual es intencionado.

## Decisiones y límites

- Una petición activa por proceso; arrancar con **un worker**. Las demás reciben 503. El dispositivo debe liberar el pulsador y reintentar; no se reenvían comandos de voz automáticamente.
- Carga máxima de 256044 bytes y 10 s para recibirla. Inferencia total limitada a 115 s, configurables de 1 a 120 s. STT tiene límite de 50 s, Ollama 55 s y TTS 30 s; el límite total prevalece. El cliente espera 150 s.
- STT y Piper se ejecutan sin shell en subprocesos cancelables. Los procesos se terminan y recogen al agotarse el tiempo. Cada comando vuelve a cargar los modelos: mejora el aislamiento de fallos, pero aumenta la latencia. Un PC lento puede requerir `faster-whisper-tiny` o un LLM más pequeño; medirlo antes de uso continuo.
- La respuesta LLM se limita a 100 tokens y 400 caracteres para TTS. Audio de salida máximo 20 s: una respuesta más larga se recorta con desvanecimiento de 5 ms. La aplicación usa remuestreo polifásico con filtro antialias y margen digital de volumen; no sustituye la calibración del altavoz.
- No se guardan grabaciones, transcripciones ni respuestas en disco y no se imprimen en logs. Pasan por RAM y pipes; Piper recibe texto UTF-8 por stdin. El aislamiento entre usuarios del PC queda fuera de este prototipo.
- No hay palabra de activación, cancelación de eco, historial, ejecución de herramientas ni control de aparatos. El dispositivo utiliza pulsar para hablar y reproducción semidúplex.
- `/healthz` solo acredita que el servicio responde. No comprueba STT, LLM, TTS, red del dispositivo ni hardware.

Variables completas en `.env.example`; el archivo no se carga automáticamente. `PIPER_COMMAND_JSON` acepta una lista JSON de argumentos, por ejemplo `["C:/ruta/python.exe", "-m", "piper"]`; nunca una cadena para interpretar con shell. El JSON de voz debe estar junto al ONNX con sufijo `.onnx.json`.

## Fuentes de integración

- [faster-whisper: API y requisitos](https://github.com/SYSTRAN/faster-whisper).
- [Ollama: POST /api/chat](https://docs.ollama.com/api/chat).
- [Piper: CLI y modelos](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md).
- [FastAPI: respuestas binarias](https://fastapi.tiangolo.com/advanced/custom-response/).

Las pruebas automatizadas no demuestran reconocimiento de voz ni calidad de conversación. Consultar el [informe de validación](../docs/validation.md) para la evidencia ejecutada.

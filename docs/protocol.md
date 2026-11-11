# Protocolo Mesa Voice v1

Transporte HTTP/1.1 sobre LAN. El firmware inicia cada intercambio al finalizar una grabación activada por pulsador. No hay conexión persistente ni websocket. Entrada y salida se almacenan completas en RAM dentro de los límites definidos; no se requiere decodificador MP3.

```http
POST /v1/voice HTTP/1.1
Host: 192.168.1.10:8000
Authorization: Bearer <token aleatorio de al menos 32 caracteres ASCII sin espacios>
Content-Type: audio/wav
Content-Length: <44 + 2*N>
Connection: close

<WAV binario>
```

Entrada: WAV RIFF little endian, cabecera **exacta de 44 bytes**; `fmt ` de 16 bytes, formato 1 (PCM), un canal, 16000 Hz, 32000 bytes/s, blockAlign=2, 16 bits, bloque `data` inmediatamente después. No se aceptan metadatos, WAV extensible ni bloques adicionales. `N` debe estar entre 1600 y 128000 muestras inclusive (0,1–8 s). Máximo 256044 bytes. Tamaños RIFF y data deben coincidir con el cuerpo HTTP. `Content-Length` recomendado y obligatorio en el firmware; el servidor también limita carga chunked.

Respuesta correcta: HTTP 200, `Content-Type: audio/wav`, `Content-Length` fijo, `Cache-Control: no-store`, `X-Mesa-Mode: local|mock`. Mismo formato canónico PCM16 mono 16000 Hz; hasta 320000 muestras / 640044 bytes / 20 s. Validar todos los campos y límites antes de reproducir. Modo mock: tono de 440 Hz, 250 ms, sin inferencia.

| Estado | Significado | Acción del dispositivo |
|---|---|---|
| 400 | Cabecera HTTP o longitud incorrecta | Indicar error; corregir protocolo |
| 401 | Token ausente o incorrecto | Indicar error; revisar configuración |
| 408 | La carga tardó más de 10 s | Volver a reposo |
| 413 | Entrada supera el límite | Revisar límite de grabación |
| 415 | Content-Type distinto de audio/wav | Corregir cliente |
| 422 | WAV inválido, demasiado corto o sin habla | Volver a reposo; pedir repetir |
| 502 | Fallo STT, LLM, TTS o respuesta inválida | Indicar error; revisar servidor |
| 503 | Servidor ocupado | Volver a reposo; `Retry-After: 2` orientativo |
| 504 | Tiempo de inferencia agotado | Indicar error y volver a reposo |

Errores FastAPI: cuerpo JSON `{"detail":"..."}`; nunca tratarlo como audio. No reenviar automáticamente un POST tras un error de red, porque el servidor pudo haberlo procesado. El usuario puede iniciar una nueva grabación.

Plazo máximo del servidor: 10 s de recepción + 115 s de procesamiento (configurable hasta 120 s); timeout del cliente 150 s. Un worker y una petición activa. Desconexión del cliente no garantiza cancelación inmediata, pero el plazo de inferencia continúa aplicándose. Las respuestas son semidúplex: no grabar mientras suena el altavoz.

`GET /healthz` devuelve `{"status":"ok","mode":"mock|local","protocol":1}` sin autenticación. Solo sirve de liveness.

El prototipo usa token en una LAN de confianza; HTTP no cifra el audio ni autentica criptográficamente el servidor. No publicar en Internet. El token debe ser distinto para cada instalación y no debe incluirse en Git ni en logs.

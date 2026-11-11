#include <Arduino.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include <esp_heap_caps.h>
#include "audio_protocol.h"
#if defined(MESA_VALIDATION_BUILD)
#include "config.validation.h"
#elif __has_include("secrets.h")
#include "secrets.h"
#else
#include "config.example.h"
#endif

namespace {
constexpr int PTT_PIN = 1, LED_PIN = 2, MUTE_PIN = 4;
constexpr int TX_BCLK = 5, TX_LRCLK = 6, TX_DATA = 43;
constexpr int MIC_CLK = 42, MIC_DATA = 41;
constexpr uint32_t BUTTON_DEBOUNCE_MS = 30;
constexpr uint32_t CONNECT_TIMEOUT_MS = 5000;
constexpr uint32_t HTTP_TIMEOUT_MS = 150000;
constexpr uint32_t HTTP_BODY_TIMEOUT_MS = 30000;
constexpr size_t MAX_HEADER_BYTES = 4096;
constexpr size_t MAX_LINE_BYTES = 256;
uint8_t *capture = nullptr;
uint8_t *reply = nullptr;
bool ready = false;
bool rxInstalled = false, txInstalled = false;
bool buttonStable = false, buttonRaw = false;
uint32_t buttonChanged = 0, lastConnectAttempt = 0;

void mute() { digitalWrite(MUTE_PIN, HIGH); }
void led(bool on) { digitalWrite(LED_PIN, on ? HIGH : LOW); }
bool elapsed(uint32_t start, uint32_t period) { return uint32_t(millis() - start) >= period; }

bool buttonPressed() {
  const bool raw = digitalRead(PTT_PIN) == LOW;
  if (raw != buttonRaw) { buttonRaw = raw; buttonChanged = millis(); }
  if (elapsed(buttonChanged, BUTTON_DEBOUNCE_MS)) buttonStable = buttonRaw;
  return buttonStable;
}

void failure(const char *reason) {
  mute();
  Serial.printf("Error: %s\n", reason);
  for (int i = 0; i < 3; ++i) { led(true); delay(120); led(false); delay(120); }
}

bool configureAudio() {
  i2s_config_t rx = {};
  rx.mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM);
  rx.sample_rate = audio::RATE;
  rx.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  rx.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
  rx.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  rx.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  rx.dma_buf_count = 4; rx.dma_buf_len = 256;
  rx.use_apll = false;
  i2s_pin_config_t rp = {};
  rp.mck_io_num = I2S_PIN_NO_CHANGE;
  rp.bck_io_num = I2S_PIN_NO_CHANGE; rp.ws_io_num = MIC_CLK;
  rp.data_out_num = I2S_PIN_NO_CHANGE; rp.data_in_num = MIC_DATA;
  if (i2s_driver_install(I2S_NUM_0, &rx, 0, nullptr) != ESP_OK) return false;
  rxInstalled = true;
  if (i2s_set_pin(I2S_NUM_0, &rp) != ESP_OK || i2s_stop(I2S_NUM_0) != ESP_OK) return false;

  i2s_config_t tx = {};
  tx.mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_TX);
  tx.sample_rate = audio::RATE;
  tx.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  tx.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  tx.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  tx.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  tx.dma_buf_count = 4; tx.dma_buf_len = 256;
  tx.use_apll = false; tx.tx_desc_auto_clear = true;
  i2s_pin_config_t tp = {};
  tp.mck_io_num = I2S_PIN_NO_CHANGE;
  tp.bck_io_num = TX_BCLK; tp.ws_io_num = TX_LRCLK;
  tp.data_out_num = TX_DATA; tp.data_in_num = I2S_PIN_NO_CHANGE;
  if (i2s_driver_install(I2S_NUM_1, &tx, 0, nullptr) != ESP_OK) return false;
  txInstalled = true;
  if (i2s_set_pin(I2S_NUM_1, &tp) != ESP_OK || i2s_stop(I2S_NUM_1) != ESP_OK) return false;
  return true;
}

bool reconnectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  if (!elapsed(lastConnectAttempt, 10000)) return false;
  lastConnectAttempt = millis();
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Conectando Wi-Fi...");
  return false;
}

bool writeAll(WiFiClient &client, const uint8_t *data, size_t len, uint32_t start, uint32_t timeout) {
  size_t sent = 0;
  while (sent < len && !elapsed(start, timeout)) {
    if (!client.connected()) return false;
    const size_t block = min(size_t(1024), len - sent);
    size_t n = client.write(data + sent, block);
    sent += n;
    delay(1);
  }
  return sent == len;
}

bool readExact(WiFiClient &client, uint8_t *data, size_t len, uint32_t start, uint32_t timeout) {
  size_t got = 0;
  while (got < len && !elapsed(start, timeout)) {
    const int available = client.available();
    if (available > 0) {
      const size_t n = min(size_t(available), len - got);
      const int count = client.read(data + got, n);
      if (count > 0) got += size_t(count);
    } else if (!client.connected()) return false;
    delay(1);
  }
  return got == len;
}

bool readLine(WiFiClient &client, String &line, size_t &headerBytes, uint32_t start) {
  line = "";
  while (!elapsed(start, HTTP_TIMEOUT_MS)) {
    if (client.available() > 0) {
      const int c = client.read();
      if (c < 0) continue;
      if (++headerBytes > MAX_HEADER_BYTES) return false;
      if (c == '\n') {
        if (!line.endsWith("\r")) return false;
        line.remove(line.length() - 1); return true;
      }
      if (line.length() >= MAX_LINE_BYTES) return false;
      line += char(c);
    } else if (!client.connected()) return false;
    delay(1);
  }
  return false;
}

bool parseLength(const String &value, size_t &length) {
  if (!value.length()) return false;
  uint32_t n = 0;
  for (size_t i = 0; i < value.length(); ++i) {
    if (value[i] < '0' || value[i] > '9') return false;
    n = n * 10 + uint32_t(value[i] - '0');
    if (n > audio::HEADER + audio::MAX_REPLY_BYTES) return false;
  }
  length = n; return length >= audio::HEADER;
}

bool exchangeAudio(size_t captureBytes, size_t &pcmBytes) {
  WiFiClient client;
  client.setTimeout(5); // WiFiClient socket timeout is seconds; reads below use explicit millis deadlines.
  if (!client.connect(SERVER_HOST, SERVER_PORT, CONNECT_TIMEOUT_MS)) return false;
  String request = String("POST /v1/voice HTTP/1.1\r\nHost: ") + SERVER_HOST + ":" + SERVER_PORT +
    "\r\nAuthorization: Bearer " + API_TOKEN + "\r\nContent-Type: audio/wav\r\nAccept: audio/wav\r\nConnection: close\r\nContent-Length: " +
    String(captureBytes + audio::HEADER) + "\r\n\r\n";
  uint32_t start = millis();
  if (!writeAll(client, reinterpret_cast<const uint8_t *>(request.c_str()), request.length(), start, 15000) ||
      !writeAll(client, capture, captureBytes + audio::HEADER, start, 15000)) { client.stop(); return false; }
  // Response deadline starts after upload. There is no automatic retry: that could repeat an action.
  start = millis();
  size_t headerBytes = 0, contentLength = 0;
  bool seenLength = false, seenType = false, unsupported = false;
  String line;
  if (!readLine(client, line, headerBytes, start) ||
      !(line.startsWith("HTTP/1.1 200 ") || line.startsWith("HTTP/1.0 200 "))) {
    client.stop(); return false;
  }
  while (true) {
    if (!readLine(client, line, headerBytes, start)) { client.stop(); return false; }
    if (!line.length()) break;
    int colon = line.indexOf(':');
    if (colon <= 0) { client.stop(); return false; }
    String key = line.substring(0, colon), value = line.substring(colon + 1);
    key.toLowerCase(); value.trim();
    if (key == "content-length") {
      if (seenLength || !parseLength(value, contentLength)) { client.stop(); return false; }
      seenLength = true;
    } else if (key == "content-type") {
      value.toLowerCase();
      if (seenType || value != "audio/wav") { client.stop(); return false; }
      seenType = true;
    } else if (key == "transfer-encoding" || key == "content-encoding") unsupported = true;
  }
  if (!seenLength || !seenType || unsupported) { client.stop(); return false; }
  start = millis();
  if (!readExact(client, reply, contentLength, start, HTTP_BODY_TIMEOUT_MS)) { client.stop(); return false; }
  client.stop();
  return audio::validateReplyHeader(reply, contentLength, pcmBytes);
}

size_t recordVoice() {
  mute();
  if (i2s_start(I2S_NUM_0) != ESP_OK) return 0;
  // Drain all four DMA buffers and let the decimator settle (~64ms).
  uint8_t discard[512];
  for (int i = 0; i < 4; ++i) {
    size_t discarded = 0;
    if (i2s_read(I2S_NUM_0, discard, sizeof(discard), &discarded, pdMS_TO_TICKS(200)) != ESP_OK ||
        discarded != sizeof(discard)) {
      i2s_stop(I2S_NUM_0); return 0;
    }
  }
  led(true);
  size_t bytes = 0;
  uint32_t began = millis();
  bool ok = true;
  while (buttonPressed() && bytes < audio::MAX_CAPTURE_BYTES && !elapsed(began, 9000)) {
    size_t got = 0;
    const size_t wanted = min(size_t(512), audio::MAX_CAPTURE_BYTES - bytes);
    if (i2s_read(I2S_NUM_0, capture + audio::HEADER + bytes, wanted, &got, pdMS_TO_TICKS(200)) != ESP_OK || !got || got % 2) {
      ok = false; break;
    }
    bytes += got;
  }
  i2s_stop(I2S_NUM_0); led(false);
  if (!ok || bytes < audio::MIN_CAPTURE_BYTES) return 0;
  audio::makeHeader(capture, bytes);
  return bytes;
}

bool writeStereo(const int16_t *data, size_t bytes) {
  size_t sent = 0;
  const uint32_t began = millis();
  while (sent < bytes && !elapsed(began, 1000)) {
    size_t written = 0;
    if (i2s_write(I2S_NUM_1, reinterpret_cast<const uint8_t *>(data) + sent, bytes - sent,
                  &written, pdMS_TO_TICKS(200)) != ESP_OK || written == 0) return false;
    sent += written;
  }
  return sent == bytes;
}

bool playVoice(size_t pcmBytes) {
  mute();
  if (i2s_zero_dma_buffer(I2S_NUM_1) != ESP_OK || i2s_start(I2S_NUM_1) != ESP_OK) return false;
  int16_t stereo[512] = {};
  bool ok = writeStereo(stereo, sizeof(stereo));
  if (ok) { delay(20); digitalWrite(MUTE_PIN, LOW); }
  const size_t samples = pcmBytes / 2;
  for (size_t pos = 0; ok && pos < samples; pos += 256) {
    const size_t n = min(size_t(256), samples - pos);
    for (size_t i = 0; i < n; ++i) {
      int32_t value = audio::limitSample(int16_t(audio::read16(reply + audio::HEADER + (pos + i) * 2)));
      // 5ms fade to reduce switching transients.
      const size_t sample = pos + i;
      if (sample < 80) value = value * int32_t(sample) / 80;
      if (samples - sample < 80) value = value * int32_t(samples - sample) / 80;
      stereo[2 * i] = int16_t(value); stereo[2 * i + 1] = int16_t(value);
    }
    ok = writeStereo(stereo, n * 4);
  }
  if (ok) {
    memset(stereo, 0, sizeof(stereo));
    // More than the four DMA buffers: drains the final voice frames before muting.
    for (int i = 0; i < 6 && ok; ++i) ok = writeStereo(stereo, sizeof(stereo));
  }
  mute(); i2s_stop(I2S_NUM_1); return ok;
}

bool validConfig() {
  if (!strlen(WIFI_SSID) || strlen(API_TOKEN) < 32 || !strlen(SERVER_HOST) || !SERVER_PORT) return false;
  for (const char *p = SERVER_HOST; *p; ++p)
    if (!(isalnum(static_cast<unsigned char>(*p)) || *p == '-' || *p == '.')) return false;
  for (const char *p = API_TOKEN; *p; ++p)
    if (*p <= ' ' || *p > '~') return false;
  return true;
}
} // namespace

void setup() {
  digitalWrite(MUTE_PIN, HIGH); pinMode(MUTE_PIN, OUTPUT); mute();
  pinMode(LED_PIN, OUTPUT); led(false); pinMode(PTT_PIN, INPUT_PULLUP);
  Serial.begin(115200); delay(150);
  Serial.println("Mesa Voice r1: PTT local, sin palabra de activacion.");
  if (!validConfig()) { failure("Configure include/secrets.h (SSID, servidor y token >=32 caracteres)"); return; }
  if (!psramFound()) { failure("PSRAM no detectada"); return; }
  capture = static_cast<uint8_t *>(heap_caps_malloc(audio::HEADER + audio::MAX_CAPTURE_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  reply = static_cast<uint8_t *>(heap_caps_malloc(audio::HEADER + audio::MAX_REPLY_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!capture || !reply) { failure("Memoria insuficiente"); return; }
  if (!configureAudio()) {
    if (rxInstalled) i2s_driver_uninstall(I2S_NUM_0);
    if (txInstalled) i2s_driver_uninstall(I2S_NUM_1);
    failure("No se pudo iniciar I2S"); return;
  }
  WiFi.mode(WIFI_STA); WiFi.persistent(false); WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD); lastConnectAttempt = millis();
  ready = true;
}

void loop() {
  if (!ready) { mute(); led((millis() % 1200) < 120); delay(10); return; }
  static bool waitingForRelease = false;
  const bool pressed = buttonPressed();
  if (!pressed) waitingForRelease = false;
  if (!reconnectWifi()) { mute(); led((millis() % 2000) < 80); delay(10); return; }
  led(false);
  if (pressed && !waitingForRelease) {
    waitingForRelease = true;
    const size_t captured = recordVoice();
    if (!captured) failure("Grabacion demasiado corta o fallo de microfono");
    else {
      led(true);
      size_t pcmBytes = 0;
      if (!exchangeAudio(captured, pcmBytes)) failure("Servidor sin respuesta valida (revise backend, red y token)");
      else if (!playVoice(pcmBytes)) failure("Fallo de reproduccion I2S");
      led(false);
      // Erase the two application buffers after use; DMA copies are not secure-erased.
      memset(capture, 0, audio::HEADER + audio::MAX_CAPTURE_BYTES);
      memset(reply, 0, audio::HEADER + audio::MAX_REPLY_BYTES);
    }
  }
  delay(5);
}

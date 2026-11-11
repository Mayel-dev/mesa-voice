#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>

namespace audio {
constexpr uint32_t RATE = 16000;
constexpr size_t HEADER = 44;
constexpr size_t MAX_CAPTURE_BYTES = RATE * 2 * 8;
constexpr size_t MIN_CAPTURE_BYTES = RATE * 2 / 10;
constexpr size_t MAX_REPLY_BYTES = RATE * 2 * 20;
inline uint16_t read16(const uint8_t *p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
inline uint32_t read32(const uint8_t *p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
inline void write16(uint8_t *p, uint16_t n) { p[0] = uint8_t(n); p[1] = uint8_t(n >> 8); }
inline void write32(uint8_t *p, uint32_t n) {
  p[0] = uint8_t(n); p[1] = uint8_t(n >> 8); p[2] = uint8_t(n >> 16); p[3] = uint8_t(n >> 24);
}
inline void makeHeader(uint8_t *p, size_t pcmBytes) {
  memcpy(p, "RIFF", 4); write32(p + 4, uint32_t(36 + pcmBytes));
  memcpy(p + 8, "WAVEfmt ", 8); write32(p + 16, 16);
  write16(p + 20, 1); write16(p + 22, 1); write32(p + 24, RATE);
  write32(p + 28, RATE * 2); write16(p + 32, 2); write16(p + 34, 16);
  memcpy(p + 36, "data", 4); write32(p + 40, uint32_t(pcmBytes));
}
// Contract deliberately accepts only canonical WAV; arbitrary chunks are rejected.
inline bool validateReplyHeader(const uint8_t *p, size_t bytes, size_t &pcmBytes) {
  if (bytes < HEADER || bytes > HEADER + MAX_REPLY_BYTES) return false;
  if (memcmp(p, "RIFF", 4) || memcmp(p + 8, "WAVEfmt ", 8) || memcmp(p + 36, "data", 4)) return false;
  if (read32(p + 4) != bytes - 8 || read32(p + 16) != 16) return false;
  if (read16(p + 20) != 1 || read16(p + 22) != 1 || read32(p + 24) != RATE) return false;
  if (read32(p + 28) != RATE * 2 || read16(p + 32) != 2 || read16(p + 34) != 16) return false;
  pcmBytes = read32(p + 40);
  return pcmBytes > 0 && pcmBytes % 2 == 0 && pcmBytes == bytes - HEADER;
}
inline int16_t limitSample(int16_t s) {
  // Quarter-scale bound, then clip; a bounded digital level is not an acoustic SPL guarantee.
  const int32_t value = int32_t(s) / 4;
  return int16_t(value > 8192 ? 8192 : (value < -8192 ? -8192 : value));
}
} // namespace audio


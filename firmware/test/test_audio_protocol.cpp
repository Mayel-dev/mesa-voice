#include "audio_protocol.h"
#include <assert.h>
#include <stdio.h>

int main() {
  uint8_t header[44] = {};
  size_t n = 123;
  audio::makeHeader(header, 32000);
  assert(audio::validateReplyHeader(header, 32044, n) && n == 32000);
  assert(!audio::validateReplyHeader(header, 43, n));
  assert(!audio::validateReplyHeader(header, 32046, n));
  header[0] = 'X'; assert(!audio::validateReplyHeader(header, 32044, n)); header[0] = 'R';
  header[22] = 2; assert(!audio::validateReplyHeader(header, 32044, n)); header[22] = 1;
  header[20] = 3; assert(!audio::validateReplyHeader(header, 32044, n)); header[20] = 1;
  header[34] = 24; assert(!audio::validateReplyHeader(header, 32044, n)); header[34] = 16;
  header[24] ^= 1; assert(!audio::validateReplyHeader(header, 32044, n)); header[24] ^= 1;
  header[28] ^= 1; assert(!audio::validateReplyHeader(header, 32044, n)); header[28] ^= 1;
  audio::makeHeader(header, audio::MAX_REPLY_BYTES);
  assert(audio::validateReplyHeader(header, 44 + audio::MAX_REPLY_BYTES, n));
  audio::makeHeader(header, audio::MAX_REPLY_BYTES + 2);
  assert(!audio::validateReplyHeader(header, 44 + audio::MAX_REPLY_BYTES + 2, n));
  audio::makeHeader(header, 0); assert(!audio::validateReplyHeader(header, 44, n));
  audio::makeHeader(header, 1); assert(!audio::validateReplyHeader(header, 45, n));
  audio::makeHeader(header, 2); assert(audio::validateReplyHeader(header, 46, n) && n == 2);
  for (int32_t input = -32768; input <= 32767; ++input) {
    const int32_t output = audio::limitSample(int16_t(input));
    assert(output >= -8192 && output <= 8192);
    assert(output == input / 4);
  }
  puts("PASS: canonical WAV acceptance/rejection boundaries and all 65536 PCM16 limiter inputs");
  return 0;
}

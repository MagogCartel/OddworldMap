// Decode an AO PS1 .CAM "Bits" chunk (strips of MDEC BS frames) to raw RGBA32.
// Usage: cam2rgba <bits_payload_file> <out_rgba_file>
// Output: width(u32) height(u32) followed by width*height*4 bytes RGBA.
//
// Build (done automatically by build_map.py):
//   c++ -O2 -std=c++17 -I. -include Types.hpp cam2rgba.cpp PSXMDECDecoder.cpp -o cam2rgba
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include "Types.hpp"
#include "PSXMDECDecoder.h"

static const int STRIP_W = 32;
static const int CAM_H = 240;

int main(int argc, char** argv)
{
    if (argc != 3)
    {
        fprintf(stderr, "usage: cam2rgba <bits_payload> <out_rgba>\n");
        return 1;
    }
    FILE* f = fopen(argv[1], "rb");
    if (!f) { perror("open input"); return 1; }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    std::vector<uint8_t> bits(size);
    fread(bits.data(), 1, size, f);
    fclose(f);

    std::vector<std::vector<uint8_t>> strips;
    PSXMDECDecoder decoder;

    long pos = 0;
    while (pos + 2 <= size)
    {
        uint16_t stripLen;
        memcpy(&stripLen, &bits[pos], 2);
        pos += 2;
        if (stripLen == 0 || pos + stripLen > size + 64)
            break;

        // BS frame: decode STRIP_W x CAM_H RGBA.
        // The VLC reader can overrun the coded data, so decode from a
        // zero-padded scratch copy instead of the raw file buffer.
        std::vector<uint8_t> scratch(stripLen + 0x10000, 0);
        memcpy(scratch.data(), &bits[pos], std::min<long>(stripLen, size - pos));
        std::vector<uint8_t> out(STRIP_W * CAM_H * 4 + 0x10000);
        decoder.DecodeFrameToRGBA32(
            reinterpret_cast<uint16_t*>(out.data()),
            reinterpret_cast<uint16_t*>(scratch.data()),
            STRIP_W, CAM_H);
        out.resize(STRIP_W * CAM_H * 4);
        strips.push_back(std::move(out));
        pos += stripLen;
    }

    const int W = STRIP_W * (int)strips.size();
    FILE* o = fopen(argv[2], "wb");
    if (!o) { perror("open output"); return 1; }
    uint32_t w32 = W, h32 = CAM_H;
    fwrite(&w32, 4, 1, o);
    fwrite(&h32, 4, 1, o);
    std::vector<uint8_t> row(W * 4);
    for (int y = 0; y < CAM_H; y++)
    {
        for (size_t s = 0; s < strips.size(); s++)
        {
            memcpy(&row[s * STRIP_W * 4], &strips[s][y * STRIP_W * 4], STRIP_W * 4);
        }
        fwrite(row.data(), 1, row.size(), o);
    }
    fclose(o);
    return 0;
}

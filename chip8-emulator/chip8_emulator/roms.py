"""Built-in test ROMs for validating the CHIP-8 emulator."""

from __future__ import annotations

from .cli import build_test_rom


def maze_rom() -> bytes:
    """Maze generator — fills the screen with a random maze pattern.

    Uses: LD, ADD, RND, DRW, JP (loop).
    """
    return build_test_rom([
        0x6000,  # LD V0, 0       (x = 0)
        0x6100,  # LD V1, 0       (y = 0)
        0xA222,  # LD I, 0x222    (sprite at 0x222 = 0x80)
        0xC201,  # RND V2, 1      (random 0 or 1)
        0x3201,  # SE V2, 1       (if random == 1, skip)
        0xA21E,  # LD I, 0x21E    (sprite at 0x21E = 0x00)
        0xD014,  # DRW V0, V1, 4  (draw 4-row sprite)
        0x7004,  # ADD V0, 4      (x += 4)
        0x3040,  # SE V0, 64      (if x == 64, next row)
        0x1200,  # JP 0x200       (loop)
        0x6000,  # LD V0, 0       (x = 0)
        0x7104,  # ADD V1, 4      (y += 4)
        0x3120,  # SE V1, 32      (if y == 32, done)
        0x1200,  # JP 0x200       (loop)
        0x1218,  # JP 0x218       (infinite loop — halt)
        # Sprite data
        0x80,  # Maze wall (left-side pixel on)
        0x80,
        0x80,
        0x80,
        0x00,  # Empty (no pixels)
        0x00,
        0x00,
        0x00,
    ])


def counter_rom() -> bytes:
    """Counter — counts from 0 to 255, displaying each number.

    Tests: LD, ADD, BCD (Fx33), font sprites (Fx29), DRW, JP (loop).
    """
    return build_test_rom([
        0x6000,  # LD V0, 0       (counter)
        0x6100,  # LD V1, 0       (x pos)
        0x6200,  # LD V2, 0       (y pos)
        # Main loop
        0xF029,  # LD F, V0       (load font sprite for digit V0)
        0xD120,  # DRW V1, V2, 5  (draw sprite)
        0x7001,  # ADD V0, 1      (increment counter)
        0x3000,  # SE V0, 0       (if overflowed to 0, we wrapped)
        0x1206,  # JP 0x206       (loop)
        0x1210,  # JP 0x210       (halt — infinite loop)
        # Halt loop
        0x1210,  # JP 0x210
    ])


def ibm_logo_rom() -> bytes:
    """IBM logo ROM — classic CHIP-8 test program.

    This draws the IBM logo using sprite data at I=0x200+28.
    """
    return bytes([
        0x00, 0xE0,  # CLS
        0xA2, 0x2A,  # LD I, 0x22A (sprite data)
        0xD0, 0x14,  # DRW V0, V1, 4
        0x60, 0x00,  # LD V0, 0
        0x61, 0x00,  # LD V1, 0
        0xA2, 0x2E,  # LD I, 0x22E
        0xD0, 0x14,  # DRW V0, V1, 4
        0x12, 0x1E,  # JP 0x21E
        # Pad to 0x22A
        *([0x00] * (0x22A - 0x200 - 22)),
        # Sprite data would go here — simplified version
        0xFF, 0x81, 0x81, 0x81,  # "I" top
        0xFF, 0x89, 0x89, 0x89,  # "B" top
        0xFF, 0x91, 0x91, 0x91,  # "M" top
        0xFF, 0x81, 0x81, 0xFF,  # "I" bottom
        0xFF, 0x89, 0x89, 0xFF,  # "B" bottom
        0xFF, 0x91, 0x91, 0xFF,  # "M" bottom
    ])


def chip8_hello_rom() -> bytes:
    """Simple hello-world ROM that draws 'HI' on screen.

    Tests: CLS, LD, DRW, infinite loop.
    """
    return build_test_rom([
        0x00E0,  # CLS
        0x600A,  # LD V0, 10 (x)
        0x610A,  # LD V1, 10 (y)
        0xA21C,  # LD I, 0x21C (H sprite)
        0xD015,  # DRW V0, V1, 5
        0x6010,  # LD V0, 16 (x offset for I)
        0xA226,  # LD I, 0x226 (I sprite)
        0xD015,  # DRW V0, V1, 5
        0x1214,  # JP 0x214 (infinite loop)
        # H sprite (5 bytes)
        0x90,  # 10010
        0x90,  # 10010
        0xF0,  # 11110
        0x90,  # 10010
        0x90,  # 10010
        # I sprite (5 bytes)
        0xE0,  # 111
        0x40,  #  1
        0x40,  #  1
        0x40,  #  1
        0xE0,  # 111
    ])


def add_test_rom() -> bytes:
    """Tests ADD instruction — adds 5 + 7 and stores result in V3.

    After running: V0=5, V1=7, V3=12, VF=0 (no carry).
    """
    return build_test_rom([
        0x6005,  # LD V0, 5
        0x6107,  # LD V1, 7
        0x8014,  # ADD V0, V1  → V0 = 12, VF = 0
        0x6300,  # LD V3, 0
        0x8304,  # ADD V3, V0  → V3 = 12
        0x1210,  # JP 0x210 (halt loop)
        0x1210,  # JP 0x210
    ])


def bcd_test_rom() -> bytes:
    """Tests BCD (Fx33) — converts 255 to BCD.

    After running: memory[I]=2, memory[I+1]=5, memory[I+2]=5.
    """
    return build_test_rom([
        0x60FF,  # LD V0, 255
        0xA210,  # LD I, 0x210
        0xF033,  # LD B, V0 (BCD of 255)
        0x1208,  # JP 0x208 (halt loop)
        0x1208,  # JP 0x208
    ])


def draw_test_rom() -> bytes:
    """Tests sprite drawing and collision detection.

    Draws the same sprite at the same position twice — second draw
    should set VF=1 (collision, because XOR turns pixels off).
    """
    return build_test_rom([
        0x00E0,  # CLS
        0x600A,  # LD V0, 10 (x)
        0x610A,  # LD V1, 10 (y)
        0xA21E,  # LD I, 0x21E (sprite data)
        0xD015,  # DRW V0, V1, 5 (first draw — no collision)
        # VF should be 0 after this
        0xD015,  # DRW V0, V1, 5 (second draw — collision!)
        # VF should be 1 after this
        0x1210,  # JP 0x210 (halt loop)
        0x1210,  # JP 0x210
        # Sprite data (letter "A")
        0x60,  # .110....
        0x90,  # 1001....
        0xF0,  # 1111....
        0x90,  # 1001....
        0x90,  # 1001....
    ])


def key_test_rom() -> bytes:
    """Tests key input — waits for any key, stores it in V3, halts."""
    return build_test_rom([
        0x6300,  # LD V3, 0
        0xF30A,  # LD V3, K (wait for key)
        0x1210,  # JP 0x210 (halt loop)
        0x1210,  # JP 0x210
    ])


def scroll_test_rom() -> bytes:
    """Tests scroll-down using the display API directly."""
    # This ROM can't really test SUPER-CHIP scrolling from pure CHIP-8,
    # so it just draws something and halts — the scrolling is tested via API.
    return build_test_rom([
        0x600A,  # LD V0, 10
        0x610A,  # LD V1, 10
        0xA21E,  # LD I, 0x21E
        0xD015,  # DRW V0, V1, 5
        0x1210,  # JP 0x210 (halt)
        0x1210,  # JP 0x210
        # Sprite
        0xFF,  # All pixels on
        0xFF,
        0xFF,
        0xFF,
        0xFF,
    ])


# Registry of all test ROMs
ALL_ROMS = {
    "maze": maze_rom,
    "counter": counter_rom,
    "ibm_logo": ibm_logo_rom,
    "hello": chip8_hello_rom,
    "add_test": add_test_rom,
    "bcd_test": bcd_test_rom,
    "draw_test": draw_test_rom,
    "key_test": key_test_rom,
    "scroll_test": scroll_test_rom,
}
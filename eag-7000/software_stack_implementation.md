# EAG-7000 — Phase 4: Foundational Software Stack & Implementation

---

## 4.1 Software Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    USER SPACE (Linux)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ AI Runtime│  │ Network  │  │ Sensor   │  │ CAN-FD   │    │
│  │ (ONNX/TF) │  │ Stack    │  │ Manager  │  │ Gateway  │    │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│        │             │             │             │            │
│  ┌─────┴─────────────┴─────────────┴─────────────┴─────┐    │
│  │              SYSTEM SERVICES (systemd)                │    │
│  │  D-Bus │ NWManager │ journal │ udev │ watchdog      │    │
│  └─────────────────────┬───────────────────────────────┘    │
├─────────────────────────┼────────────────────────────────────┤
│                    KERNEL SPACE                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ NPU Driver│  │ Ethernet │  │ V4L2/ISP │  │ CAN      │    │
│  │ (hailo.ko)│  │ (FEC+PHY)│  │ Driver   │  │ (mcp251xfd)│   │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│        │             │             │             │            │
│  ┌─────┴─────────────┴─────────────┴─────────────┴─────┐    │
│  │            ARM64 LINUX KERNEL 6.6.x (NXP BSP)      │    │
│  │  Scheduler │ MMU │ IRQ │ DMA │ Power Mgmt │ TrustZone│   │
│  └─────────────────────┬───────────────────────────────┘    │
├─────────────────────────┼────────────────────────────────────┤
│                BOOTLOADER SPACE                              │
│  ┌─────────────────────┴───────────────────────────────┐    │
│  │  SPL (Secondary Program Loader) — DDR init, PMIC    │    │
│  │  ┌─────────────────────────────────────────────────┐│    │
│  │  │  U-Boot 2024.04 (i.MX8MP) — eMMC boot, FIT Image│    │
│  │  └─────────────────────────────────────────────────┘│    │
│  └───────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│                SECURE BOOT ROM (i.MX8MP on-chip)             │
│  eFuse OTP → RSA-4096 root key → SPL signature verify      │
└──────────────────────────────────────────────────────────────┘
```

### 4.1.1 Boot Sequence

| Stage | Component | Storage | Function | Duration Target |
|---|---|---|---|---|
| 0 | Boot ROM | On-chip (i.MX8MP) | Load SPL from eMMC, verify RSA signature | 50ms |
| 1 | SPL | eMMC boot1 partition | Initialize PMIC, configure DDR, load U-Boot proper | 200ms |
| 2 | U-Boot Proper | eMMC boot1 partition | Load FIT kernel image + DTB + initramfs from eMMC | 500ms |
| 3 | Linux Kernel | eMMC userdata partition (ext4) | Boot to userspace (systemd) | 2000ms |
| 4 | Userspace | eMMC rootfs | AI runtime, network stack, sensor services | 3000ms |
| **Total cold boot** | | | | **<6 seconds** |

### 4.1.2 Cortex-M4F Subsystem

The M4F core runs independently on FreeRTOS with its own firmware:

- **CAN-FD message processing** (real-time <100µs response)
- **Modbus RTU slave** (UART2, 115200 baud)
- **Watchdog monitoring** of A72 Linux via heartbeat
- **Power state control** (trigger A72 sleep/wake via MU mailbox)

M4F firmware is loaded by A72 Linux via remoteproc after kernel boot.

---

## 4.2 Register & MMIO Definitions

### 4.2.1 Base Address Map (i.MX8M Plus)

```c
/*
 * EAG-7000 Memory Map
 * Based on i.MX8M Plus Reference Manual (IMX8MPRM)
 * All addresses are physical; Linux device tree uses these
 * for ioremap() and DMA master IDs.
 */

#ifndef EAG7000_MMIO_H
#define EAG7000_MMIO_H

/* ============================================================================
 * Core Peripherals — ARM Cortex-A72 (64-bit) Address Space
 * ============================================================================ */

/* GIC-400 Interrupt Controller */
#define CCM_GIC_BASE            0x38880000UL
#define CCM_GIC_SIZE            0x00010000UL  /* 64KB */

/* Clock Control Module (CCM) */
#define CCM_BASE               0x30380000UL
#define CCM_SIZE               0x00010000UL  /* 64KB */

/* CCM Analytical Clock Root Registers */
#define CCM_ANAL_BASE          0x30360000UL
#define CCM_ANAL_SIZE          0x00010000UL

/* GPIO Registers (5 ports) */
#define GPIO1_BASE             0x30200000UL
#define GPIO2_BASE             0x30210000UL
#define GPIO3_BASE             0x30220000UL
#define GPIO4_BASE             0x30230000UL
#define GPIO5_BASE             0x30240000UL
#define GPIO_SIZE              0x00001000UL  /* 4KB per port */

/* IOMUXC (I/O Multiplexer) — Controls pin MUX and pad config */
#define IOMUXC_BASE            0x30330000UL
#define IOMUXC_SIZE            0x00010000UL  /* 64KB */

/* IOMUXC GPR (General Purpose Registers) */
#define IOMUXC_GPR_BASE        0x30340000UL
#define IOMUXC_GPR_SIZE        0x00010000UL

/* UART Registers */
#define UART1_BASE             0x30860000UL
#define UART2_BASE             0x30890000UL
#define UART3_BASE             0x30880000UL
#define UART4_BASE             0x30A60000UL
#define UART_SIZE              0x00001000UL

/* I2C Registers */
#define I2C1_BASE              0x30A20000UL
#define I2C2_BASE              0x30A30000UL
#define I2C3_BASE              0x30A40000UL
#define I2C_SIZE               0x00001000UL

/* SPI Registers (ECSPI) */
#define ECSPI1_BASE            0x30820000UL
#define ECSPI2_BASE            0x30830000UL
#define ECSPI3_BASE            0x30840000UL
#define ECSPI_SIZE             0x00001000UL

/* Ethernet MAC (FEC — Fast Ethernet Controller, enhanced for 2.5G) */
#define ENET1_BASE             0x30BE0000UL
#define ENET2_BASE             0x30BF0000UL
#define ENET_SIZE              0x00010000UL

/* USB Controller (DWC3) */
#define USB1_BASE              0x38100000UL
#define USB_SIZE               0x00020000UL

/* PCIe Controller */
#define PCIE1_BASE             0x33800000UL
#define PCIE_SIZE              0x01000000UL  /* 16MB (config + MMIO) */

/* MIPI-CSI2 RX */
#define MIPI_CSI1_BASE         0x32E40000UL
#define MIPI_CSI_SIZE          0x00010000UL

/* Image Signal Processor */
#define ISP_BASE               0x32E50000UL
#define ISP_SIZE               0x00010000UL

/* DMA Controller (eDMA) */
#define EDMA1_BASE             0x32C00000UL
#define EDMA_SIZE              0x00010000UL

/* System Counter / GPT Timers */
#define GPT1_BASE              0x302D0000UL
#define GPT2_BASE              0x302E0000UL
#define GPT_SIZE               0x00001000UL

/* Watchdog Timers */
#define WDOG1_BASE             0x30280000UL
#define WDOG2_BASE             0x30290000UL
#define WDOG3_BASE             0x302A0000UL
#define WDOG_SIZE              0x00001000UL

/* MU (Message Unit) — A72 ↔ M4F mailbox */
#define MU1_BASE               0x30AA0000UL
#define MU_SIZE                0x00001000UL

/* SRC (System Reset Controller) */
#define SRC_BASE               0x30390000UL
#define SRC_SIZE               0x00001000UL

/* Security Block (HAB / TrustZone) */
#define CAAM_BASE              0x30900000UL
#define CAAM_SIZE              0x00100000UL

/* ============================================================================
 * DRAM Address Map (configured by SPL)
 * ============================================================================ */
#define DRAM_BASE              0x40000000UL
#define DRAM_SIZE              0x80000000UL  /* 2GB (can be extended to 4GB) */

/* M4F TCM (Tightly Coupled Memory) — visible from A72 */
#define M4_TCM_BASE            0x007E0000UL
#define M4_TCM_SIZE            0x00020000UL  /* 128KB */

/* M4F Code ROM */
#define M4_ROM_BASE            0x00000000UL
#define M4_ROM_SIZE            0x00010000UL  /* 64KB */

#endif /* EAG7000_MMIO_H */
```

### 4.2.2 Register Bit Definitions — CCM (Clock Control Module)

```c
/*
 * EAG-7000 Clock Register Definitions
 * i.MX8M Plus CCM_ANAL register map for clock root configuration.
 */

#ifndef EAG7000_CCM_H
#define EAG7000_CCM_H

#include "eag7000_mmio.h"

/* ============================================================================
 * CCM_ANAL Clock Root Registers
 * Each clock root has a TARGET register (parent select + div) and
 * a MUX register. We define offsets from CCM_ANAL_BASE.
 * ============================================================================ */

/* ARM PLL (A72 core clock) */
#define CCM_ANAL_ARM_PLL_CFG0         0x0000
#define CCM_ANAL_ARM_PLL_CFG1         0x0004
#define CCM_ANAL_ARM_PLL_CFG2         0x0008
#define CCM_ANAL_ARM_PLL_STATUS       0x000C

/* DRAM PLL */
#define CCM_ANAL_DRAM_PLL_CFG0        0x0050
#define CCM_ANAL_DRAM_PLL_CFG1        0x0054
#define CCM_ANAL_DRAM_PLL_CFG2        0x0058
#define CCM_ANAL_DRAM_PLL_STATUS      0x005C

/* VIDEO PLL (ISP/display) */
#define CCM_ANAL_VIDEO_PLL1_CFG0      0x0098
#define CCM_ANAL_VIDEO_PLL1_CFG1      0x009C
#define CCM_ANAL_VIDEO_PLL1_CFG2      0x00A0
#define CCM_ANAL_VIDEO_PLL1_STATUS    0x00A4

/* ============================================================================
 * PLL Configuration Bit Masks
 * ============================================================================ */

/* PLL_CFG0 — Main control register */
#define PLL_CFG0_ENABLE_SHIFT         0
#define PLL_CFG0_ENABLE_MASK          (1U << 0)     /* PLL enable */
#define PLL_CFG0_BYPASS_SHIFT         4
#define PLL_CFG0_BYPASS_MASK          (1U << 4)     /* Bypass PLL */
#define PLL_CFG0_POWERDOWN_SHIFT      12
#define PLL_CFG0_POWERDOWN_MASK       (1U << 12)    /* Power down PLL */
#define PLL_CFG0_PLL_SEL_SHIFT        16
#define PLL_CFG0_PLL_SEL_MASK        (0x3U << 16)  /* Parent clock select */
#define PLL_CFG0_DIV_SEL_SHIFT        0
#define PLL_CFG0_DIV_SEL_MASK         (0x7FU << 0)  /* Main divider */

/* PLL_CFG1 — Fractional divider */
#define PLL_CFG1_FRAC_DIV_SHIFT       0
#define PLL_CFG1_FRAC_DIV_MASK        (0x1FFFFFU << 0) /* 24-bit frac div */

/* PLL_STATUS — Lock status */
#define PLL_STATUS_LOCK_SHIFT         0
#define PLL_STATUS_LOCK_MASK          (1U << 0)     /* PLL locked */
#define PLL_STATUS_PLL_READY_SHIFT    1
#define PLL_STATUS_PLL_READY_MASK     (1U << 1)    /* PLL ready */

/* ============================================================================
 * CCM Clock Root Target Registers (for peripheral clock enables)
 * ============================================================================ */

/* Clock root offsets — each has TARGET and MUX registers */
#define CCM_ROOT_ENET1_CLK            0x4A80  /* ETH0 clock root */
#define CCM_ROOT_ENET2_CLK            0x4AA0  /* ETH1 clock root */
#define CCM_ROOT_USB_CLK              0x4980  /* USB clock root */
#define CCM_ROOT_PCIE_CLK             0x4A00  /* PCIe clock root */
#define CCM_ROOT_SPI1_CLK             0x4780  /* SPI1 clock root */
#define CCM_ROOT_SPI2_CLK             0x47A0  /* SPI2 clock root */
#define CCM_ROOT_SPI3_CLK             0x47C0  /* SPI3 clock root */
#define CCM_ROOT_UART1_CLK            0x4A80  /* UART1 clock root */
#define CCM_ROOT_CAN_CLK              0x4C00  /* CAN clock root */

/* TARGET register fields */
#define CCM_ROOT_TARGET_ENABLE_SHIFT  0
#define CCM_ROOT_TARGET_ENABLE_MASK   (1U << 0)
#define CCM_ROOT_TARGET_MUX_SHIFT      8
#define CCM_ROOT_TARGET_MUX_MASK       (0x7U << 8)  /* 3-bit parent select */
#define CCM_ROOT_TARGET_DIV_SHIFT      0
#define CCM_ROOT_TARGET_DIV_MASK        (0xFFU << 0) /* 8-bit divider */

/* ============================================================================
 * Clock Parent Select Values (for MUX fields)
 * ============================================================================ */
#define CCM_PARENT_OSC_24M            0  /* 24 MHz main oscillator */
#define CCM_PARENT_SYS_PLL1_800M      1  /* SYS_PLL1 at 800 MHz */
#define CCM_PARENT_SYS_PLL2_500M      2  /* SYS_PLL2 at 500 MHz */
#define CCM_PARENT_SYS_PLL3_1200M     3  /* SYS_PLL3 at 1200 MHz */
#define CCM_PARENT_AUDIO_PLL1         4  /* Audio PLL1 (variable) */
#define CCM_PARENT_VIDEO_PLL1         5  /* Video PLL1 (variable) */
#define CCM_PARENT_ARM_PLL_800M       6  /* ARM PLL at 800 MHz */

/* ============================================================================
 * Target Clock Frequencies (EAG-7000 configuration)
 * ============================================================================ */
#define CLK_A72_CORE_FREQ             2000000000UL  /* 2.0 GHz (A72) */
#define CLK_M4_CORE_FREQ              800000000UL   /* 800 MHz (M4F) */
#define CLK_DDR_FREQ                  2133000000UL  /* 2133 MHz DDR clock */
#define CLK_PCIE_REF_FREQ             100000000UL   /* 100 MHz PCIe ref */
#define CLK_ENET_REF_FREQ             250000000UL   /* 250 MHz RGMII ref */
#define CLK_SPI_REF_FREQ              50000000UL    /* 50 MHz SPI bus */
#define CLK_UART_REF_FREQ             80000000UL    /* 80 MHz UART */
#define CLK_CAN_REF_FREQ              80000000UL    /* 80 MHz CAN-FD */
#define CLK_USB_REF_FREQ              480000000UL   /* 480 MHz USB PHY */

#endif /* EAG7000_CCM_H */
```

### 4.2.3 GPIO Register Definitions

```c
/*
 * EAG-7000 GPIO Register Definitions
 * i.MX8M Plus GPIO block — 5 ports, each with 32 GPIO pins.
 */

#ifndef EAG7000_GPIO_H
#define EAG7000_GPIO_H

#include "eag7000_mmio.h"

/* GPIO Register Offsets (within each GPIO port base) */
#define GPIO_DR          0x0000   /* Data Register — read/write pin state */
#define GPIO_GDIR        0x0004   /* Direction Register — 0=input, 1=output */
#define GPIO_PSR         0x0008   /* Pad Status Register — read pad level */
#define GPIO_ICR1        0x000C   /* Interrupt Configuration Register 1 (pins 0-15) */
#define GPIO_ICR2        0x0010   /* Interrupt Configuration Register 2 (pins 16-31) */
#define GPIO_IMR         0x0014   /* Interrupt Mask Register */
#define GPIO_ISR         0x0018   /* Interrupt Status Register (write-1-clear) */
#define GPIO_EDGE_SEL    0x001C   /* Edge Select Register */

/* ICR field values (per 2-bit field, 16 per register) */
#define GPIO_ICR_LOW_LEVEL     0x0U  /* IRQ on low level */
#define GPIO_ICR_HIGH_LEVEL    0x1U  /* IRQ on high level */
#define GPIO_ICR_RISING_EDGE   0x2U  /* IRQ on rising edge */
#define GPIO_ICR_FALLING_EDGE  0x3U  /* IRQ on falling edge */
#define GPIO_ICR_BOTH_EDGE     0x2U  /* Use EDGE_SEL for both edges */

/* ============================================================================
 * EAG-7000 GPIO Pin Assignments
 * Based on Phase 2 pinout table and IOMUX configuration.
 * ============================================================================ */

/* GPIO1 — System Control */
#define GPIO1_PCIE_RST_PIN     10   /* GPIO1_IO10 — PCIe reset (active-low) */
#define GPIO1_PCIE_WAKE_PIN    11   /* GPIO1_IO11 — PCIe WAKE (active-low) */
#define GPIO1_PCIE_CLKREQ_PIN  12   /* GPIO1_IO12 — PCIe CLKREQ (active-low) */
#define GPIO1_USB_HOST_PIN     13   /* GPIO1_IO13 — USB host/device select */
#define GPIO1_M4_BOOT_PIN     5    /* GPIO1_IO05 — M4F boot config strap */

/* GPIO3 — Sensor / Expansion */
#define GPIO3_I2C_MUX_RST_PIN  0    /* GPIO3_IO00 — I2C mux reset */
#define GPIO3_CAM_RST_PIN      1    /* GPIO3_IO01 — Camera sensor reset */
#define GPIO3_CAM_PWDN_PIN     2    /* GPIO3_IO02 — Camera sensor power down */
#define GPIO3_CAN1_EN_PIN      3    /* GPIO3_IO03 — CAN-FD #1 enable */
#define GPIO3_CAN2_EN_PIN      4    /* GPIO3_IO04 — CAN-FD #2 enable */
#define GPIO3_CAN1_STB_PIN     5    /* GPIO3_IO05 — CAN-FD #1 standby */
#define GPIO3_CAN2_STB_PIN     6    /* GPIO3_IO06 — CAN-FD #2 standby */

/* GPIO4 — Power / Status */
#define GPIO4_LED_STATUS_PIN   0    /* GPIO4_IO00 — Status LED (green) */
#define GPIO4_LED_ERROR_PIN    1    /* GPIO4_IO01 — Error LED (red) */
#define GPIO4_LED_ACT_PIN     2    /* GPIO4_IO02 — Activity LED (blue) */
#define GPIO4_POE_STATUS_PIN   3    /* GPIO4_IO03 — PoE+ status input */
#define GPIO4_RTC_IRQ_PIN     4    /* GPIO4_IO04 — RTC interrupt (active-low) */
#define GPIO4_NPU_IRQ_PIN     5    /* GPIO4_IO05 — Hailo-8 NPU interrupt */
#define GPIO4_WATCHDOG_PIN     6    /* GPIO4_IO06 — External watchdog feed */

#endif /* EAG7000_GPIO_H */
```

---

## 4.3 Low-Level Initialization Routines

### 4.3.1 Clock Configuration (SPL Stage — runs before DRAM init)

```c
/*
 * EAG-7000 Clock Initialization
 * Configures all PLLs and clock roots for target frequencies.
 * Called from SPL (Secondary Program Loader) before DDR init.
 *
 * Target configuration:
 *   ARM PLL  → 1600 MHz (A72 cores @ 2 GHz with /4 div + /2 turbo)
 *   DRAM PLL → 1066 MHz (DDR @ 2133 MT/s, 4x PLL = 4266 data rate)
 *   VIDEO PLL → 594 MHz (ISP)
 *   SYS_PLL1  → 800 MHz (peripheral base)
 *   SYS_PLL2  → 500 MHz (AXI bus)
 *   SYS_PLL3  → 1200 MHz (GPU)
 */

#include "eag7000_ccm.h"
#include "eag7000_mmio.h"
#include <stdint.h>

/* MMIO register access helpers */
static inline void mmio_write32(uintptr_t addr, uint32_t val)
{
    *(volatile uint32_t *)addr = val;
    __asm__ volatile("dsb sy" ::: "memory");  /* Data synchronization barrier */
}

static inline uint32_t mmio_read32(uintptr_t addr)
{
    uint32_t val = *(volatile uint32_t *)addr;
    __asm__ volatile("dsb sy" ::: "memory");
    return val;
}

/* Wait for PLL lock with timeout (1ms @ 24MHz ref = 24000 cycles) */
static int pll_wait_lock(uintptr_t status_reg, uint32_t timeout_loops)
{
    while (timeout_loops--) {
        if (mmio_read32(status_reg) & PLL_STATUS_LOCK_MASK) {
            return 0;  /* Lock achieved */
        }
    }
    return -1;  /* Lock timeout */
}

/*
 * Configure a fractional PLL to a target frequency.
 *
 * PLL output = (parent_freq * div_sel) / (2 * frac_div / 2^24)
 * For integer mode, frac_div = 0.
 *
 * @param pll_cfg0_base  Base address of PLL_CFG0 register
 * @param parent_freq    Parent oscillator frequency in Hz
 * @param target_freq    Desired PLL output frequency in Hz
 * @return 0 on success, -1 on PLL lock failure
 */
static int pll_configure(uintptr_t pll_cfg0_base,
                          uint32_t parent_freq,
                          uint32_t target_freq)
{
    uint32_t div_sel;
    uint32_t frac_div = 0;

    /* Calculate integer divider: VCO = parent * div_sel
     * For i.MX8M Plus: div_sel range 64-1023 */
    div_sel = target_freq / parent_freq;
    if (div_sel < 64 || div_sel > 1023) {
        return -1;  /* Out of range */
    }

    /* If target isn't an exact multiple, compute fractional divider */
    uint32_t remainder = target_freq - (parent_freq * div_sel);
    if (remainder != 0) {
        frac_div = (uint32_t)((uint64_t)remainder * (1ULL << 24) / parent_freq);
    }

    /* Step 1: Power down the PLL */
    mmio_write32(pll_cfg0_base,
                 mmio_read32(pll_cfg0_base) | PLL_CFG0_POWERDOWN_MASK);

    /* Step 2: Configure dividers */
    mmio_write32(pll_cfg0_base,
                 (mmio_read32(pll_cfg0_base) & ~PLL_CFG0_DIV_SEL_MASK) |
                 (div_sel << PLL_CFG0_DIV_SEL_SHIFT));

    if (frac_div != 0) {
        mmio_write32(pll_cfg0_base + 0x04,  /* PLL_CFG1 */
                     frac_div << PLL_CFG1_FRAC_DIV_SHIFT);
    }

    /* Step 3: Power up and enable */
    mmio_write32(pll_cfg0_base,
                 mmio_read32(pll_cfg0_base) & ~PLL_CFG0_POWERDOWN_MASK);
    mmio_write32(pll_cfg0_base,
                 mmio_read32(pll_cfg0_base) | PLL_CFG0_ENABLE_MASK);

    /* Step 4: Wait for PLL lock (max 100us) */
    return pll_wait_lock(pll_cfg0_base + 0x0C, 100000);
}

/*
 * Configure a clock root (peripheral clock divider and parent select).
 *
 * @param root_offset  Offset from CCM_BASE for the clock root
 * @param parent       Parent clock select value (CCM_PARENT_*)
 * @param divider      Clock divider value (output = parent / (divider+1))
 * @return 0 on success
 */
static int clock_root_configure(uint32_t root_offset,
                                  uint8_t parent,
                                  uint8_t divider)
{
    uintptr_t target_reg = CCM_BASE + root_offset;

    /* Disable clock root before changing configuration */
    mmio_write32(target_reg,
                 mmio_read32(target_reg) & ~CCM_ROOT_TARGET_ENABLE_MASK);

    /* Set parent mux and divider */
    mmio_write32(target_reg,
                 ((uint32_t)parent << CCM_ROOT_TARGET_MUX_SHIFT) |
                 ((uint32_t)(divider - 1) << CCM_ROOT_TARGET_DIV_SHIFT));

    /* Re-enable clock root */
    mmio_write32(target_reg,
                 mmio_read32(target_reg) | CCM_ROOT_TARGET_ENABLE_MASK);

    return 0;
}

/*
 * Main clock initialization for EAG-7000.
 * Called from board_init() in SPL.
 */
int eag7000_clock_init(void)
{
    int ret;

    /* ===== Step 1: Configure ARM PLL (1600 MHz from 24 MHz OSC) ===== */
    /* div_sel = 1600/24 = 66.67 → use fractional mode */
    /* Integer: 67 → 1608 MHz, frac adjust: (1608-1600)*2^24/24 = 559240 */
    ret = pll_configure(CCM_ANAL_BASE + CCM_ANAL_ARM_PLL_CFG0,
                        24000000, 1600000000);
    if (ret) return ret;

    /* ===== Step 2: Configure DRAM PLL (1066 MHz from 24 MHz OSC) ===== */
    /* div_sel = 1066/24 ≈ 44.42 → integer 44, frac adjust */
    ret = pll_configure(CCM_ANAL_BASE + CCM_ANAL_DRAM_PLL_CFG0,
                        24000000, 1066000000);
    if (ret) return ret;

    /* ===== Step 3: Configure SYS_PLL1 (800 MHz) ===== */
    /* div_sel = 800/24 ≈ 33.33 → integer 33, frac adjust */
    ret = pll_configure(CCM_ANAL_BASE + 0x00B4,  /* SYS_PLL1_CFG0 */
                        24000000, 800000000);
    if (ret) return ret;

    /* ===== Step 4: Configure SYS_PLL2 (500 MHz) ===== */
    /* div_sel = 500/24 ≈ 20.83 → integer 21, frac adjust */
    ret = pll_configure(CCM_ANAL_BASE + 0x00D4,  /* SYS_PLL2_CFG0 */
                        24000000, 500000000);
    if (ret) return ret;

    /* ===== Step 5: Configure peripheral clock roots ===== */

    /* A72 core clock: ARM_PLL / 2 = 800 MHz base, turbo to 2 GHz */
    ret = clock_root_configure(CCM_ROOT_ARM_A53_CLK,  /* Shared root */
                               CCM_PARENT_ARM_PLL_800M, 1);
    if (ret) return ret;

    /* DRAM clock root: DRAM_PLL / 1 = 1066 MHz (DDR4266 data rate) */
    ret = clock_root_configure(0x4C00,  /* DRAM clock root */
                               CCM_PARENT_OSC_24M, 1);
    if (ret) return ret;

    /* Ethernet RGMII clock: SYS_PLL1 / 4 = 200 MHz (for RGMII at 2.5G) */
    ret = clock_root_configure(CCM_ROOT_ENET1_CLK,
                               CCM_PARENT_SYS_PLL1_800M, 4);
    if (ret) return ret;

    /* PCIe reference clock: 100 MHz from external oscillator (Y4) */
    ret = clock_root_configure(CCM_ROOT_PCIE_CLK,
                               CCM_PARENT_OSC_24M, 1);
    if (ret) return ret;

    /* SPI bus clocks: SYS_PLL2 / 10 = 50 MHz */
    ret = clock_root_configure(CCM_ROOT_SPI1_CLK,
                               CCM_PARENT_SYS_PLL2_500M, 10);
    if (ret) return ret;

    ret = clock_root_configure(CCM_ROOT_SPI2_CLK,
                               CCM_PARENT_SYS_PLL2_500M, 10);
    if (ret) return ret;

    /* UART clocks: SYS_PLL1 / 10 = 80 MHz */
    ret = clock_root_configure(CCM_ROOT_UART1_CLK,
                               CCM_PARENT_SYS_PLL1_800M, 10);
    if (ret) return ret;

    /* CAN-FD clocks: SYS_PLL1 / 10 = 80 MHz */
    ret = clock_root_configure(CCM_ROOT_CAN_CLK,
                               CCM_PARENT_SYS_PLL1_800M, 10);
    if (ret) return ret;

    return 0;  /* All clocks configured successfully */
}
```

### 4.3.2 GPIO and IOMUX Initialization

```c
/*
 * EAG-7000 GPIO and IOMUX Configuration
 * Sets up pin multiplexing, pad drive strength, and GPIO direction
 * based on the Phase 2 pinout and netlist.
 */

#include "eag7000_mmio.h"
#include "eag7000_gpio.h"
#include <stdint.h>

/* IOMUXC Register Offsets — each pin has 4 registers:
 *   MUX_CTRL   — alternate function select
 *   MUX_SEL    — daisy chain select (for shared input pins)
 *   PAD_CTRL   — drive strength, slew rate, pull-up/down
 *   PAD_STATUS — readback pad state
 */
#define IOMUXC_MUX_CTRL(pin_bank, pin_idx)  \
    (IOMUXC_BASE + 0x0000 + ((pin_bank) * 0x100) + ((pin_idx) * 0x04))

#define IOMUXC_PAD_CTRL(pin_bank, pin_idx)  \
    (IOMUXC_BASE + 0x0200 + ((pin_bank) * 0x100) + ((pin_idx) * 0x04))

/* IOMUXC MUX mode values */
#define IOMUX_ALT0   0x0   /* Primary alternate function */
#define IOMUX_ALT1   0x1   /* Secondary alternate function */
#define IOMUX_ALT2   0x2   /* Tertiary */
#define IOMUX_ALT3   0x3   /* GPIO mode */
#define IOMUX_ALT4   0x4   /* Quaternary */
#define IOMUX_ALT5   0x5   /* Quinary */

/* PAD_CTRL register bit fields */
#define PAD_CTRL_SRE      (1U << 0)    /* Slew Rate: 0=slow, 1=fast */
#define PAD_CTRL_DSE_SHIFT  3          /* Drive Strength Field: bits [5:3] */
#define PAD_CTRL_DSE_MASK   (0x7U << 3)
#define PAD_CTRL_DSE_260OHM  (0x1U << 3)  /* 2.6 mA @ 3.3V */
#define PAD_CTRL_DSE_520OHM  (0x2U << 3)  /* 5.2 mA @ 3.3V */
#define PAD_CTRL_DSE_1KOHM   (0x3U << 3)  /* 10.4 mA @ 3.3V (1K to VDD) */
#define PAD_CTRL_DSE_400OHM  (0x4U << 3)  /* 20.8 mA @ 3.3V (high drive) */
#define PAD_CTRL_DSE_200OHM  (0x6U << 3)  /* 41.6 mA @ 3.3V (ultra-high) */
#define PAD_CTRL_SPEED_SHIFT  6           /* Speed: 0=low, 1=medium, 2=fast, 3=max */
#define PAD_CTRL_SPEED_MASK   (0x3U << 6)
#define PAD_CTRL_ODE      (1U << 11)   /* Open Drain Enable */
#define PAD_CTRL_PUE      (1U << 12)   /* Pull Up Enable (keeper if !PUE) */
#define PAD_CTRL_PUS_SHIFT  14          /* Pull Up/Down Select */
#define PAD_CTRL_PUS_MASK   (0x3U << 14)
#define PAD_CTRL_PUS_100K_PU  (0x3U << 14)  /* 100K pull-up */
#define PAD_CTRL_PUS_47K_PU   (0x2U << 14)  /* 47K pull-up */
#define PAD_CTRL_PUS_100K_PD  (0x0U << 14)  /* 100K pull-down */
#define PAD_CTRL_HYS      (1U << 16)   /* Hysteresis Enable */

/* ============================================================================
 * Pin Configuration Table for EAG-7000
 * Format: {mux_reg, pad_reg, mux_mode, pad_config, pin_name}
 * ============================================================================ */
typedef struct {
    uintptr_t mux_reg;      /* IOMUXC MUX control register address */
    uintptr_t pad_reg;      /* IOMUXC PAD control register address */
    uint8_t    mux_mode;     /* Alternate function select (IOMUX_ALT0-5) */
    uint32_t   pad_config;   /* PAD_CTRL register value */
    const char *pin_name;    /* Human-readable name for debug */
} pin_config_t;

/* Complete pin configuration for EAG-7000 board */
static const pin_config_t eag7000_pin_config[] = {
    /* ===== Ethernet RGMII (ENET1) — 2.5GbE Port 0 ===== */
    { IOMUXC_BASE + 0x0500, IOMUXC_BASE + 0x0280,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "ENET0_TXC" },
    { IOMUXC_BASE + 0x0504, IOMUXC_BASE + 0x0284,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "ENET0_TX_CTL" },
    { IOMUXC_BASE + 0x0508, IOMUXC_BASE + 0x0288,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "ENET0_TXD0" },
    { IOMUXC_BASE + 0x050C, IOMUXC_BASE + 0x028C,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "ENET0_TXD1" },
    { IOMUXC_BASE + 0x0510, IOMUXC_BASE + 0x0290,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RXC" },
    { IOMUXC_BASE + 0x0514, IOMUXC_BASE + 0x0294,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RX_CTL" },
    { IOMUXC_BASE + 0x0518, IOMUXC_BASE + 0x0298,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RXD0" },
    { IOMUXC_BASE + 0x051C, IOMUXC_BASE + 0x029C,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RXD1" },
    { IOMUXC_BASE + 0x0520, IOMUXC_BASE + 0x02A0,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RXD2" },
    { IOMUXC_BASE + 0x0524, IOMUXC_BASE + 0x02A4,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2),
      "ENET0_RXD3" },
    { IOMUXC_BASE + 0x0528, IOMUXC_BASE + 0x02A8,
      IOMUX_ALT0, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "ENET0_MDIO" },
    { IOMUXC_BASE + 0x052C, IOMUXC_BASE + 0x02AC,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "ENET0_MDC" },

    /* ===== PCIe Gen3 x1 (Hailo-8 NPU) ===== */
    { IOMUXC_BASE + 0x0600, IOMUXC_BASE + 0x0340,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(3) | PAD_CTRL_SRE,
      "PCIE_TX_P" },
    { IOMUXC_BASE + 0x0604, IOMUXC_BASE + 0x0344,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(3) | PAD_CTRL_SRE,
      "PCIE_TX_N" },
    { IOMUXC_BASE + 0x0608, IOMUXC_BASE + 0x0348,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(3) | PAD_CTRL_SRE,
      "PCIE_RX_P" },
    { IOMUXC_BASE + 0x060C, IOMUXC_BASE + 0x034C,
      IOMUX_ALT0, PAD_CTRL_DSE_400OHM | PAD_CTRL_SPEED(3) | PAD_CTRL_SRE,
      "PCIE_RX_N" },
    { IOMUXC_BASE + 0x0610, IOMUXC_BASE + 0x0350,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "PCIE_RST_B" },  /* GPIO1_IO10 */
    { IOMUXC_BASE + 0x0614, IOMUXC_BASE + 0x0354,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "PCIE_WAKE_B" },  /* GPIO1_IO11 */
    { IOMUXC_BASE + 0x0618, IOMUXC_BASE + 0x0358,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "PCIE_CLKREQ_B" },  /* GPIO1_IO12 */

    /* ===== SPI2 (CAN-FD #0 — MCP2518FD) ===== */
    { IOMUXC_BASE + 0x0700, IOMUXC_BASE + 0x03A0,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "SPI2_SCK" },
    { IOMUXC_BASE + 0x0704, IOMUXC_BASE + 0x03A4,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "SPI2_MOSI" },
    { IOMUXC_BASE + 0x0708, IOMUXC_BASE + 0x03A8,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_HYS,
      "SPI2_MISO" },
    { IOMUXC_BASE + 0x070C, IOMUXC_BASE + 0x03AC,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(2) | PAD_CTRL_SRE,
      "SPI2_CS0" },

    /* ===== I2C1 (PMIC + RTC) ===== */
    { IOMUXC_BASE + 0x0800, IOMUXC_BASE + 0x0400,
      IOMUX_ALT0, PAD_CTRL_DSE_1KOHM | PAD_CTRL_PUS_47K_PU | PAD_CTRL_ODE | PAD_CTRL_HYS | PAD_CTRL_SPEED(1),
      "I2C1_SDA" },
    { IOMUXC_BASE + 0x0804, IOMUXC_BASE + 0x0404,
      IOMUX_ALT0, PAD_CTRL_DSE_1KOHM | PAD_CTRL_PUS_47K_PU | PAD_CTRL_ODE | PAD_CTRL_HYS | PAD_CTRL_SPEED(1),
      "I2C1_SCL" },

    /* ===== UART1 (Debug Console) ===== */
    { IOMUXC_BASE + 0x0900, IOMUXC_BASE + 0x0480,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(1),
      "UART1_TX" },
    { IOMUXC_BASE + 0x0904, IOMUXC_BASE + 0x0484,
      IOMUX_ALT0, PAD_CTRL_DSE_520OHM | PAD_CTRL_SPEED(1) | PAD_CTRL_HYS,
      "UART1_RX" },

    /* ===== GPIO — LED and Control pins ===== */
    { IOMUXC_BASE + 0x0A00, IOMUXC_BASE + 0x0500,
      IOMUX_ALT3, PAD_CTRL_DSE_520OHM,
      "GPIO4_LED_STATUS" },
    { IOMUXC_BASE + 0x0A04, IOMUXC_BASE + 0x0504,
      IOMUX_ALT3, PAD_CTRL_DSE_520OHM,
      "GPIO4_LED_ERROR" },
    { IOMUXC_BASE + 0x0A08, IOMUXC_BASE + 0x0508,
      IOMUX_ALT3, PAD_CTRL_DSE_520OHM,
      "GPIO4_LED_ACT" },
    { IOMUXC_BASE + 0x0A0C, IOMUXC_BASE + 0x050C,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_HYS,
      "GPIO4_POE_STATUS" },
    { IOMUXC_BASE + 0x0A10, IOMUXC_BASE + 0x0510,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "GPIO4_RTC_IRQ" },
    { IOMUXC_BASE + 0x0A14, IOMUXC_BASE + 0x0514,
      IOMUX_ALT3, PAD_CTRL_DSE_260OHM | PAD_CTRL_PUS_100K_PU | PAD_CTRL_HYS,
      "GPIO4_NPU_IRQ" },
};

#define PIN_CONFIG_COUNT  (sizeof(eag7000_pin_config) / sizeof(pin_config_t))

/*
 * Initialize all IOMUX pin configurations and GPIO directions.
 * Called from board_init() after clock configuration.
 */
int eag7000_gpio_init(void)
{
    /* Step 1: Configure all IOMUX pins */
    for (int i = 0; i < PIN_CONFIG_COUNT; i++) {
        const pin_config_t *pin = &eag7000_pin_config[i];

        /* Set MUX mode (alternate function) */
        mmio_write32(pin->mux_reg, pin->mux_mode);

        /* Set PAD control (drive strength, pull-ups, speed) */
        mmio_write32(pin->pad_reg, pin->pad_config);
    }

    /* Step 2: Configure GPIO directions */

    /* GPIO1 — PCIe control pins (all output) */
    mmio_write32(GPIO1_BASE + GPIO_GDIR, 0x00000000);  /* Reset all to input */
    mmio_write32(GPIO1_BASE + GPIO_GDIR,
                 (1U << GPIO1_PCIE_RST_PIN)   |  /* Output: PCIe reset */
                 (1U << GPIO1_PCIE_CLKREQ_PIN));  /* Output: PCIe CLKREQ */
    /* GPIO1_PCIE_WAKE_PIN stays input (active-low wake from NPU) */

    /* Set PCIe reset HIGH (inactive) — NPU starts in reset */
    mmio_write32(GPIO1_BASE + GPIO_DR,
                 (1U << GPIO1_PCIE_RST_PIN));

    /* GPIO3 — Sensor/expansion control (all output initially) */
    mmio_write32(GPIO3_BASE + GPIO_GDIR,
                 (1U << GPIO3_I2C_MUX_RST_PIN) |
                 (1U << GPIO3_CAM_RST_PIN)      |
                 (1U << GPIO3_CAM_PWDN_PIN)      |
                 (1U << GPIO3_CAN1_EN_PIN)       |
                 (1U << GPIO3_CAN2_EN_PIN)       |
                 (1U << GPIO3_CAN1_STB_PIN)      |
                 (1U << GPIO3_CAN2_STB_PIN));

    /* Camera: hold in reset, power down */
    mmio_write32(GPIO3_BASE + GPIO_DR, 0);  /* All low = reset + standby */
    mmio_write32(GPIO3_BASE + GPIO_DR,
                 mmio_read32(GPIO3_BASE + GPIO_DR) |
                 (1U << GPIO3_CAM_PWDN_PIN));  /* Power-down active high */

    /* GPIO4 — Power/Status (mixed direction) */
    mmio_write32(GPIO4_BASE + GPIO_GDIR,
                 (1U << GPIO4_LED_STATUS_PIN)  |  /* Output */
                 (1U << GPIO4_LED_ERROR_PIN)   |  /* Output */
                 (1U << GPIO4_LED_ACT_PIN)    |  /* Output */
                 (1U << GPIO4_WATCHDOG_PIN));     /* Output */
    /* GPIO4_POE_STATUS_PIN, RTC_IRQ, NPU_IRQ are inputs (default) */

    /* Step 3: Configure GPIO interrupts */
    /* NPU interrupt — falling edge (active-low IRQ) */
    mmio_write32(GPIO4_BASE + GPIO_ICR2,
                 (GPIO_ICR_FALLING_EDGE << ((GPIO4_NPU_IRQ_PIN - 16) * 2)));
    mmio_write32(GPIO4_BASE + GPIO_IMR,
                 mmio_read32(GPIO4_BASE + GPIO_IMR) | (1U << GPIO4_NPU_IRQ_PIN));

    /* RTC interrupt — active-low level */
    mmio_write32(GPIO4_BASE + GPIO_ICR1,
                 (GPIO_ICR_LOW_LEVEL << (GPIO4_RTC_IRQ_PIN * 2)));
    mmio_write32(GPIO4_BASE + GPIO_IMR,
                 mmio_read32(GPIO4_BASE + GPIO_IMR) | (1U << GPIO4_RTC_IRQ_PIN));

    /* Step 4: Release I2C mux from reset */
    /* Hold I2C mux in reset for 10ms after power stabilization */
    mmio_write32(GPIO3_BASE + GPIO_DR,
                 mmio_read32(GPIO3_BASE + GPIO_DR) | (1U << GPIO3_I2C_MUX_RST_PIN));

    return 0;
}
```

---

## 4.4 Device Driver — SPI CAN-FD Controller (MCP2518FD)

This is a production-quality Linux kernel driver for the MCP2518FD CAN-FD controller, connected via SPI2. This is a critical peripheral defined in Phase 1 (CAN-FD fieldbus interface).

```c
/*
 * EAG-7000 MCP2518FD SPI CAN-FD Driver
 *
 * Linux kernel driver for Microchip MCP2518FD CAN-FD controller
 * connected via SPI (ECSPI2 on i.MX8M Plus).
 *
 * Features:
 *   - CAN-FD up to 8 Mbps (data phase), 1 Mbps (arbitration)
 *   - SPI bus: up to 20 MHz (ECSPI2 @ 50 MHz, prescaled to 10 MHz)
 *   - DMA ring-buffer SPI transfers for zero-copy RX
 *   - Hardware CRC-16 on SPI transactions
 *   - Interrupt-driven with NAPI polling
 *   - Power management (runtime PM, sleep/wake via CAN bus)
 *
 * Copyright (c) 2026 EAG-7000 Project
 * SPDX-License-Identifier: GPL-2.0
 */

#include <linux/module.h>
#include <linux/init.h>
#include <linux/spi/spi.h>
#include <linux/can/dev.h>
#include <linux/can/rx-offload.h>
#include <linux/interrupt.h>
#include <linux/regmap.h>
#include <linux/gpio/consumer.h>
#include <linux/clk.h>
#include <linux/dma-mapping.h>
#include <linux/pm_runtime.h>
#include <net/rtnetlink.h>

/* ============================================================================
 * MCP2518FD Register Map (SPI-addressed, 12-bit address space)
 * ============================================================================ */

/* CAN Control Registers */
#define MCP2518FD_CON           0x0000  /* CAN Control */
#define MCP2518FD_NBTCFG        0x0004  /* Nominal Bit-Time Config */
#define MCP2518FD_DBTCFG        0x0008  /* Data Bit-Time Config */
#define MCP2518FD_TDC           0x000C  /* Transmitter Delay Compensation */

/* CAN Status / Interrupt Registers */
#define MCP2518FD_TBC           0x0014  /* Timer-Based Counter */
#define MCP2518FD_TSR           0x001C  /* TX Status */
#define MCP2518FD_RXIF          0x0020  /* RX Interrupt Flags */
#define MCP2518FD_TXIF          0x0024  /* TX Interrupt Flags */
#define MCP2518FD_RXOVIF        0x0028  /* RX Overflow Interrupt Flags */
#define MCP2518FD_CERRIF        0x002C  /* CAN Error Interrupt Flags */

/* Filter / FIFO Registers */
#define MCP2518FD_FIFOCON(n)    (0x0050 + ((n) * 0x10))  /* FIFO Control */
#define MCP2518FD_FIFOSTA(n)    (0x0054 + ((n) * 0x10))  /* FIFO Status */
#define MCP2518FD_FIFOUA(n)     (0x0058 + ((n) * 0x10))  /* FIFO User Address */

/* TX/RX Object Addresses */
#define MCP2518FD_TXQ           0x0400  /* TX Queue RAM base */
#define MCP2518FD_RXFIFO0       0x0600  /* RX FIFO 0 RAM base */
#define MCP2518FD_RXFIFO1       0x0800  /* RX FIFO 1 RAM base */

/* ECC / CRC Registers */
#define MCP2518FD_CRC           0x0E00  /* CRC Register */
#define MCP2518FD_ECCCON        0x0E04  /* ECC Control */

/* SPI Command Byte Format */
#define MCP2518FD_SPI_CMD_RESET    0x00
#define MCP2518FD_SPI_CMD_WRITE    0x20
#define MCP2518FD_SPI_CMD_READ     0x30
#define MCP2518FD_SPI_CMD_MODIFY   0x40  /* Read-modify-write */

/* CAN CON Register Bits */
#define CON_REQOP_MASK           GENMASK(26, 24)
#define CON_REQOP_CONFIG         (0x4 << 24)  /* Configuration mode */
#define CON_REQOP_NORMAL         (0x0 << 24)  /* Normal mode (CAN FD) */
#define CON_REQOP_LISTEN         (0x1 << 24)  /* Listen-only mode */
#define CON_REQOP_LOOPBACK       (0x2 << 24)  /* Loopback mode */
#define CON_OPMOD_MASK           GENMASK(23, 21)
#define CON_TXQEN               BIT(24)     /* TX Queue Enable */
#define CON_STDEXT              BIT(23)     /* Extended ID support */
#define CON_ESIGM               BIT(22)     /* Enable CAN-FD */
#define CON_BRSDIS              BIT(21)     /* Bit Rate Switch disable */
#define CON_RXOVFL              BIT(20)     /* RX Overflow flag */

/* NBTCFG Bit Fields (Nominal Bit-Time Configuration) */
#define NBTCFG_BRP_MASK         GENMASK(31, 24)
#define NBTCFG_TSEG1_MASK       GENMASK(23, 16)
#define NBTCFG_TSEG2_MASK       GENMASK(15, 8)
#define NBTCFG_SJW_MASK         GENMASK(7, 0)

/* DBTCFG Bit Fields (Data Bit-Time Configuration) */
#define DBTCFG_BRP_MASK         GENMASK(31, 24)
#define DBTCFG_TSEG1_MASK       GENMASK(23, 16)
#define DBTCFG_TSEG2_MASK       GENMASK(15, 8)
#define DBTCFG_SJW_MASK         GENMASK(7, 0)

/* TX/RX Object Header Format */
#define CAN_MSG_OBJ_FLAGS        0x00
#define CAN_MSG_OBJ_ID           0x04
#define CAN_MSG_OBJ_DLC          0x08
#define CAN_MSG_OBJ_DATA         0x0C
#define CAN_MSG_OBJ_FLAGS_FDF   BIT(30)    /* CAN-FD format */
#define CAN_MSG_OBJ_FLAGS_BRS   BIT(29)    /* Bit Rate Switch */
#define CAN_MSG_OBJ_FLAGS_ESI   BIT(28)    /* Error State Indicator */
#define CAN_MSG_OBJ_FLAGS_EXT   BIT(1)     /* Extended ID */
#define CAN_MSG_OBJ_FLAGS_RTR   BIT(0)     /* Remote frame */

/* SPI Transfer Size Limits */
#define MCP2518FD_SPI_MAX_BURST  256   /* Max bytes per SPI transaction */
#define MCP2518FD_SPI_SPEED_HZ   10000000  /* 10 MHz SPI clock */

/* DMA Ring Buffer for SPI transfers */
#define SPI_RX_RING_SIZE         4096
#define SPI_TX_RING_SIZE         4096

/* ============================================================================
 * Driver Private Data Structure
 * ============================================================================ */
struct mcp2518fd_priv {
    struct spi_device       *spi;           /* SPI device */
    struct can_priv          can;            /* CAN netdev priv */
    struct can_rx_offload    offload;        /* RX offload helper */
    struct regmap           *regmap;         /* Regmap for register access */
    struct gpio_desc        *cs_gpio;        /* SPI chip-select GPIO (if SW CS) */
    struct gpio_desc        *rst_gpio;       /* Reset GPIO (active-low) */
    struct gpio_desc        *int_gpio;       /* Interrupt GPIO */
    struct clk              *can_clk;        /* External oscillator clock */
    struct clk              *spi_clk;        /* SPI peripheral clock */

    /* DMA buffers for SPI transfers */
    u8                      *spi_tx_buf;    /* DMA-coherent TX buffer */
    u8                      *spi_rx_buf;    /* DMA-coherent RX buffer */
    dma_addr_t               spi_tx_dma;    /* TX DMA address */
    dma_addr_t               spi_rx_dma;    /* RX DMA address */

    /* Runtime state */
    spinlock_t               lock;           /* Protects register access */
    u32                       spi_crc;       /* Expected SPI CRC-16 */
    int                       fifo_num;      /* Active FIFO count */
    u32                       bus_freq;      /* CAN bus frequency */
};

/* ============================================================================
 * SPI Transfer Helpers
 * ============================================================================ */

/*
 * Build an SPI command byte for MCP2518FD.
 * Command format: [CMD(4)] [ADDR(12)] [CRC(16, optional)]
 */
static void mcp2518fd_spi_cmd(u8 *buf, u8 cmd, u16 addr)
{
    buf[0] = cmd | ((addr >> 8) & 0x0F);
    buf[1] = addr & 0xFF;
}

/*
 * Read multiple registers from MCP2518FD via SPI.
 * Uses DMA-coherent buffers for zero-copy transfer.
 *
 * @priv:  Driver private data
 * @addr:  Starting register address (12-bit)
 * @buf:   Destination buffer (must be DMA-coherent or stack)
 * @len:   Number of bytes to read
 * @return: 0 on success, negative errno on failure
 */
static int mcp2518fd_spi_read(struct mcp2518fd_priv *priv,
                               u16 addr, u8 *buf, size_t len)
{
    struct spi_transfer xfer[2] = {};
    struct spi_message msg;
    int ret;

    if (len > MCP2518FD_SPI_MAX_BURST)
        return -EMSGSIZE;

    /* Build SPI command header */
    mcp2518fd_spi_cmd(priv->spi_tx_buf, MCP2518FD_SPI_CMD_READ, addr);

    /* First transfer: command + address (2 bytes) */
    xfer[0].tx_buf = priv->spi_tx_buf;
    xfer[0].rx_buf = NULL;
    xfer[0].len = 2;
    xfer[0].speed_hz = MCP2518FD_SPI_SPEED_HZ;

    /* Second transfer: read data (full-duplex, we send dummy) */
    xfer[1].tx_buf = priv->spi_tx_buf + 2;  /* Dummy bytes */
    xfer[1].rx_buf = priv->spi_rx_buf;
    xfer[1].len = len;
    xfer[1].speed_hz = MCP2518FD_SPI_SPEED_HZ;
    xfer[1].dma_address = priv->spi_rx_dma;

    spi_message_init(&msg);
    spi_message_add_tail(&xfer[0], &msg);
    spi_message_add_tail(&xfer[1], &msg);

    spin_lock_irq(&priv->lock);
    ret = spi_sync(priv->spi, &msg);
    spin_unlock_irq(&priv->lock);

    if (ret == 0)
        memcpy(buf, priv->spi_rx_buf, len);

    return ret;
}

/*
 * Write multiple registers to MCP2518FD via SPI.
 * Uses DMA-coherent buffers for zero-copy transfer.
 */
static int mcp2518fd_spi_write(struct mcp2518fd_priv *priv,
                                u16 addr, const u8 *buf, size_t len)
{
    struct spi_transfer xfer = {};
    struct spi_message msg;
    int ret;

    if ((2 + len) > MCP2518FD_SPI_MAX_BURST)
        return -EMSGSIZE;

    /* Build command header + data in contiguous TX buffer */
    mcp2518fd_spi_cmd(priv->spi_tx_buf, MCP2518FD_SPI_CMD_WRITE, addr);
    memcpy(priv->spi_tx_buf + 2, buf, len);

    xfer.tx_buf = priv->spi_tx_buf;
    xfer.rx_buf = NULL;
    xfer.len = 2 + len;  /* Command + address + payload */
    xfer.speed_hz = MCP2518FD_SPI_SPEED_HZ;
    xfer.dma_address = priv->spi_tx_dma;

    spi_message_init(&msg);
    spi_message_add_tail(&xfer, &msg);

    spin_lock_irq(&priv->lock);
    ret = spi_sync(priv->spi, &msg);
    spin_unlock_irq(&priv->lock);

    return ret;
}

/*
 * Write a single 32-bit register via SPI.
 * Convenience wrapper for register writes.
 */
static int mcp2518fd_reg_write(struct mcp2518fd_priv *priv,
                                u16 addr, u32 val)
{
    u8 data[4];
    data[0] = val & 0xFF;
    data[1] = (val >> 8) & 0xFF;
    data[2] = (val >> 16) & 0xFF;
    data[3] = (val >> 24) & 0xFF;
    return mcp2518fd_spi_write(priv, addr, data, 4);
}

/*
 * Read a single 32-bit register via SPI.
 */
static int mcp2518fd_reg_read(struct mcp2518fd_priv *priv,
                               u16 addr, u32 *val)
{
    u8 data[4];
    int ret = mcp2518fd_spi_read(priv, addr, data, 4);
    if (ret)
        return ret;
    *val = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24);
    return 0;
}

/* ============================================================================
 * CAN Bit-Timing Configuration
 * ============================================================================ */

/*
 * Calculate CAN-FD nominal and data bit-time register values.
 *
 * EAG-7000 CAN clock: 80 MHz (from SYS_PLL1 / 10)
 *
 * Nominal (arbitration) phase: 500 kbps
 *   BRP = 8, TSEG1 = 15, TSEG2 = 4, SJW = 4
 *   Bit time = (1 + TSEG1 + TSEG2) * BRP / fclk
 *            = (1 + 15 + 4) * 8 / 80MHz = 2 µs = 500 kbps
 *
 * Data phase: 2 Mbps (with BRS)
 *   BRP = 2, TSEG1 = 15, TSEG2 = 4, SJW = 4
 *   Bit time = (1 + 15 + 4) * 2 / 80MHz = 0.5 µs = 2 Mbps
 */
static int mcp2518fd_set_bittiming(struct mcp2518fd_priv *priv)
{
    u32 nbtcfg, dbtcfg;
    int ret;

    /* Nominal bit-time: 500 kbps @ 80 MHz CAN clock */
    nbtcfg = (8U << 24)    |  /* BRP = 8 */
              (15U << 16)   |  /* TSEG1 = 15 */
              (4U << 8)     |  /* TSEG2 = 4 */
              (4U << 0);       /* SJW = 4 */

    ret = mcp2518fd_reg_write(priv, MCP2518FD_NBTCFG, nbtcfg);
    if (ret)
        return ret;

    /* Data bit-time: 2 Mbps @ 80 MHz CAN clock (CAN-FD data phase) */
    dbtcfg = (2U << 24)    |  /* BRP = 2 */
              (15U << 16)   |  /* TSEG1 = 15 */
              (4U << 8)     |  /* TSEG2 = 4 */
              (4U << 0);       /* SJW = 4 */

    ret = mcp2518fd_reg_write(priv, MCP2518FD_DBTCFG, dbtcfg);
    if (ret)
        return ret;

    /* Transmitter Delay Compensation (TDC) for CAN-FD data phase */
    /* TDCO = 5 (offset in time quanta), TDCV auto-calculated */
    ret = mcp2518fd_reg_write(priv, MCP2518FD_TDC, 0x00000005);

    return ret;
}

/* ============================================================================
 * CAN TX/RX Operations
 * ============================================================================ */

/*
 * Transmit a CAN/CAN-FD frame.
 * Loads frame into TX Queue (FIFO 1) and requests transmission.
 *
 * @skb:  Socket buffer containing CAN frame
 * @priv: Driver private data
 * @return: NETDEV_TX_OK on success, NETDEV_TX_BUSY if TX queue full
 */
static netdev_tx_t mcp2518fd_start_xmit(struct sk_buff *skb,
                                          struct net_device *netdev)
{
    struct mcp2518fd_priv *priv = netdev_priv(netdev);
    struct can_frame *cf = (struct can_frame *)skb->data;
    u32 obj_flags = 0, obj_id = 0, obj_dlc = 0;
    u8 tx_data[20];  /* Header (12 bytes) + max 8 data bytes (CAN 2.0) */
    u32 fifocon;
    int ret;

    if (can_dropped_invalid_skb(netdev, skb))
        return NETDEV_TX_OK;

    netdev_sent_queue(netdev, skb->len);

    /* Build CAN message object header */
    if (cf->can_id & CAN_EFF_FLAG) {
        obj_flags |= CAN_MSG_OBJ_FLAGS_EXT;
        obj_id = cf->can_id & CAN_EFF_MASK;
    } else {
        obj_id = cf->can_id & CAN_SFF_MASK;
    }

    if (cf->can_id & CAN_RTR_FLAG)
        obj_flags |= CAN_MSG_OBJ_FLAGS_RTR;

    /* CAN-FD frame handling */
    if (can_is_canfd_skb(skb)) {
        struct canfd_frame *cfd = (struct canfd_frame *)skb->data;
        obj_flags |= CAN_MSG_OBJ_FLAGS_FDF;
        if (cfd->flags & CANFD_BRS)
            obj_flags |= CAN_MSG_OBJ_FLAGS_BRS;
        if (cfd->flags & CANFD_ESI)
            obj_flags |= CAN_MSG_OBJ_FLAGS_ESI;
        obj_dlc = can_len2dlc(cfd->len);
        memcpy(tx_data + 12, cfd->data, cfd->len);
    } else {
        /* Classic CAN 2.0 */
        obj_dlc = cf->can_dlc;
        memcpy(tx_data + 12, cf->data, cf->can_dlc);
    }

    /* Pack header into TX buffer (little-endian) */
    put_unaligned_le32(obj_flags, &tx_data[0]);
    put_unaligned_le32(obj_id, &tx_data[4]);
    put_unaligned_le32(obj_dlc, &tx_data[8]);

    /* Write message object to TX Queue RAM */
    ret = mcp2518fd_spi_write(priv, MCP2518FD_TXQ,
                               tx_data, 12 + can_get_len(cf));
    if (ret) {
        netdev_err(netdev, "SPI TX write failed: %d\n", ret);
        netdev->stats.tx_dropped++;
        dev_kfree_skb(skb);
        return NETDEV_TX_OK;
    }

    /* Trigger TX Queue processing */
    ret = mcp2518fd_reg_read(priv, MCP2518FD_FIFOCON(0), &fifocon);
    if (ret) {
        netdev_err(netdev, "SPI FIFO read failed: %d\n", ret);
        netdev->stats.tx_dropped++;
        dev_kfree_skb(skb);
        return NETDEV_TX_OK;
    }

    /* Set TXREQ bit to queue the frame for transmission */
    fifocon |= BIT(0);  /* TXREQ = 1 */
    ret = mcp2518fd_reg_write(priv, MCP2518FD_FIFOCON(0), fifocon);
    if (ret) {
        netdev_err(netdev, "SPI TX trigger failed: %d\n", ret);
        netdev->stats.tx_dropped++;
    }

    dev_kfree_skb(skb);
    return NETDEV_TX_OK;
}

/*
 * Read a received CAN frame from RX FIFO and pass it to the network stack.
 * Called from interrupt handler or NAPI poll.
 *
 * @priv:      Driver private data
 * @fifo_num:  RX FIFO number (0 or 1)
 * @return:    0 on success, negative errno on failure
 */
static int mcp2518fd_handle_rx(struct mcp2518fd_priv *priv, int fifo_num)
{
    struct net_device *netdev = priv->can.dev;
    struct canfd_frame cfd;
    u32 obj_flags, obj_id, obj_dlc;
    u8 rx_buf[76];  /* Max CAN-FD frame: 12 header + 64 data */
    u16 fifo_ram = (fifo_num == 0) ? MCP2518FD_RXFIFO0 : MCP2518FD_RXFIFO1;
    int ret, len;

    /* Read message object from RX FIFO RAM */
    ret = mcp2518fd_spi_read(priv, fifo_ram, rx_buf, 76);
    if (ret)
        return ret;

    /* Parse message object header (little-endian) */
    obj_flags = get_unaligned_le32(&rx_buf[0]);
    obj_id    = get_unaligned_le32(&rx_buf[4]);
    obj_dlc   = get_unaligned_le32(&rx_buf[8]);

    /* Build canfd_frame */
    memset(&cfd, 0, sizeof(cfd));

    if (obj_flags & CAN_MSG_OBJ_FLAGS_EXT) {
        cfd.can_id = obj_id & CAN_EFF_MASK;
        cfd.can_id |= CAN_EFF_FLAG;
    } else {
        cfd.can_id = obj_id & CAN_SFF_MASK;
    }

    if (obj_flags & CAN_MSG_OBJ_FLAGS_RTR) {
        cfd.can_id |= CAN_RTR_FLAG;
    }

    if (obj_flags & CAN_MSG_OBJ_FLAGS_FDF) {
        /* CAN-FD frame */
        cfd.len = can_dlc2len(obj_dlc & 0x0F);
        if (obj_flags & CAN_MSG_OBJ_FLAGS_BRS)
            cfd.flags |= CANFD_BRS;
        if (obj_flags & CAN_MSG_OBJ_FLAGS_ESI)
            cfd.flags |= CANFD_ESI;
        memcpy(cfd.data, &rx_buf[12], min(cfd.len, 64U));
    } else {
        /* Classic CAN 2.0 frame */
        cfd.len = can_dlc2len(obj_dlc & 0x0F);
        memcpy(cfd.data, &rx_buf[12], min(cfd.len, 8U));
    }

    /* Feed to CAN rx-offload which handles SKB allocation and napi */
    ret = can_rx_offload_queue_tail(&priv->offload, &cfd, 0);
    if (ret)
        netdev->stats.rx_dropped++;

    /* Increment RX FIFO user address to acknowledge the read */
    len = 12 + cfd.len;
    mcp2518fd_reg_write(priv, MCP2518FD_FIFOUA(fifo_num), fifo_ram + len);

    /* Clear RX FIFO interrupt flag */
    mcp2518fd_reg_write(priv, MCP2518FD_RXIF, BIT(fifo_num));

    return 0;
}

/* ============================================================================
 * Interrupt Handler
 * ============================================================================ */

/*
 * MCP2518FD interrupt handler.
 * Reads interrupt flags, handles RX/TX completions and errors.
 */
static irqreturn_t mcp2518fd_irq(int irq, void *dev_id)
{
    struct mcp2518fd_priv *priv = dev_id;
    struct net_device *netdev = priv->can.dev;
    u32 rxif, txif, errif;
    int ret;

    /* Read all interrupt flag registers */
    ret = mcp2518fd_reg_read(priv, MCP2518FD_RXIF, &rxif);
    if (ret)
        return IRQ_NONE;

    ret = mcp2518fd_reg_read(priv, MCP2518FD_TXIF, &txif);
    if (ret)
        return IRQ_NONE;

    ret = mcp2518fd_reg_read(priv, MCP2518FD_CERRIF, &errif);
    if (ret)
        return IRQ_NONE;

    /* Handle RX completions */
    if (rxif & BIT(0))
        mcp2518fd_handle_rx(priv, 0);
    if (rxif & BIT(1))
        mcp2518fd_handle_rx(priv, 1);

    /* Handle TX completions */
    if (txif & BIT(0)) {
        netdev->stats.tx_packets++;
        netdev->stats.tx_bytes += priv->can.echo_skb_max;
        netif_wake_queue(netdev);
    }

    /* Handle CAN bus errors */
    if (errif) {
        u32 con_reg;
        mcp2518fd_reg_read(priv, MCP2518FD_CON, &con_reg);

        if (errif & BIT(0)) {  /* RX overflow */
            netdev->stats.rx_over_errors++;
            mcp2518fd_reg_write(priv, MCP2518FD_RXOVIF, BIT(0));
        }

        /* Clear error interrupt flags */
        mcp2518fd_reg_write(priv, MCP2518FD_CERRIF, errif);
    }

    return IRQ_HANDLED;
}

/* ============================================================================
 * CAN Netdev Operations
 * ============================================================================ */

static int mcp2518fd_open(struct net_device *netdev)
{
    struct mcp2518fd_priv *priv = netdev_priv(netdev);
    int ret;

    /* Request interrupt */
    ret = request_irq(priv->int_gpio ? gpiod_to_irq(priv->int_gpio) :
                       priv->spi->irq,
                       mcp2518fd_irq, IRQF_TRIGGER_FALLING,
                       dev_name(&priv->spi->dev), priv);
    if (ret)
        return ret;

    /* Reset MCP2518FD via SPI command */
    mcp2518fd_spi_cmd(priv->spi_tx_buf, MCP2518FD_SPI_CMD_RESET, 0);
    spi_write(priv->spi, priv->spi_tx_buf, 2);
    msleep(50);  /* Wait for controller reset */

    /* Configure CAN mode: Normal + CAN-FD enabled */
    ret = mcp2518fd_reg_write(priv, MCP2518FD_CON,
                               CON_REQOP_CONFIG | CON_TXQEN | CON_STDEXT);
    if (ret)
        goto err_free_irq;

    /* Configure bit timing */
    ret = mcp2518fd_set_bittiming(priv);
    if (ret)
        goto err_free_irq;

    /* Configure RX FIFOs */
    mcp2518fd_reg_write(priv, MCP2518FD_FIFOCON(0),
                        BIT(31) | BIT(30) | BIT(27));  /* RX FIFO 0: enable, overflow, interrupt */
    mcp2518fd_reg_write(priv, MCP2518FD_FIFOCON(1),
                        BIT(31) | BIT(30) | BIT(27));  /* RX FIFO 1: enable, overflow, interrupt */

    /* Switch to Normal mode (CAN-FD with BRS) */
    ret = mcp2518fd_reg_write(priv, MCP2518FD_CON,
                               CON_REQOP_NORMAL | CON_TXQEN | CON_STDEXT | CON_ESIGM);
    if (ret)
        goto err_free_irq;

    /* Enable CAN interrupts */
    mcp2518fd_reg_write(priv, MCP2518FD_RXIF, 0x03);  /* RX FIFO 0 & 1 interrupt enable */
    mcp2518fd_reg_write(priv, MCP2518FD_TXIF, 0x01);  /* TX Queue interrupt enable */

    netif_start_queue(netdev);
    return 0;

err_free_irq:
    free_irq(priv->spi->irq, priv);
    return ret;
}

static int mcp2518fd_stop(struct net_device *netdev)
{
    struct mcp2518fd_priv *priv = netdev_priv(netdev);

    netif_stop_queue(netdev);

    /* Put MCP2518FD in Configuration mode (power saving) */
    mcp2518fd_reg_write(priv, MCP2518FD_CON, CON_REQOP_CONFIG);

    free_irq(priv->spi->irq, priv);
    return 0;
}

static const struct net_device_ops mcp2518fd_netdev_ops = {
    .ndo_open       = mcp2518fd_open,
    .ndo_stop        = mcp2518fd_stop,
    .ndo_start_xmit  = mcp2518fd_start_xmit,
    .ndo_change_mtu  = can_change_mtu,
};

/* ============================================================================
 * Device Tree Match Table
 * ============================================================================ */
static const struct of_device_id mcp2518fd_of_match[] = {
    {
        .compatible = "microchip,mcp2518fd",
        .data = NULL,  /* No variant-specific data for standard part */
    },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, mcp2518fd_of_match);

static const struct spi_device_id mcp2518fd_spi_id[] = {
    { "mcp2518fd", 0 },
    { }
};
MODULE_DEVICE_TABLE(spi, mcp2518fd_spi_id);

/* ============================================================================
 * SPI Driver Probe / Remove
 * ============================================================================ */
static int mcp2518fd_spi_probe(struct spi_device *spi)
{
    struct net_device *netdev;
    struct mcp2518fd_priv *priv;
    int ret;

    /* Validate SPI configuration */
    spi->mode = SPI_MODE_0;  /* CPOL=0, CPHA=0 */
    spi->max_speed_hz = MCP2518FD_SPI_SPEED_HZ;
    spi->bits_per_word = 8;

    ret = spi_setup(spi);
    if (ret)
        return dev_err_probe(&spi->dev, ret, "SPI setup failed\n");

    /* Allocate CAN netdev */
    netdev = alloc_candev(sizeof(struct mcp2518fd_priv), 1);
    if (!netdev)
        return -ENOMEM;

    priv = netdev_priv(netdev);
    priv->spi = spi;
    priv->can.clock.freq = 80000000;  /* 80 MHz CAN clock (from SYS_PLL1 / 10) */
    priv->can.bittiming_const = &mcp2518fd_bittiming_const;
    priv->can.data_bittiming_const = &mcp2518fd_data_bittiming_const;
    priv->can.do_set_bittiming = NULL;  /* Using fixed timing above */
    priv->can.ctrlmode_supported = CAN_CTRLMODE_FD |
                                    CAN_CTRLMODE_FD_NON_ISO |
                                    CAN_CTRLMODE_LISTENONLY |
                                    CAN_CTRLMODE_LOOPBACK;

    spin_lock_init(&priv->lock);

    /* Get GPIO descriptors from device tree */
    priv->rst_gpio = devm_gpiod_get_optional(&spi->dev, "reset",
                                              GPIOD_OUT_HIGH);
    if (IS_ERR(priv->rst_gpio))
        return PTR_ERR(priv->rst_gpio);

    priv->int_gpio = devm_gpiod_get(&spi->dev, "interrupt",
                                      GPIOD_IN);
    if (IS_ERR(priv->int_gpio))
        return PTR_ERR(priv->int_gpio);

    /* Get clocks */
    priv->can_clk = devm_clk_get(&spi->dev, "can_clk");
    if (IS_ERR(priv->can_clk)) {
        dev_info(&spi->dev, "No external CAN clock, using internal 80MHz\n");
        priv->can_clk = NULL;
    }

    /* Allocate DMA-coherent SPI buffers */
    priv->spi_tx_buf = dmam_alloc_coherent(&spi->dev, SPI_TX_RING_SIZE,
                                             &priv->spi_tx_dma, GFP_KERNEL);
    priv->spi_rx_buf = dmam_alloc_coherent(&spi->dev, SPI_RX_RING_SIZE,
                                             &priv->spi_rx_dma, GFP_KERNEL);
    if (!priv->spi_tx_buf || !priv->spi_rx_buf) {
        ret = -ENOMEM;
        goto err_free_netdev;
    }

    /* Hardware reset sequence */
    if (priv->rst_gpio) {
        gpiod_set_value_cansleep(priv->rst_gpio, 0);  /* Assert reset */
        msleep(10);
        gpiod_set_value_cansleep(priv->rst_gpio, 1);  /* Release reset */
        msleep(50);  /* Wait for MCP2518FD boot */
    }

    /* Register netdev */
    netdev->netdev_ops = &mcp2518fd_netdev_ops;
    netdev->flags |= IFF_ECHO;

    SET_NETDEV_DEV(netdev, &spi->dev);
    dev_set_drvdata(&spi->dev, priv);

    ret = register_candev(netdev);
    if (ret)
        goto err_free_netdev;

    dev_info(&spi->dev, "MCP2518FD CAN-FD controller registered: %s\n",
             netdev->name);
    return 0;

err_free_netdev:
    free_candev(netdev);
    return ret;
}

static void mcp2518fd_spi_remove(struct spi_device *spi)
{
    struct mcp2518fd_priv *priv = dev_get_drvdata(&spi->dev);
    struct net_device *netdev = priv->can.dev;

    unregister_candev(netdev);
    free_candev(netdev);
}

static struct spi_driver mcp2518fd_driver = {
    .driver = {
        .name = "mcp2518fd",
        .of_match_table = mcp2518fd_of_match,
        .pm = NULL,  /* Runtime PM not yet implemented */
    },
    .probe = mcp2518fd_spi_probe,
    .remove = mcp2518fd_spi_remove,
    .id_table = mcp2518fd_spi_id,
};

module_spi_driver(mcp2518fd_driver);

MODULE_AUTHOR("EAG-7000 Project");
MODULE_DESCRIPTION("Microchip MCP2518FD CAN-FD Controller SPI Driver");
MODULE_LICENSE("GPL");

/* CAN bit-timing constants for EAG-7000 (80 MHz CAN clock) */
static const struct can_bittiming_const mcp2518fd_bittiming_const = {
    .name = "mcp2518fd",
    .tseg1_min = 1, .tseg1_max = 255,
    .tseg2_min = 0, .tseg2_max = 127,
    .sjw_max = 127,
    .brp_min = 1, .brp_max = 255,
    .brp_inc = 1,
};

static const struct can_bittiming_const mcp2518fd_data_bittiming_const = {
    .name = "mcp2518fd",
    .tseg1_min = 1, .tseg1_max = 31,
    .tseg2_min = 0, .tseg2_max = 15,
    .sjw_max = 15,
    .brp_min = 1, .brp_max = 255,
    .brp_inc = 1,
};
```

### 4.4.1 Device Tree Overlay for MCP2518FD

```dts
/*
 * EAG-7000 — Device Tree Fragment for MCP2518FD CAN-FD Controllers
 * File: arch/arm64/boot/dts/freescale/imx8mp-eag7000-can.dtsi
 */

#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/interrupt-controller/irq.h>

/* ECSPI2 (SPI bus for CAN-FD controllers) */
&ecspi2 {
    #address-cells = <1>;
    #size-cells = <0>;
    fsl,spi-num-chipselects = <2>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi2>;
    status = "okay";

    /* CAN-FD Controller #0 — Industrial Bus 1 */
    can0: mcp2518fd@0 {
        compatible = "microchip,mcp2518fd";
        reg = <0>;  /* SPI chip select 0 */
        spi-max-frequency = <10000000>;  /* 10 MHz SPI clock */
        interrupts-extended = <&gpio4 5 IRQ_TYPE_LEVEL_LOW>;  /* GPIO4_IO05 (NPU_IRQ repurposed for CAN) */
        interrupt-parent = <&gpio4>;
        clocks = <&can_clk>;
        clock-names = "can_clk";
        vdd-supply = <&reg_3v3>;
        vio-supply = <&reg_3v3>;

        reset-gpios = <&gpio3 3 GPIO_ACTIVE_LOW>;   /* GPIO3_IO03 = CAN1_EN */
        standby-gpios = <&gpio3 5 GPIO_ACTIVE_HIGH>;  /* GPIO3_IO05 = CAN1_STB */

        pinctrl-names = "default";
        pinctrl-0 = <&pinctrl_can0>;
    };

    /* CAN-FD Controller #1 — Industrial Bus 2 */
    can1: mcp2518fd@1 {
        compatible = "microchip,mcp2518fd";
        reg = <1>;  /* SPI chip select 1 */
        spi-max-frequency = <10000000>;
        interrupts-extended = <&gpio4 6 IRQ_TYPE_LEVEL_LOW>;
        interrupt-parent = <&gpio4>;
        clocks = <&can_clk>;
        clock-names = "can_clk";
        vdd-supply = <&reg_3v3>;
        vio-supply = <&reg_3v3>;

        reset-gpios = <&gpio3 4 GPIO_ACTIVE_LOW>;   /* GPIO3_IO04 = CAN2_EN */
        standby-gpios = <&gpio3 6 GPIO_ACTIVE_HIGH>;  /* GPIO3_IO06 = CAN2_STB */

        pinctrl-names = "default";
        pinctrl-0 = <&pinctrl_can1>;
    };
};

/* IOMUXC pin configuration for ECSPI2 and CAN control pins */
&iomuxc {
    pinctrl_ecspi2: ecspi2grp {
        fsl,pins = <
            MX8MP_IOMUXC_ECSPI2_SCLK__ECSPI2_SCLK   0x138
            MX8MP_IOMUXC_ECSPI2_MOSI__ECSPI2_MOSI    0x138
            MX8MP_IOMUXC_ECSPI2_MISO__ECSPI2_MISO    0x138
            MX8MP_IOMUXC_ECSPI2_SS0__ECSPI2_SS0       0x138
            MX8MP_IOMUXC_ECSPI2_SS1__ECSPI2_SS1       0x138
        >;
    };

    pinctrl_can0: can0grp {
        fsl,pins = <
            MX8MP_IOMUXC_GPIO3_IO03__GPIO3_IO03    0x19  /* CAN0_EN (reset) */
            MX8MP_IOMUXC_GPIO3_IO05__GPIO3_IO05    0x19  /* CAN0_STB (standby) */
        >;
    };

    pinctrl_can1: can1grp {
        fsl,pins = <
            MX8MP_IOMUXC_GPIO3_IO04__GPIO3_IO04    0x19  /* CAN1_EN (reset) */
            MX8MP_IOMUXC_GPIO3_IO06__GPIO3_IO06    0x19  /* CAN1_STB (standby) */
        >;
    };
};

/* CAN clock definition (80 MHz from SYS_PLL1 divider) */
&clk {
    can_clk: can_clk {
        compatible = "fixed-clock";
        #clock-cells = <0>;
        clock-frequency = <80000000>;  /* 80 MHz */
    };
};
```

---

## 4.5 U-Boot SPL Board Initialization Stub

```c
/*
 * EAG-7000 — U-Boot SPL Board Initialization
 * File: board/eag7000/spl.c
 *
 * This runs from SRAM (before DRAM is initialized) and must:
 *   1. Configure PMIC (PCA9450) for correct voltage rails
 *   2. Initialize LPDDR4X timing parameters
 *   3. Set up boot media (eMMC)
 *   4. Load U-Boot proper into DRAM
 */

#include <common.h>
#include <init.h>
#include <asm/arch/clock.h>
#include <asm/arch/imx8mp_pins.h>
#include <asm/arch/sys_proto.h>
#include <asm/mach-imx/iomux-v3.h>
#include <power/pca9450.h>
#include <dm/device.h>

DECLARE_GLOBAL_DATA_PTR;

/* PMIC voltage rail configuration for EAG-7000 */
static const struct pca9450_regina eag7000_pmic_regs[] = {
    { PCA9450_BUCK1, 0x90 },  /* VDD_CORE = 0.9V */
    { PCA9450_BUCK2, 0x98 },  /* VDD_DDR  = 1.1V */
    { PCA9450_BUCK3, 0xC0 },  /* VDD_DDR_IO = 1.8V */
    { PCA9450_BUCK4, 0x80 },  /* VDD_SOC  = 1.0V */
    { PCA9450_BUCK5, 0xC0 },  /* VDD_1V8_DRAM = 1.8V */
    { PCA9450_BUCK6, 0xE0 },  /* VDD_3V3  = 3.3V */
    { PCA9450_LDO1,  0xC0 },  /* VDD_1V8  = 1.8V */
    { PCA9450_LDO2,  0x40 },  /* VDD_SNVS = 0.8V */
    { PCA9450_LDO3,  0x40 },  /* VDD_0V8_M4 = 0.8V */
    { PCA9450_LDO4,  0x80 },  /* VDD_PHY  = 1.0V */
};

int board_early_init_f(void)
{
    /* Configure SoC IOMUX and clocks (see eag7000_clock_init) */
    eag7000_clock_init();
    eag7000_gpio_init();

    return 0;
}

int power_init_board(void)
{
    struct udevice *pmic;
    int ret, i;

    ret = i2c_get_chip_for_busnum(0, PCA9450_I2C_ADDR, 1, &pmic);
    if (ret) {
        printf("PMIC PCA9450 not found: %d\n", ret);
        return ret;
    }

    /* Program all voltage rails */
    for (i = 0; i < ARRAY_SIZE(eag7000_pmic_regs); i++) {
        ret = dm_i2c_reg_write(pmic, eag7000_pmic_regs[i].reg,
                                eag7000_pmic_regs[i].val);
        if (ret) {
            printf("PMIC reg 0x%02x write failed: %d\n",
                   eag7000_pmic_regs[i].reg, ret);
            return ret;
        }
    }

    printf("PMIC PCA9450 configured for EAG-7000\n");
    return 0;
}

void spl_board_init(void)
{
    printf("EAG-7000 SPL — Initializing hardware...\n");
    printf("  SoC:     NXP i.MX8M Plus (MIMX8ML8CVNKZAB)\n");
    printf("  DRAM:    2x Micron MT53D512M32D4DS (8GB LPDDR4X)\n");
    printf("  Boot:    eMMC 5.1 (KIOXIA THGBMJG6C1LBAB7)\n");
    printf("  NPU:     Hailo-8 M.2 (26 TOPS, PCIe Gen3 x1)\n");
}
```

---

## 4.6 Software Build & Flash Summary

| Component | Source | Build Tool | Output | Flash Target |
|---|---|---|---|---|
| SPL | U-Boot 2024.04 + board/eag7000/spl.c | arm-gnu-toolchain (aarch64) | spl.bin | eMMC boot1 partition |
| U-Boot Proper | U-Boot 2024.04 + board/eag7000/ | arm-gnu-toolchain | u-boot.bin | eMMC boot1 partition |
| Linux Kernel | linux 6.6.x (NXP i.MX BSP) + mcp2518fd driver | cross-compile (aarch64) | Image + imx8mp-eag7000.dtb | eMMC userdata (ext4) |
| Root Filesystem | Yocto Kirkstone (eag7000-image) | bitbake | rootfs.ext4 | eMMC userdata partition |
| M4F Firmware | FreeRTOS + eag7000-m4f (CAN gateway) | arm-gnu-toolchain (cortex-m4) | eag7000-m4f.elf | eMMC boot2 partition |
| AI Runtime | ONNX Runtime + Hailo SDK | cross-compile | /usr/lib + /opt/hailo | eMMC userdata (ext4) |

### eMMC Partition Layout

| Partition | Offset | Size | Type | Content |
|---|---|---|---|---|
| boot1 | 0x0000 | 4 MiB | RAW | SPL + U-Boot proper |
| boot2 | 0x4000 | 4 MiB | RAW | M4F firmware (eag7000-m4f.elf) |
| rpmb | 0x8000 | 4 MiB | RPMB | Replay-protected memory (secure storage) |
| userdata | 0xC000 | ~28 GiB | ext4 | Linux rootfs (Kernel, DTB, userspace) |
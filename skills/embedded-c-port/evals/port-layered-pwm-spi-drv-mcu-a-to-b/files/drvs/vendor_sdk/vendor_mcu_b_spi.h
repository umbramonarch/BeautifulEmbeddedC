#ifndef VENDOR_MCU_B_SPI_H_
#define VENDOR_MCU_B_SPI_H_

#include <stdint.h>

/*
 * Target MCU-B SPI & GPIO Register SDK (96 MHz APB bus, 8-bit byte FIFO TXDR8/RXDR8)
 *
 * Key hardware differences from MCU-A:
 * 1. Peripheral clock `MCU_B_SPI_PCLK_HZ` is 96 MHz (double MCU-A's 48 MHz).
 *    Baud-rate field `CFG1.MBR` (bits [2:0]) divides PCLK by `(2U << mbr)` where `mbr` is 0..7:
 *      mbr=0 -> /2 (48 MHz), mbr=1 -> /4 (24 MHz), mbr=2 -> /8 (12 MHz),
 *      mbr=3 -> /16 (6 MHz), mbr=4 -> /32 (3 MHz), ..., mbr=7 -> /256 (375 kHz).
 * 2. On the MCU-B board, the external 12-bit DAC is connected to `MCU_B_SPI1`
 *    (`hwInstanceId = 1U`), and its active-low Chip-Select is on `GPIOC` Pin 2
 *    (`csPortId = 2U`, `csPin = 2U`, `isCsActiveLow = true`).
 * 3. `TXDR8` and `RXDR8` are 8-bit byte FIFO registers (not 16-bit!). A 16-bit frame word
 *    must be sent and received MSB-first as two 8-bit bytes:
 *      - Byte 0: high byte `(uint8_t)((txWord >> 8U) & 0xFFU)`
 *      - Byte 1: low byte  `(uint8_t)(txWord & 0xFFU)`
 * 4. Status flags in `SR` (`TXP` bit 0, `RXP` bit 1, `EOT` bit 3, `OVR` bit 6) are read-only.
 *    Clearing `EOT` or `OVR` requires a direct Write-1-to-Clear write to `IFCR`:
 *      `spi->IFCR = MCU_B_SPI_IFCR_EOTC_MASK | MCU_B_SPI_IFCR_OVRC_MASK;`
 * 5. GPIO ports (`GPIOA`=0, `GPIOB`=1, `GPIOC`=2) use atomic `BSRR`:
 *      - `BSRR = (1U << pin)` drives pin HIGH.
 *      - `BSRR = (1U << (pin + 16U))` drives pin LOW.
 */

#define MCU_B_SPI_PCLK_HZ        (96000000U)
#define MCU_B_SPI_INSTANCE_COUNT (2U)
#define MCU_B_GPIO_PORT_COUNT    (3U)

typedef struct {
    volatile uint32_t CR1;   /* Control register 1 (SPE enable, CSTART transfer start) */
    volatile uint32_t CFG1;  /* Configuration register 1 (MBR baud divider, MASTER, CPOL/CPHA) */
    volatile uint32_t SR;    /* Read-only status register (TXP, RXP, EOT, OVR) */
    volatile uint32_t IFCR;  /* Write-1-to-Clear interrupt/status flag clear register */
    volatile uint8_t  TXDR8; /* 8-bit transmit FIFO data register */
    uint8_t           RESERVED0[3];
    volatile uint8_t  RXDR8; /* 8-bit receive FIFO data register */
    uint8_t           RESERVED1[3];
} MCU_B_SPI_TypeDef;

typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;  /* Atomic bit set [15:0] / bit reset [31:16] */
} MCU_B_GPIO_TypeDef;

/* CR1 bit masks */
#define MCU_B_SPI_CR1_SPE_POS       (0U)
#define MCU_B_SPI_CR1_SPE_MASK      (UINT32_C(1) << MCU_B_SPI_CR1_SPE_POS)
#define MCU_B_SPI_CR1_CSTART_POS    (9U)
#define MCU_B_SPI_CR1_CSTART_MASK   (UINT32_C(1) << MCU_B_SPI_CR1_CSTART_POS)

/* CFG1 bit masks */
#define MCU_B_SPI_CFG1_MBR_POS      (0U)
#define MCU_B_SPI_CFG1_MBR_MASK     (UINT32_C(0x7) << MCU_B_SPI_CFG1_MBR_POS)
#define MCU_B_SPI_CFG1_CPHA_POS     (4U)
#define MCU_B_SPI_CFG1_CPOL_POS     (5U)
#define MCU_B_SPI_CFG1_MASTER_POS   (22U)
#define MCU_B_SPI_CFG1_MASTER_MASK  (UINT32_C(1) << MCU_B_SPI_CFG1_MASTER_POS)

/* SR status masks (read-only) */
#define MCU_B_SPI_SR_TXP_MASK       (UINT32_C(1) << 0U) /* TX FIFO has space for >= 1 byte */
#define MCU_B_SPI_SR_RXP_MASK       (UINT32_C(1) << 1U) /* RX FIFO contains >= 1 byte */
#define MCU_B_SPI_SR_EOT_MASK       (UINT32_C(1) << 3U) /* End of transfer complete */
#define MCU_B_SPI_SR_OVR_MASK       (UINT32_C(1) << 6U) /* Overrun error */

/* IFCR Write-1-to-Clear masks */
#define MCU_B_SPI_IFCR_EOTC_MASK    (UINT32_C(1) << 3U) /* Write 1 to clear EOT */
#define MCU_B_SPI_IFCR_OVRC_MASK    (UINT32_C(1) << 6U) /* Write 1 to clear OVR */

/* GPIO BSRR helper macros */
#define MCU_B_GPIO_BSRR_SET(pin)    (UINT32_C(1) << (uint32_t)(pin))
#define MCU_B_GPIO_BSRR_RESET(pin)  (UINT32_C(1) << ((uint32_t)(pin) + 16U))

#if defined(__GNUC__) || defined(__clang__)
__attribute__((weak)) MCU_B_SPI_TypeDef MCU_B_SPI_Instances[MCU_B_SPI_INSTANCE_COUNT];
__attribute__((weak)) MCU_B_GPIO_TypeDef MCU_B_GPIO_Ports[MCU_B_GPIO_PORT_COUNT];
#else
extern MCU_B_SPI_TypeDef MCU_B_SPI_Instances[MCU_B_SPI_INSTANCE_COUNT];
extern MCU_B_GPIO_TypeDef MCU_B_GPIO_Ports[MCU_B_GPIO_PORT_COUNT];
#endif

#define MCU_B_SPI0  (&MCU_B_SPI_Instances[0])
#define MCU_B_SPI1  (&MCU_B_SPI_Instances[1])
#define MCU_B_GPIOA (&MCU_B_GPIO_Ports[0])
#define MCU_B_GPIOB (&MCU_B_GPIO_Ports[1])
#define MCU_B_GPIOC (&MCU_B_GPIO_Ports[2])

#endif /* VENDOR_MCU_B_SPI_H_ */

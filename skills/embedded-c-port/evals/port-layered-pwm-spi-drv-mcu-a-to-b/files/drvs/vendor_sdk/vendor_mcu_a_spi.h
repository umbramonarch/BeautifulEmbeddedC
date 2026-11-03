#ifndef VENDOR_MCU_A_SPI_H_
#define VENDOR_MCU_A_SPI_H_

#include <stdint.h>

/*
 * Source MCU-A SPI & GPIO Register SDK (48 MHz peripheral bus, 16-bit data register DR16)
 *
 * - MCU_A_SPI0 (hwInstanceId = 0) transfers 16-bit words directly via DR16.
 * - CTRL bits [5:3] select baud-rate divider: PCLK / (2 << brDiv) where PCLK = 48 MHz.
 * - Status register SR uses read-modify-write (`SR &= ~MCU_A_SPI_SR_OVR_MASK`) to clear flags.
 * - GPIO ports use direct output latch register `OUT` (non-atomic RMW).
 */

#define MCU_A_SPI_PCLK_HZ        (48000000U)
#define MCU_A_SPI_INSTANCE_COUNT (2U)
#define MCU_A_GPIO_PORT_COUNT    (3U)

typedef struct {
    volatile uint32_t CTRL;
    volatile uint32_t SR;
    volatile uint16_t DR16;
    uint16_t RESERVED;
} MCU_A_SPI_TypeDef;

typedef struct {
    volatile uint32_t DIR;
    volatile uint32_t OUT;
} MCU_A_GPIO_TypeDef;

#define MCU_A_SPI_CTRL_EN_POS      (0U)
#define MCU_A_SPI_CTRL_EN_MASK     (UINT32_C(1) << MCU_A_SPI_CTRL_EN_POS)
#define MCU_A_SPI_CTRL_MASTER_POS  (1U)
#define MCU_A_SPI_CTRL_MASTER_MASK (UINT32_C(1) << MCU_A_SPI_CTRL_MASTER_POS)
#define MCU_A_SPI_CTRL_MODE_POS    (2U)
#define MCU_A_SPI_CTRL_BR_POS      (4U)
#define MCU_A_SPI_CTRL_BR_MASK     (UINT32_C(0x7) << MCU_A_SPI_CTRL_BR_POS)

#define MCU_A_SPI_SR_TXE_MASK      (UINT32_C(1) << 0U)
#define MCU_A_SPI_SR_RXNE_MASK     (UINT32_C(1) << 1U)
#define MCU_A_SPI_SR_OVR_MASK      (UINT32_C(1) << 6U)
#define MCU_A_SPI_SR_BSY_MASK      (UINT32_C(1) << 7U)

#if defined(__GNUC__) || defined(__clang__)
__attribute__((weak)) MCU_A_SPI_TypeDef MCU_A_SPI_Instances[MCU_A_SPI_INSTANCE_COUNT];
__attribute__((weak)) MCU_A_GPIO_TypeDef MCU_A_GPIO_Ports[MCU_A_GPIO_PORT_COUNT];
#else
extern MCU_A_SPI_TypeDef MCU_A_SPI_Instances[MCU_A_SPI_INSTANCE_COUNT];
extern MCU_A_GPIO_TypeDef MCU_A_GPIO_Ports[MCU_A_GPIO_PORT_COUNT];
#endif

#define MCU_A_SPI0 (&MCU_A_SPI_Instances[0])
#define MCU_A_SPI1 (&MCU_A_SPI_Instances[1])

#endif /* VENDOR_MCU_A_SPI_H_ */

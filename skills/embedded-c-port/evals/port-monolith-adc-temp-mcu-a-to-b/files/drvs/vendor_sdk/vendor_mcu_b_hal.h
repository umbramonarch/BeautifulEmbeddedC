#ifndef VENDOR_MCU_B_HAL_H
#define VENDOR_MCU_B_HAL_H

#include <stdint.h>

/*
 * Target 32-bit MCU-B Register HAL (drvs/vendor_sdk/vendor_mcu_b_hal.h)
 *
 * Key hardware differences from legacy 16-bit MCU-A:
 * 1. 12-bit SAR ADC (0..4095 counts) with 3.3V (3300 mV) Vref.
 * 2. 32-bit MMIO registers accessed via explicit shift/mask macros (no bit-fields).
 * 3. Interrupt & Status Register (ISR) is Write-1-to-Clear (W1C):
 *    Writing `MCU_B_ADC1->ISR = MCU_B_ADC_ISR_EOC_MASK` clears EOC without disturbing
 *    other flags. Using `|=` or `&=` on ISR corrupts sibling status bits.
 * 4. GPIOB uses an atomic Bit Set/Reset Register (BSRR):
 *    - Writing `(1U << pin)` to bits [15:0] drives the pin HIGH.
 *    - Writing `(1U << (pin + 16U))` to bits [31:16] drives the pin LOW.
 *    On the MCU-B board, the Heater Cutoff relay is wired to PB4 and is ACTIVE-LOW
 *    (driving PB4 LOW asserts heater cutoff; driving PB4 HIGH deasserts cutoff).
 */

typedef struct {
    volatile uint32_t CR;    /* Control register */
    volatile uint32_t CHSEL; /* Channel selection register (channel index 0..15) */
    volatile uint32_t ISR;   /* Interrupt & status register (Write-1-to-Clear!) */
    volatile uint32_t DR;    /* 12-bit conversion data register (0..4095) */
} MCU_B_ADC_TypeDef;

typedef struct {
    volatile uint32_t MODER; /* Mode register */
    volatile uint32_t ODR;   /* Output data register */
    volatile uint32_t BSRR;  /* Atomic bit set (bits 0..15) / reset (bits 16..31) */
} MCU_B_GPIO_TypeDef;

/* ADC Control Register (CR) masks */
#define MCU_B_ADC_CR_ADEN_POS     (0U)
#define MCU_B_ADC_CR_ADEN_MASK    (UINT32_C(1) << MCU_B_ADC_CR_ADEN_POS)
#define MCU_B_ADC_CR_START_POS    (1U)
#define MCU_B_ADC_CR_START_MASK   (UINT32_C(1) << MCU_B_ADC_CR_START_POS)

/* ADC Interrupt & Status Register (ISR) masks — Write-1-to-Clear (W1C) */
#define MCU_B_ADC_ISR_EOC_POS     (2U)
#define MCU_B_ADC_ISR_EOC_MASK    (UINT32_C(1) << MCU_B_ADC_ISR_EOC_POS)
#define MCU_B_ADC_ISR_OVR_POS     (3U)
#define MCU_B_ADC_ISR_OVR_MASK    (UINT32_C(1) << MCU_B_ADC_ISR_OVR_POS)

/* ADC physical characteristics on MCU-B */
#define MCU_B_ADC_RESOLUTION_BITS (12U)
#define MCU_B_ADC_MAX_COUNTS      (4095U)
#define MCU_B_ADC_VREF_MV         (3300U)

/* GPIOB Heater Cutoff wiring on MCU-B (PB4, Active-Low) */
#define MCU_B_GPIOB_HEATER_CUTOFF_PIN (4U)
#define MCU_B_GPIO_BSRR_SET(pin)      (UINT32_C(1) << (uint32_t)(pin))
#define MCU_B_GPIO_BSRR_RESET(pin)    (UINT32_C(1) << ((uint32_t)(pin) + 16U))

#if defined(__GNUC__) || defined(__clang__)
__attribute__((weak)) MCU_B_ADC_TypeDef MCU_B_ADC1_Instance;
__attribute__((weak)) MCU_B_GPIO_TypeDef MCU_B_GPIOB_Instance;
__attribute__((weak)) uint32_t MCU_B_MockPrimask;
#else
extern MCU_B_ADC_TypeDef MCU_B_ADC1_Instance;
extern MCU_B_GPIO_TypeDef MCU_B_GPIOB_Instance;
extern uint32_t MCU_B_MockPrimask;
#endif

#define MCU_B_ADC1  (&MCU_B_ADC1_Instance)
#define MCU_B_GPIOB (&MCU_B_GPIOB_Instance)

static inline uint32_t mcuB_IrqSaveAndDisable(void) {
    uint32_t const prev = MCU_B_MockPrimask;
    MCU_B_MockPrimask = 1U;
    return prev;
}

static inline void mcuB_IrqRestore(uint32_t irqState) {
    MCU_B_MockPrimask = irqState;
}

#endif /* VENDOR_MCU_B_HAL_H */

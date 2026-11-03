#ifndef VENDOR_MCU_A_REGS_H
#define VENDOR_MCU_A_REGS_H

#include <stdint.h>

/*
 * Legacy 16-bit MCU-A hardware register definitions:
 * - 10-bit Successive Approximation ADC (0..1023 counts) with 5.0V (5000 mV) Vref
 * - C bit-field control/status register where DONE is cleared by writing 0 (RMW &= ~)
 * - Port A GPIO output latch where bit 3 drives an active-high heater cutoff relay
 */

typedef struct {
    unsigned int EN    : 1;
    unsigned int START : 1;
    unsigned int DONE  : 1;
    unsigned int IE    : 1;
    unsigned int CH    : 4;
    unsigned int RSVD  : 8;
} MCU_A_ADC_CS_Bits_t;

typedef struct {
    volatile MCU_A_ADC_CS_Bits_t CS;
    volatile uint16_t RESULT; /* 10-bit conversion result (0..1023 at 5.0V Vref) */
} MCU_A_ADC_Regs_t;

extern MCU_A_ADC_Regs_t MCU_A_ADC0_Instance;
extern volatile uint16_t MCU_A_PORTA_OUT;

#define MCU_A_ADC0                  (&MCU_A_ADC0_Instance)
#define MCU_A_PORTA_HEATER_CUTOFF   (1U << 3) /* Active-high on MCU-A board */

#endif /* VENDOR_MCU_A_REGS_H */

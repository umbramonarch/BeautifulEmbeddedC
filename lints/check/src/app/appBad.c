//-------------------------------------------------------------------------------------------------//
/**
 * @file        appBad.c
 * @brief       Deliberate violation fixture for app layer, JPL, BARR-C, and RTOS rules
 */
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdint.h>
#include "drvPwm.h" // expect: [BENINGO-ARCH-01]

//-------------------------------------------------------------------------------------------------//
//             Private Prototypes
//-------------------------------------------------------------------------------------------------//
static uint32_t prv_Recurse(uint32_t depth);

//-------------------------------------------------------------------------------------------------//
//             Implementation
//-------------------------------------------------------------------------------------------------//
static uint32_t prv_Recurse(uint32_t depth) {
    if (depth == 0U) {
        return 0U;
    }
    return prv_Recurse(depth - 1U); // expect: [JPL-1]
}

uint32_t appBad_ControlFlowAndAlloc(uint32_t reg, uint32_t state) {
    const char *safeStr = "switch (x) { case 1: goto float malloc : 3; }";
    (void)safeStr;

    void *stackBuf = alloca(16U); // expect: [JPL-1]
    (void)stackBuf;

    void *heapBuf = malloc(32U); // expect: [JPL-3]
    (void)heapBuf;

    while ((reg & 1U) == 0U); // expect: [JPL-2]

    switch (state) { // expect: [BARR-8.3.b]
        case 0U: {
            reg += 1U;
            break;
        }
        case 1U: {
            reg += 2U;
            break;
        }
    }

    switch (state) {
        case 0U: {
            reg += 1U;
            break;
        }
        default: {
            break;
        }
    }

    __enable_irq(); // expect: [BARR-ISR-ATOMIC]
    xQueueCreate(4U, sizeof(uint32_t)); // expect: [RTOS-STATIC-01]
    xQueueReceive(0, &reg, portMAX_DELAY); // expect: [RTOS-WDT-01]

    if (reg == 99U) {
        goto cleanup; // expect: [JPL-1]
    }
cleanup:
    return prv_Recurse(reg);
}

void TIM2_IRQHandler(void) {
    xSemaphoreTake(0, 0U); // expect: [RTOS-ISR-01]
}

uint32_t appBad_OverlongFunction(uint32_t seed) { // expect: [JPL-4]
    uint32_t acc = seed;
    acc += 1U;
    acc += 2U;
    acc += 3U;
    acc += 4U;
    acc += 5U;
    acc += 6U;
    acc += 7U;
    acc += 8U;
    acc += 9U;
    acc += 10U;
    acc += 11U;
    acc += 12U;
    acc += 13U;
    acc += 14U;
    acc += 15U;
    acc += 16U;
    acc += 17U;
    acc += 18U;
    acc += 19U;
    acc += 20U;
    acc += 21U;
    acc += 22U;
    acc += 23U;
    acc += 24U;
    acc += 25U;
    acc += 26U;
    acc += 27U;
    acc += 28U;
    acc += 29U;
    acc += 30U;
    acc += 31U;
    acc += 32U;
    acc += 33U;
    acc += 34U;
    acc += 35U;
    acc += 36U;
    acc += 37U;
    acc += 38U;
    acc += 39U;
    acc += 40U;
    acc += 41U;
    acc += 42U;
    acc += 43U;
    acc += 44U;
    acc += 45U;
    acc += 46U;
    acc += 47U;
    acc += 48U;
    acc += 49U;
    acc += 50U;
    acc += 51U;
    acc += 52U;
    acc += 53U;
    acc += 54U;
    acc += 55U;
    acc += 56U;
    acc += 57U;
    acc += 58U;
    acc += 59U;
    acc += 60U;
    return acc;
}

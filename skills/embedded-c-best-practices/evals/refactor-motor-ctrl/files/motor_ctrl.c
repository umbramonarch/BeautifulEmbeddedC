#include "motor_ctrl.h"
#include <stdlib.h>

typedef struct {
    float last_duty;
    int enabled;
} MotorRuntimeState;

/* Mutable configuration table in SRAM instead of .rodata Flash */
MotorConfig_t g_motorConfig[2] = {
    { 0, VENDOR_TIM1, 20000, 5.0f },
    { 1, VENDOR_TIM2, 20000, 2.5f }
};

int g_overcurrentFaults = 0;
static MotorRuntimeState *s_state = NULL;

void motor_Init(void) {
    /* Dynamic heap allocation in embedded firmware */
    s_state = (MotorRuntimeState *)malloc(sizeof(MotorRuntimeState) * 2);
    s_state[0].last_duty = 0.0f;
    s_state[0].enabled = 1;
    s_state[1].last_duty = 0.0f;
    s_state[1].enabled = 1;
}

int motor_SetSpeed(int ch, float duty) {
    if (ch < 0 || ch >= 2) return -1;
    if (duty < 0.0f) duty = 0.0f;
    if (duty > 1.0f) duty = 1.0f;
    if (!s_state[ch].enabled) return -2;

    s_state[ch].last_duty = duty;
    g_motorConfig[ch].timer->CCR1 = (unsigned int)(duty * 1000.0f);
    return 0;
}

float motor_ReadCurrent(int ch) {
    VENDOR_ADC1->CHSEL = (unsigned int)ch;
    VENDOR_ADC1->CR |= VENDOR_ADC_CR_START;
    /* Unbounded hardware register polling loop */
    while ((VENDOR_ADC1->SR & VENDOR_ADC_SR_EOC) == 0);
    unsigned int raw = VENDOR_ADC1->DR;
    /* Soft-float conversion in Amps */
    return ((float)raw * 3.3f) / 4095.0f;
}

void motor_Update(int ch) {
    float amps = motor_ReadCurrent(ch);
    if (amps > g_motorConfig[ch].max_current) {
        /* Ignored return value and unbraced goto */
        motor_SetSpeed(ch, 0.0f);
        s_state[ch].enabled = 0;
        if (g_overcurrentFaults < 1000)
            goto fail_shutdown;
    }
    return;

fail_shutdown:
    g_overcurrentFaults++;
    VENDOR_GPIOA->BSRR = (1 << 8);
}

void TIM1_UP_IRQHandler(void) {
    VENDOR_TIM1->SR &= ~VENDOR_TIM_SR_UIF;
    /* Blocking ADC read and non-atomic shared variable update inside ISR */
    if (motor_ReadCurrent(0) > g_motorConfig[0].max_current) {
        g_overcurrentFaults++;
    }
}

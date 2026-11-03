#include "ntc_monitor.h"
#include <stdlib.h>

typedef struct {
    float last_temp_c;
    int tripped;
} NtcRuntimeState_t;

/* Mutable configuration table in SRAM instead of const .rodata Flash */
NtcChannelConfig_t g_ntcConfig[2] = {
    { 0, MCU_A_ADC0, 80.0f, 70.0f }, /* Ch 0: Power stage NTC */
    { 1, MCU_A_ADC0, 60.0f, 50.0f }  /* Ch 1: Battery pack NTC */
};

int g_overtempFaultCount = 0;
static NtcRuntimeState_t *s_state = NULL;

void ntc_Init(void) {
    /* Dynamic heap allocation in embedded firmware */
    s_state = (NtcRuntimeState_t *)malloc(sizeof(NtcRuntimeState_t) * 2);
    s_state[0].last_temp_c = 25.0f;
    s_state[0].tripped = 0;
    s_state[1].last_temp_c = 25.0f;
    s_state[1].tripped = 0;

    MCU_A_ADC0->CS.EN = 1;
    MCU_A_PORTA_OUT &= (uint16_t)(~MCU_A_PORTA_HEATER_CUTOFF);
}

float ntc_ReadTempC(int ch) {
    g_ntcConfig[ch].adc->CS.CH = (unsigned int)ch;
    g_ntcConfig[ch].adc->CS.DONE = 0; /* RMW bit-field clear on MCU-A */
    g_ntcConfig[ch].adc->CS.START = 1;

    /* Unbounded hardware register polling loop */
    while (g_ntcConfig[ch].adc->CS.DONE == 0);

    uint16_t raw = g_ntcConfig[ch].adc->RESULT;
    /* MCU-A 10-bit ADC (0..1023) at 5.0V Vref using soft-float arithmetic */
    float volts = ((float)raw * 5.0f) / 1023.0f;
    return 100.0f - (volts * 20.0f);
}

int ntc_UpdateChannel(int ch) {
    if (ch < 0 || ch >= 2) return -1;

    float temp_c = ntc_ReadTempC(ch);
    s_state[ch].last_temp_c = temp_c;

    if (!s_state[ch].tripped && temp_c >= g_ntcConfig[ch].trip_temp_c) {
        s_state[ch].tripped = 1;
        goto latch_fault;
    } else if (s_state[ch].tripped && temp_c <= g_ntcConfig[ch].recover_temp_c) {
        s_state[ch].tripped = 0;
    }

    if (s_state[0].tripped || s_state[1].tripped)
        MCU_A_PORTA_OUT |= MCU_A_PORTA_HEATER_CUTOFF;
    else
        MCU_A_PORTA_OUT &= (uint16_t)(~MCU_A_PORTA_HEATER_CUTOFF);

    return s_state[ch].tripped;

latch_fault:
    g_overtempFaultCount++;
    MCU_A_PORTA_OUT |= MCU_A_PORTA_HEATER_CUTOFF;
    return 1;
}

int ntc_IsHeaterCutoffActive(void) {
    return (s_state[0].tripped || s_state[1].tripped) ? 1 : 0;
}

void ADC_COMP_IRQHandler(void) {
    /* Non-atomic RMW of shared fault counter and heavy float polling in ISR */
    if (ntc_ReadTempC(0) >= g_ntcConfig[0].trip_temp_c) {
        g_overtempFaultCount++;
        MCU_A_PORTA_OUT |= MCU_A_PORTA_HEATER_CUTOFF;
    }
}

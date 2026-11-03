#ifndef NTC_MONITOR_H
#define NTC_MONITOR_H

#include "vendor_mcu_a_regs.h"

/*
 * Deliberately flawed monolithic MCU-A thermistor monitor fixture for
 * BeautifulEmbeddedC cross-MCU porting evaluation.
 */

typedef struct {
    int adc_channel;
    MCU_A_ADC_Regs_t *adc;
    float trip_temp_c;
    float recover_temp_c;
} NtcChannelConfig_t;

extern NtcChannelConfig_t g_ntcConfig[2];
extern int g_overtempFaultCount;

void ntc_Init(void);
float ntc_ReadTempC(int ch);
int ntc_UpdateChannel(int ch);
int ntc_IsHeaterCutoffActive(void);

#endif /* NTC_MONITOR_H */

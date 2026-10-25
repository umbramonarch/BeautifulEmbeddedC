#ifndef MOTOR_CTRL_H
#define MOTOR_CTRL_H

#include "vendor_mcu_hal.h"

/* Deliberately flawed fixture for BeautifulEmbeddedC refactor & review evals */

typedef struct {
    int channel;
    VENDOR_TIM_Regs *timer;
    int pwm_freq;
    float max_current;
} MotorConfig_t;

extern MotorConfig_t g_motorConfig[2];
extern int g_overcurrentFaults;

void motor_Init(void);
int motor_SetSpeed(int ch, float duty);
float motor_ReadCurrent(int ch);
void motor_Update(int ch);

#endif

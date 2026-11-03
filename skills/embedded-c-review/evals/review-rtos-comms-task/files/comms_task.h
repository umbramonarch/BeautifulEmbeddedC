//-------------------------------------------------------------------------------------------------//
/**
 * @file        comms_task.h
 * @brief       RS-485 telemetry RTOS task and USART2 interrupt interface
 */
//-------------------------------------------------------------------------------------------------//
#ifndef COMMS_TASK_H_
#define COMMS_TASK_H_

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "FreeRTOS.h"
#include "queue.h"
#include "semphr.h"
#include "task.h"
#include "vendor_usart_hal.h"

//-------------------------------------------------------------------------------------------------//
//             Exported Macros
//-------------------------------------------------------------------------------------------------//
#define COMMS_ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//
typedef enum {
    COMMS_BAUD_9600 = 0,
    COMMS_BAUD_115200,
    COMMS_BAUD_COUNT
} CommsBaudProfile_e;

typedef enum {
    COMMS_CMD_PING = 1,
    COMMS_CMD_SET_VBUS_LIMIT = 2,
    COMMS_CMD_CLEAR_FAULTS = 3
} CommsCmd_e;

typedef struct {
    uint32_t baudRate_hz;
    uint16_t turnaroundDelay_us;
} CommsBaudConfig_t;

typedef struct {
    CommsCmd_e cmd;
    int32_t payload_mv;
} CommsFrame_t;

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//
extern const CommsBaudConfig_t kCommsBaudConfigTable[COMMS_BAUD_COUNT];

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
void comms_Init(void);
void vCommsTask(void *pvParameters);
int comms_SendTelemetryMv(int32_t busVoltage_mv);
uint32_t comms_TakeErrorCount(void);
void USART2_IRQHandler(void);

#endif /* COMMS_TASK_H_ */

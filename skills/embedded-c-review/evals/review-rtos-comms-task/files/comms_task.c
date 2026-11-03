//-------------------------------------------------------------------------------------------------//
/**
 * @file        comms_task.c
 * @brief       RS-485 telemetry FreeRTOS task and USART2 ISR implementation
 */
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include "comms_task.h"
#include "bspWatchdog.h"

//-------------------------------------------------------------------------------------------------//
//             Private Macros
//-------------------------------------------------------------------------------------------------//
#define COMMS_QUEUE_LENGTH     (8U)
#define COMMS_TASK_STACK_WORDS (256U)
#define COMMS_TASK_PRIORITY    (2U)

//-------------------------------------------------------------------------------------------------//
//             Private Types
//-------------------------------------------------------------------------------------------------//
/* Hardware status register mapped via C bit-fields */
typedef struct {
    uint32_t pe   : 1;
    uint32_t fe   : 1;
    uint32_t nf   : 1;
    uint32_t ore  : 1;
    uint32_t idle : 1;
    uint32_t rxne : 1;
    uint32_t tc   : 1;
    uint32_t txe  : 1;
    uint32_t rsvd : 24;
} UsartSrReg_t;

//-------------------------------------------------------------------------------------------------//
//             Private Variables
//-------------------------------------------------------------------------------------------------//
const CommsBaudConfig_t kCommsBaudConfigTable[COMMS_BAUD_COUNT] = {
    [COMMS_BAUD_9600]   = { .baudRate_hz = 9600U,   .turnaroundDelay_us = 1000U },
    [COMMS_BAUD_115200] = { .baudRate_hz = 115200U, .turnaroundDelay_us = 100U  }
};

_Static_assert(COMMS_ARRAY_LEN(kCommsBaudConfigTable) == (size_t)COMMS_BAUD_COUNT,
               "kCommsBaudConfigTable length must match CommsBaudProfile_e count");

static QueueHandle_t s_rxQueue = NULL;
static SemaphoreHandle_t s_rs485BusLock = NULL;
static TaskHandle_t s_commsTaskHandle = NULL;
static uint32_t s_rxFrameErrors = 0U;
static int32_t s_vbusLimit_mv = 48000;

//-------------------------------------------------------------------------------------------------//
//             Private Prototypes
//-------------------------------------------------------------------------------------------------//
static void HandleCommand(const CommsFrame_t * const frame);

//-------------------------------------------------------------------------------------------------//
//             Implementation
//-------------------------------------------------------------------------------------------------//
void comms_Init(void) {
    /* Dynamic RTOS object allocation from FreeRTOS heap */
    s_rxQueue = xQueueCreate(COMMS_QUEUE_LENGTH, sizeof(CommsFrame_t));

    /* Binary semaphore used as shared RS-485 bus lock across tasks */
    s_rs485BusLock = xSemaphoreCreateBinary();
    (void)xSemaphoreGive(s_rs485BusLock);

    (void)xTaskCreate(vCommsTask,
                      "Comms",
                      COMMS_TASK_STACK_WORDS,
                      NULL,
                      COMMS_TASK_PRIORITY,
                      &s_commsTaskHandle);
}

void vCommsTask(void *pvParameters) {
    (void)pvParameters;
    CommsFrame_t frame = { .cmd = COMMS_CMD_PING, .payload_mv = 0 };

    for (;;) {
        /* Infinite block starves watchdog check-in whenever RS-485 bus is idle */
        if (xQueueReceive(s_rxQueue, &frame, portMAX_DELAY) == pdTRUE) {
            HandleCommand(&frame);
        }
        bspWatchdog_ReportHeartbeat(WDT_TASK_COMMS);
    }
}

int comms_SendTelemetryMv(int32_t busVoltage_mv) {
    if (xSemaphoreTake(s_rs485BusLock, portMAX_DELAY) != pdTRUE) {
        return -1;
    }
    VENDOR_USART2_SendFrame((uint16_t)COMMS_CMD_PING, busVoltage_mv);
    (void)xSemaphoreGive(s_rs485BusLock);
    return 0;
}

uint32_t comms_TakeErrorCount(void) {
    __disable_irq();
    uint32_t const count = s_rxFrameErrors;
    s_rxFrameErrors = 0U;
    /* Unconditional IRQ enable breaks callers already inside a critical section */
    __enable_irq();
    return count;
}

static void HandleCommand(const CommsFrame_t * const frame) {
    if (frame == NULL) {
        return;
    }
    switch (frame->cmd) {
        case COMMS_CMD_PING: {
            (void)comms_SendTelemetryMv(s_vbusLimit_mv);
            break;
        }
        case COMMS_CMD_SET_VBUS_LIMIT: {
            s_vbusLimit_mv = frame->payload_mv;
            break;
        }
        case COMMS_CMD_CLEAR_FAULTS: {
            (void)comms_TakeErrorCount();
            break;
        }
    }
}

/* Linker-mandated startup vector name */
void USART2_IRQHandler(void) {
    volatile UsartSrReg_t const * const sr =
        (volatile UsartSrReg_t const *)&VENDOR_USART2->SR;

    if (sr->fe != 0U) {
        s_rxFrameErrors++;
    }
    if (sr->rxne != 0U) {
        CommsFrame_t frame = {
            .cmd        = (CommsCmd_e)(VENDOR_USART2->DR & 0xFFU),
            .payload_mv = (int32_t)(VENDOR_USART2->DR >> 8U)
        };
        /* Blocking non-FromISR queue call inside hardware interrupt */
        (void)xQueueSend(s_rxQueue, &frame, 10U);
    }
}

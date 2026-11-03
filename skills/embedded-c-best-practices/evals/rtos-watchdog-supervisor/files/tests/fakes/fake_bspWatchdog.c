//-------------------------------------------------------------------------------------------------//
/**
 * @file        fake_bspWatchdog.c
 * @brief       Link-time fake implementation for bspWatchdog and bspRtos host unit tests
 */
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include "fake_bspWatchdog.h"

//-------------------------------------------------------------------------------------------------//
//             Private Macros
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Private Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Private Variables
//-------------------------------------------------------------------------------------------------//
static bool s_isWdtInitialized = false;
static Milliseconds_t s_configuredWindow_ms = {.ms = 0U};
static uint32_t s_kickCount = 0U;
static uint8_t s_latchedFaultTask = FAKE_WDT_NO_FAULT_TASK;
static uint32_t s_criticalEnterCount = 0U;
static uint32_t s_criticalExitCount = 0U;
static uint32_t s_staticTaskCreateCount = 0U;
static Milliseconds_t s_lastDelay_ms = {.ms = 0U};

//-------------------------------------------------------------------------------------------------//
//             Private Prototypes
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Implementation
//-------------------------------------------------------------------------------------------------//
void fakeBspWatchdog_Reset(void) {
    s_isWdtInitialized = false;
    s_configuredWindow_ms.ms = 0U;
    s_kickCount = 0U;
    s_latchedFaultTask = FAKE_WDT_NO_FAULT_TASK;
    s_criticalEnterCount = 0U;
    s_criticalExitCount = 0U;
    s_staticTaskCreateCount = 0U;
    s_lastDelay_ms.ms = 0U;
}

uint32_t fakeBspWatchdog_GetKickCount(void) {
    return s_kickCount;
}

uint8_t fakeBspWatchdog_GetLatchedFaultTask(void) {
    return s_latchedFaultTask;
}

Milliseconds_t fakeBspWatchdog_GetConfiguredWindowMs(void) {
    return s_configuredWindow_ms;
}

uint32_t fakeBspRtos_GetCriticalEnterCount(void) {
    return s_criticalEnterCount;
}

uint32_t fakeBspRtos_GetCriticalExitCount(void) {
    return s_criticalExitCount;
}

uint32_t fakeBspRtos_GetStaticTaskCreateCount(void) {
    return s_staticTaskCreateCount;
}

Milliseconds_t fakeBspRtos_GetLastDelayMs(void) {
    return s_lastDelay_ms;
}

Status_e bspWatchdog_Init(Milliseconds_t window_ms) {
    if ((window_ms.ms < BSP_WATCHDOG_MIN_TIMEOUT_MS) ||
        (window_ms.ms > BSP_WATCHDOG_MAX_TIMEOUT_MS)) {
        return STATUS_ERR_INVALID_PARAM;
    }
    s_configuredWindow_ms = window_ms;
    s_isWdtInitialized = true;
    return STATUS_OK;
}

Status_e bspWatchdog_Kick(void) {
    if (!s_isWdtInitialized) {
        return STATUS_ERR_UNINITIALIZED;
    }
    s_kickCount++;
    return STATUS_OK;
}

Status_e bspWatchdog_LatchFaultTask(uint8_t faultedTaskId) {
    s_latchedFaultTask = faultedTaskId;
    return STATUS_OK;
}

uint32_t bspRtos_EnterCritical(void) {
    s_criticalEnterCount++;
    return s_criticalEnterCount;
}

void bspRtos_ExitCritical(uint32_t savedIrqState) {
    (void)savedIrqState;
    s_criticalExitCount++;
}

Status_e bspRtos_DelayMs(Milliseconds_t delay_ms) {
    if ((delay_ms.ms == 0U) || (delay_ms.ms > BSP_RTOS_MAX_DELAY_MS)) {
        return STATUS_ERR_INVALID_PARAM;
    }
    s_lastDelay_ms = delay_ms;
    return STATUS_OK;
}

Status_e bspRtos_TaskCreateStatic(BspRtosTaskEntry_t entryFn, const char *const taskName,
                                  uint8_t priority, BspRtosStackWord_t *const stackBuf,
                                  size_t stackWords, BspRtosStaticTcb_t *const tcbBuf) {
    (void)priority;
    if ((entryFn == NULL) || (taskName == NULL) || (stackBuf == NULL) || (tcbBuf == NULL)) {
        return STATUS_ERR_NULL_PTR;
    }
    if (stackWords == 0U) {
        return STATUS_ERR_INVALID_PARAM;
    }
    s_staticTaskCreateCount++;
    return STATUS_OK;
}

//-------------------------------------------------------------------------------------------------//
/**
 * @file        fake_bspWatchdog.h
 * @brief       Link-time test double control API for bspWatchdog and bspRtos
 */
//-------------------------------------------------------------------------------------------------//
#ifndef FAKE_BSP_WATCHDOG_H_
#define FAKE_BSP_WATCHDOG_H_

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "bspRtos.h"
#include "bspWatchdog.h"

//-------------------------------------------------------------------------------------------------//
//             Exported Macros
//-------------------------------------------------------------------------------------------------//
#define FAKE_WDT_NO_FAULT_TASK (0xFFU)

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
void fakeBspWatchdog_Reset(void);
uint32_t fakeBspWatchdog_GetKickCount(void);
uint8_t fakeBspWatchdog_GetLatchedFaultTask(void);
Milliseconds_t fakeBspWatchdog_GetConfiguredWindowMs(void);
uint32_t fakeBspRtos_GetCriticalEnterCount(void);
uint32_t fakeBspRtos_GetCriticalExitCount(void);
uint32_t fakeBspRtos_GetStaticTaskCreateCount(void);
Milliseconds_t fakeBspRtos_GetLastDelayMs(void);

#endif /* FAKE_BSP_WATCHDOG_H_ */

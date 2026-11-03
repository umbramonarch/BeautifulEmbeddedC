//-------------------------------------------------------------------------------------------------//
/**
 * @file        bspWatchdog.h
 * @brief       Board Support Package interface for hardware watchdog timer and fault latching
 */
//-------------------------------------------------------------------------------------------------//
#ifndef BSP_WATCHDOG_H_
#define BSP_WATCHDOG_H_

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

//-------------------------------------------------------------------------------------------------//
//             Exported Macros
//-------------------------------------------------------------------------------------------------//
#define BSP_WATCHDOG_MIN_TIMEOUT_MS (10U)
#define BSP_WATCHDOG_MAX_TIMEOUT_MS (5000U)

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
/**
 * @brief       Initialize hardware watchdog timer with the specified window in milliseconds
 * @param[in]   window_ms  Watchdog timeout window (BSP_WATCHDOG_MIN_TIMEOUT_MS..BSP_WATCHDOG_MAX_TIMEOUT_MS)
 * @return      STATUS_OK on success, STATUS_ERR_INVALID_PARAM if window_ms is out of range
 */
MUST_CHECK Status_e bspWatchdog_Init(Milliseconds_t window_ms);

/**
 * @brief       Service (kick/reload) the hardware watchdog counter
 * @return      STATUS_OK on success, STATUS_ERR_UNINITIALIZED if not initialized
 */
MUST_CHECK Status_e bspWatchdog_Kick(void);

/**
 * @brief       Record the ID of a starved task in backup register before watchdog reset
 * @param[in]   faultedTaskId  Zero-based task index that missed its heartbeat window
 * @return      STATUS_OK on success
 */
MUST_CHECK Status_e bspWatchdog_LatchFaultTask(uint8_t faultedTaskId);

#endif /* BSP_WATCHDOG_H_ */

//-------------------------------------------------------------------------------------------------//
/**
 * @file        bspRtos.h
 * @brief       Vendor-free RTOS abstraction seam for static tasks, bounded delays, and critical sections
 */
//-------------------------------------------------------------------------------------------------//
#ifndef BSP_RTOS_H_
#define BSP_RTOS_H_

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
#define BSP_RTOS_MAX_DELAY_MS (10000U)

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//
typedef uint32_t BspRtosStackWord_t;

typedef struct {
    uint32_t reservedWords[16];
} BspRtosStaticTcb_t;

typedef void (*BspRtosTaskEntry_t)(void *pvParameters);

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
/**
 * @brief       Save interrupt mask and enter a critical section ([BARR-ISR-ATOMIC])
 * @return      Saved interrupt status word to pass to bspRtos_ExitCritical
 */
uint32_t bspRtos_EnterCritical(void);

/**
 * @brief       Restore previously saved interrupt status word ([BARR-ISR-ATOMIC])
 * @param[in]   savedIrqState  Token returned by bspRtos_EnterCritical
 */
void bspRtos_ExitCritical(uint32_t savedIrqState);

/**
 * @brief       Block calling RTOS task for a bounded duration in milliseconds ([RTOS-WDT-01])
 * @param[in]   delay_ms  Finite delay in milliseconds (1..BSP_RTOS_MAX_DELAY_MS)
 * @return      STATUS_OK on completion, STATUS_ERR_INVALID_PARAM if delay_ms is 0 or out of bounds
 */
MUST_CHECK Status_e bspRtos_DelayMs(Milliseconds_t delay_ms);

/**
 * @brief       Create an RTOS task using pre-allocated static stack and TCB buffers ([RTOS-STATIC-01])
 * @param[in]   entryFn     Task entry function (`void vTask(void *pvParameters)`)
 * @param[in]   taskName    Null-terminated ASCII task name
 * @param[in]   priority    Static task priority
 * @param[in]   stackBuf    Caller-allocated static stack array
 * @param[in]   stackWords  Number of BspRtosStackWord_t elements in stackBuf (> 0)
 * @param[in]   tcbBuf      Caller-allocated static TCB storage
 * @return      STATUS_OK on success, STATUS_ERR_NULL_PTR or STATUS_ERR_INVALID_PARAM on error
 */
MUST_CHECK Status_e bspRtos_TaskCreateStatic(BspRtosTaskEntry_t entryFn, const char *const taskName,
                                             uint8_t priority, BspRtosStackWord_t *const stackBuf,
                                             size_t stackWords, BspRtosStaticTcb_t *const tcbBuf);

#endif /* BSP_RTOS_H_ */

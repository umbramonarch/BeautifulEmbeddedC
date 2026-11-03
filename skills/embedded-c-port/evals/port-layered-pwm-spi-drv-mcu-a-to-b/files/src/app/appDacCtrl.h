//-------------------------------------------------------------------------------------------------//
/**
 * @file        appDacCtrl.h
 * @brief       Application control policy for the 12-bit precision analog reference DAC
 */
//-------------------------------------------------------------------------------------------------//
#ifndef APP_DAC_CTRL_H_
#define APP_DAC_CTRL_H_

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
#define APP_DAC_CTRL_VREF_MV      (3300)
#define APP_DAC_CTRL_MAX_CODE     (4095U)
#define APP_DAC_CTRL_CMD_ACTIVE   (0x3000U) /* Write DAC register, gain 1x, active mode */
#define APP_DAC_CTRL_CMD_SHUTDOWN (0x0000U) /* Power-down high-Z mode */

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
 * @brief Initialize the DAC control application and underlying board SPI interface.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e appDacCtrl_Init(void);

/**
 * @brief Command the analog reference output voltage in millivolts (0..3300 mV).
 * @param target_mv Desired output voltage in millivolts (0 <= mv <= 3300).
 * @return STATUS_OK on success, STATUS_ERR_INVALID_PARAM or hardware error otherwise.
 */
MUST_CHECK Status_e appDacCtrl_SetOutputMv(Millivolts_t target_mv);

/**
 * @brief Place the external DAC into low-power high-impedance shutdown mode.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e appDacCtrl_Shutdown(void);

/**
 * @brief Return the last successfully commanded output voltage in millivolts.
 * @param outLast_mv Pointer to receive the last commanded voltage.
 * @return STATUS_OK on success, STATUS_ERR_NULL_PTR or STATUS_ERR_UNINITIALIZED otherwise.
 */
MUST_CHECK Status_e appDacCtrl_GetLastOutputMv(Millivolts_t * const outLast_mv);

#endif /* APP_DAC_CTRL_H_ */

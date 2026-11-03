//-------------------------------------------------------------------------------------------------//
/**
 * @file        appDacCtrl.c
 * @brief       Application control implementation for the 12-bit precision analog reference DAC
 */
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include "appDacCtrl.h"
#include "bspSpi.h"

//-------------------------------------------------------------------------------------------------//
//             Private Macros
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Private Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Private Variables
//-------------------------------------------------------------------------------------------------//
static Millivolts_t s_lastCommanded_mv = { .mv = 0 };
static bool s_isInitialized = false;

//-------------------------------------------------------------------------------------------------//
//             Private Prototypes
//-------------------------------------------------------------------------------------------------//
static uint16_t MillivoltsToDacCode(Millivolts_t target_mv);

//-------------------------------------------------------------------------------------------------//
//             Implementation
//-------------------------------------------------------------------------------------------------//
Status_e appDacCtrl_Init(void) {
    Status_e const status = bspSpi_Init();
    if (status != STATUS_OK) {
        return status;
    }
    s_lastCommanded_mv.mv = 0;
    s_isInitialized = true;
    return STATUS_OK;
}

Status_e appDacCtrl_SetOutputMv(Millivolts_t target_mv) {
    if (!s_isInitialized) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if ((target_mv.mv < 0) || (target_mv.mv > APP_DAC_CTRL_VREF_MV)) {
        return STATUS_ERR_INVALID_PARAM;
    }

    uint16_t const code12 = MillivoltsToDacCode(target_mv);
    uint16_t const frameWord = (uint16_t)(APP_DAC_CTRL_CMD_ACTIVE | (code12 & 0x0FFFU));
    Status_e const status = bspSpi_DacTransferFrame(frameWord, NULL);
    if (status == STATUS_OK) {
        s_lastCommanded_mv = target_mv;
    }
    return status;
}

Status_e appDacCtrl_Shutdown(void) {
    if (!s_isInitialized) {
        return STATUS_ERR_UNINITIALIZED;
    }
    Status_e const status = bspSpi_DacTransferFrame(APP_DAC_CTRL_CMD_SHUTDOWN, NULL);
    if (status == STATUS_OK) {
        s_lastCommanded_mv.mv = 0;
    }
    return status;
}

Status_e appDacCtrl_GetLastOutputMv(Millivolts_t * const outLast_mv) {
    if (!s_isInitialized) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if (outLast_mv == NULL) {
        return STATUS_ERR_NULL_PTR;
    }
    *outLast_mv = s_lastCommanded_mv;
    return STATUS_OK;
}

static uint16_t MillivoltsToDacCode(Millivolts_t target_mv) {
    uint32_t const clamped_mv = (uint32_t)target_mv.mv;
    uint32_t const scaled =
        (clamped_mv * APP_DAC_CTRL_MAX_CODE + ((uint32_t)APP_DAC_CTRL_VREF_MV / 2U)) /
        (uint32_t)APP_DAC_CTRL_VREF_MV;
    return (uint16_t)scaled;
}

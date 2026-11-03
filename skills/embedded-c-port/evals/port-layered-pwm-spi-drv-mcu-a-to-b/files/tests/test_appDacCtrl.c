#include <assert.h>
#include "appDacCtrl.h"
#include "fake_drvSpi.h"

int main(void) {
    Millivolts_t last_mv = { .mv = -1 };

    fakeDrvSpi_Reset();
    assert(appDacCtrl_SetOutputMv((Millivolts_t){ .mv = 1650 }) == STATUS_ERR_UNINITIALIZED);
    assert(appDacCtrl_Init() == STATUS_OK);

    /* Reject out-of-range millivolt requests */
    assert(appDacCtrl_SetOutputMv((Millivolts_t){ .mv = -10 }) == STATUS_ERR_INVALID_PARAM);
    assert(appDacCtrl_SetOutputMv((Millivolts_t){ .mv = 3301 }) == STATUS_ERR_INVALID_PARAM);
    assert(fakeDrvSpi_GetTransferCallCount() == 0U);

    /* Mid-scale 1650 mV -> code ~2048 -> frame 0x3800 */
    assert(appDacCtrl_SetOutputMv((Millivolts_t){ .mv = 1650 }) == STATUS_OK);
    assert(fakeDrvSpi_GetTransferCallCount() == 1U);
    assert(fakeDrvSpi_GetLastTxWord(0U) == 0x3800U);
    assert(appDacCtrl_GetLastOutputMv(&last_mv) == STATUS_OK);
    assert(last_mv.mv == 1650);

    /* Full-scale 3300 mV -> code 4095 -> frame 0x3FFF */
    assert(appDacCtrl_SetOutputMv((Millivolts_t){ .mv = 3300 }) == STATUS_OK);
    assert(fakeDrvSpi_GetLastTxWord(0U) == 0x3FFFU);

    /* Shutdown frame 0x0000 resets output to 0 mV */
    assert(appDacCtrl_Shutdown() == STATUS_OK);
    assert(fakeDrvSpi_GetLastTxWord(0U) == 0x0000U);
    assert(appDacCtrl_GetLastOutputMv(&last_mv) == STATUS_OK);
    assert(last_mv.mv == 0);

    return 0;
}

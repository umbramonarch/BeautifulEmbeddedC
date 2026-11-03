#include "fake_drvSpi.h"

#define FAKE_DRV_SPI_MAX_CHANNELS (8U)

static const DrvSpiConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static bool s_isInitialized = false;
static uint16_t s_lastTxWord[FAKE_DRV_SPI_MAX_CHANNELS];
static uint16_t s_nextRxWord = 0U;
static uint32_t s_transferCalls = 0U;
static Status_e s_injectedStatus = STATUS_OK;

void fakeDrvSpi_Reset(void) {
    s_configTable = NULL;
    s_numChannels = 0U;
    s_isInitialized = false;
    s_nextRxWord = 0U;
    s_transferCalls = 0U;
    s_injectedStatus = STATUS_OK;
    for (size_t i = 0U; i < FAKE_DRV_SPI_MAX_CHANNELS; ++i) {
        s_lastTxWord[i] = 0U;
    }
}

void fakeDrvSpi_InjectStatus(Status_e status) {
    s_injectedStatus = status;
}

void fakeDrvSpi_SetNextRxWord(uint16_t rxWord) {
    s_nextRxWord = rxWord;
}

uint16_t fakeDrvSpi_GetLastTxWord(size_t channel) {
    if (channel < FAKE_DRV_SPI_MAX_CHANNELS) {
        return s_lastTxWord[channel];
    }
    return 0U;
}

uint32_t fakeDrvSpi_GetTransferCallCount(void) {
    return s_transferCalls;
}

Status_e drvSpi_Init(const DrvSpiConfig_t * const configTable,
                     size_t numChannels) {
    if (s_injectedStatus != STATUS_OK) {
        return s_injectedStatus;
    }
    if ((configTable == NULL) || (numChannels == 0U) ||
        (numChannels > FAKE_DRV_SPI_MAX_CHANNELS)) {
        return STATUS_ERR_NULL_PTR;
    }
    for (size_t i = 0U; i < numChannels; ++i) {
        if (configTable[i].maxClock_hz.hz == 0U) {
            return STATUS_ERR_INVALID_PARAM;
        }
    }
    s_configTable = configTable;
    s_numChannels = numChannels;
    s_isInitialized = true;
    return STATUS_OK;
}

Status_e drvSpi_TransferWord(size_t channel,
                             uint16_t txWord,
                             uint16_t * const outRxWord) {
    if (s_injectedStatus != STATUS_OK) {
        return s_injectedStatus;
    }
    if (!s_isInitialized || (s_configTable == NULL)) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if (outRxWord == NULL) {
        return STATUS_ERR_NULL_PTR;
    }
    if (channel >= s_numChannels) {
        return STATUS_ERR_INVALID_CHANNEL;
    }
    s_lastTxWord[channel] = txWord;
    *outRxWord = s_nextRxWord;
    s_transferCalls++;
    return STATUS_OK;
}

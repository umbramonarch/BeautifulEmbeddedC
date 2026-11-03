//-------------------------------------------------------------------------------------------------//
/**
 * @file        drvSpi.c
 * @brief       Synchronous 16-bit SPI peripheral driver targeting MCU-A (vendor_mcu_a_spi.h)
 */
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include "drvSpi.h"
#include "vendor_mcu_a_spi.h"

//-------------------------------------------------------------------------------------------------//
//             Private Macros
//-------------------------------------------------------------------------------------------------//
#define DRV_SPI_MAX_POLL_CYCLES (10000U)
#define DRV_SPI_MAX_PIN_NUMBER  (15U)

//-------------------------------------------------------------------------------------------------//
//             Private Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Private Variables
//-------------------------------------------------------------------------------------------------//
static const DrvSpiConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static bool s_isInitialized = false;

//-------------------------------------------------------------------------------------------------//
//             Private Prototypes
//-------------------------------------------------------------------------------------------------//
static uint32_t ComputeBaudDividerBits(FreqHz_t maxClock_hz);
static void SetChipSelect(const DrvSpiConfig_t * const cfg, bool isAsserted);
static Status_e PollStatusMask(const volatile uint32_t * const srReg,
                               uint32_t mask,
                               bool waitUntilSet);

//-------------------------------------------------------------------------------------------------//
//             Implementation
//-------------------------------------------------------------------------------------------------//
Status_e drvSpi_Init(const DrvSpiConfig_t * const configTable,
                     size_t numChannels) {
    if ((configTable == NULL) || (numChannels == 0U)) {
        return STATUS_ERR_NULL_PTR;
    }

    for (size_t i = 0U; i < numChannels; ++i) {
        const DrvSpiConfig_t * const cfg = &configTable[i];
        if ((cfg->hwInstanceId >= MCU_A_SPI_INSTANCE_COUNT) ||
            (cfg->csPortId >= MCU_A_GPIO_PORT_COUNT) ||
            (cfg->csPin > DRV_SPI_MAX_PIN_NUMBER) ||
            (cfg->maxClock_hz.hz == 0U)) {
            return STATUS_ERR_INVALID_PARAM;
        }

        MCU_A_SPI_TypeDef * const spi = &MCU_A_SPI_Instances[cfg->hwInstanceId];
        MCU_A_GPIO_TypeDef * const gpio = &MCU_A_GPIO_Ports[cfg->csPortId];

        gpio->DIR |= (UINT32_C(1) << cfg->csPin);
        SetChipSelect(cfg, false);

        uint32_t const brBits = ComputeBaudDividerBits(cfg->maxClock_hz);
        uint32_t const modeBits = ((uint32_t)cfg->clockMode & UINT32_C(0x3)) << MCU_A_SPI_CTRL_MODE_POS;
        spi->CTRL = MCU_A_SPI_CTRL_EN_MASK | MCU_A_SPI_CTRL_MASTER_MASK | modeBits |
                    (brBits << MCU_A_SPI_CTRL_BR_POS);
        spi->SR &= ~MCU_A_SPI_SR_OVR_MASK;
    }

    s_configTable = configTable;
    s_numChannels = numChannels;
    s_isInitialized = true;
    return STATUS_OK;
}

Status_e drvSpi_TransferWord(size_t channel,
                             uint16_t txWord,
                             uint16_t * const outRxWord) {
    if (!s_isInitialized || (s_configTable == NULL)) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if (outRxWord == NULL) {
        return STATUS_ERR_NULL_PTR;
    }
    if (channel >= s_numChannels) {
        return STATUS_ERR_INVALID_CHANNEL;
    }

    const DrvSpiConfig_t * const cfg = &s_configTable[channel];
    MCU_A_SPI_TypeDef * const spi = &MCU_A_SPI_Instances[cfg->hwInstanceId];

    SetChipSelect(cfg, true);

    Status_e status = PollStatusMask(&spi->SR, MCU_A_SPI_SR_TXE_MASK, true);
    if (status == STATUS_OK) {
        spi->DR16 = txWord;
        status = PollStatusMask(&spi->SR, MCU_A_SPI_SR_RXNE_MASK, true);
    }
    if (status == STATUS_OK) {
        *outRxWord = spi->DR16;
        status = PollStatusMask(&spi->SR, MCU_A_SPI_SR_BSY_MASK, false);
    }

    SetChipSelect(cfg, false);
    return status;
}

static uint32_t ComputeBaudDividerBits(FreqHz_t maxClock_hz) {
    for (uint32_t div = 0U; div < 7U; ++div) {
        uint32_t const divisor = UINT32_C(2) << div;
        if ((MCU_A_SPI_PCLK_HZ / divisor) <= maxClock_hz.hz) {
            return div;
        }
    }
    return 7U;
}

static void SetChipSelect(const DrvSpiConfig_t * const cfg, bool isAsserted) {
    MCU_A_GPIO_TypeDef * const gpio = &MCU_A_GPIO_Ports[cfg->csPortId];
    bool const driveHigh = cfg->isCsActiveLow ? (!isAsserted) : isAsserted;
    uint32_t const mask = (UINT32_C(1) << cfg->csPin);
    if (driveHigh) {
        gpio->OUT |= mask;
    } else {
        gpio->OUT &= ~mask;
    }
}

static Status_e PollStatusMask(const volatile uint32_t * const srReg,
                               uint32_t mask,
                               bool waitUntilSet) {
    for (uint32_t cycle = 0U; cycle < DRV_SPI_MAX_POLL_CYCLES; ++cycle) {
        bool const isSet = ((*srReg & mask) != 0U);
        if (isSet == waitUntilSet) {
            return STATUS_OK;
        }
    }
    return STATUS_ERR_TIMEOUT;
}

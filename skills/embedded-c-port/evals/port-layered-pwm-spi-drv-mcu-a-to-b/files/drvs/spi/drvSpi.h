//-------------------------------------------------------------------------------------------------//
/**
 * @file        drvSpi.h
 * @brief       Vendor-free synchronous 16-bit frame SPI peripheral driver interface
 */
//-------------------------------------------------------------------------------------------------//
#ifndef DRV_SPI_H_
#define DRV_SPI_H_

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

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//
typedef enum {
    DRV_SPI_MODE_0 = 0,
    DRV_SPI_MODE_1,
    DRV_SPI_MODE_2,
    DRV_SPI_MODE_3
} DrvSpiMode_e;

typedef struct {
    uint32_t hwInstanceId;
    FreqHz_t maxClock_hz;
    DrvSpiMode_e clockMode;
    uint32_t csPortId;
    uint8_t csPin;
    bool isCsActiveLow;
} DrvSpiConfig_t;

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
/**
 * @brief Initialize SPI channels from a const configuration table in .rodata Flash.
 * @param configTable Pointer to const DrvSpiConfig_t array.
 * @param numChannels Number of logical SPI channels in configTable.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e drvSpi_Init(const DrvSpiConfig_t * const configTable,
                                size_t numChannels);

/**
 * @brief Transmit and receive a 16-bit MSB-first SPI frame on a logical channel.
 * @param channel Logical SPI channel index (< numChannels).
 * @param txWord 16-bit frame word to transmit MSB-first.
 * @param outRxWord Pointer to store the received 16-bit word.
 * @return STATUS_OK on success, STATUS_ERR_TIMEOUT or parameter error otherwise.
 */
MUST_CHECK Status_e drvSpi_TransferWord(size_t channel,
                                        uint16_t txWord,
                                        uint16_t * const outRxWord);

#endif /* DRV_SPI_H_ */

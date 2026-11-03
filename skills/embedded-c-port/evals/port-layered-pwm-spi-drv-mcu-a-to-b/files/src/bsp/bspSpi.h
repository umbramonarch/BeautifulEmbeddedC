//-------------------------------------------------------------------------------------------------//
/**
 * @file        bspSpi.h
 * @brief       Board-meaningful hardware abstraction for the external precision SPI DAC
 */
//-------------------------------------------------------------------------------------------------//
#ifndef BSP_SPI_H_
#define BSP_SPI_H_

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

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//
/**
 * @brief Initialize board SPI buses using kBspSpiConfigTable.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e bspSpi_Init(void);

/**
 * @brief Write a 16-bit command/data frame to the board's precision analog DAC.
 * @param dacFrameWord 16-bit DAC frame word (4-bit command header + 12-bit DAC code).
 * @param outLoopbackWord Optional pointer to receive the 16-bit MISO loopback word (or NULL).
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e bspSpi_DacTransferFrame(uint16_t dacFrameWord,
                                            uint16_t * const outLoopbackWord);

#endif /* BSP_SPI_H_ */

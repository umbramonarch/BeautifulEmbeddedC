#ifndef FAKE_DRV_SPI_H_
#define FAKE_DRV_SPI_H_

#include "drvSpi.h"

void fakeDrvSpi_Reset(void);
void fakeDrvSpi_InjectStatus(Status_e status);
void fakeDrvSpi_SetNextRxWord(uint16_t rxWord);
uint16_t fakeDrvSpi_GetLastTxWord(size_t channel);
uint32_t fakeDrvSpi_GetTransferCallCount(void);

#endif /* FAKE_DRV_SPI_H_ */

# RTOS Tasks, Synchronization, Watchdogs & ISR Frameworks (digest)

Source: Synthesized from FreeRTOS / SafeRTOS / Zephyr RTOS safety profiles, NASA JPL Power of
10 (`[JPL-2]`, `[JPL-3]`), BARR-C:2018 (`[BARR-6.5]`, `[BARR-ISR-ATOMIC]`), Jacob Beningo's
HAL/BSP architecture, and James Grenning's Humble Object pattern.
Read this when writing or reviewing RTOS tasks, queues, mutexes, semaphores, ISR-to-task
notifications, watchdog supervisor tasks, or CMSIS/vendor interrupt vector handlers.

## 1. Framework Conventions to Leave Alone

Embedded frameworks and MCU startup vector tables mandate specific function signatures and
task loops. **Never flag or "fix" these framework-mandated idioms as rule violations:**

- **RTOS task entry signatures (`void vTask(void *pvParameters)`):** FreeRTOS (`TaskFunction_t`),
  Zephyr (`k_thread_entry_t`), and ThreadX mandate `void *` parameters and `void` return types.
  Silence unused context parameters at the top of the function with `(void)pvParameters;`.
- **Intentional task superloops (`for (;;)`):** An RTOS task body is an intentional infinite
  loop that yields the CPU on every iteration via a bounded OS blocking call
  (`xQueueReceive(..., pdMS_TO_TICKS(50U))`, `vTaskDelayUntil()`). This is **not** an unbounded
  hardware register polling loop (`[JPL-2]`), provided every iteration blocks on an OS primitive
  with a finite tick timeout.
- **Linker-mandated interrupt vector names (`void USART2_IRQHandler(void)`):** Startup `.s`
  vector tables bind weak symbols by exact name (`TIM1_UP_IRQHandler`, `USART2_IRQHandler`,
  `SysTick_Handler`, `DMA1_Channel1_IRQHandler`). These handlers **must have external linkage**
  (never mark them `static`, which hides them from the linker and leaves `Default_Handler`
  active) and **must keep their exact vector symbol name**. Keep the vector body minimal and
  delegate to a driver ISR helper.
- **Vendor HAL/DMA callbacks (`HAL_UART_RxCpltCallback`):** Weak callback hooks required by a
  vendor SDK are legal **only inside `drvs/<periph>/drv*.c`**, never in `src/bsp/` or `src/app/`.

## 2. Static RTOS Object Allocation (`[RTOS-STATIC-01]`)

- **`[RTOS-STATIC-01]` (Use static RTOS allocation APIs exclusively):** Dynamic RTOS creation
  APIs (`xTaskCreate`, `xQueueCreate`, `xSemaphoreCreateMutex`, `xSemaphoreCreateBinary`,
  `xTimerCreate`) allocate kernel objects and task stacks from the RTOS heap (`pvPortMalloc`),
  violating `[JPL-3]` and `[MISRA-21.3]`. Configure `configSUPPORT_STATIC_ALLOCATION = 1` and
  `configSUPPORT_DYNAMIC_ALLOCATION = 0`, and allocate all TCBs, stacks, queues, and mutexes in
  fixed `static` storage (`xTaskCreateStatic`, `xQueueCreateStatic`,
  `xSemaphoreCreateMutexStatic`, or Zephyr `K_THREAD_DEFINE` / `K_MSGQ_DEFINE`):

```c
#include <stddef.h>
#include <stdint.h>

/* Minimal vendor-neutral RTOS static allocation types for illustration */
typedef uint32_t StackType_t;
typedef struct { uint32_t opaque[8]; } StaticTask_t;
typedef struct { uint32_t opaque[6]; } StaticQueue_t;
typedef void *TaskHandle_t;
typedef void *QueueHandle_t;
typedef struct { uint16_t id; int32_t payload_mv; } CommsMsg_t;

#define COMMS_STACK_WORDS (256U)
#define COMMS_QUEUE_LEN   (8U)

extern QueueHandle_t xQueueCreateStatic(uint32_t len, uint32_t itemSize,
                                        uint8_t *storage, StaticQueue_t *qBuf);
extern TaskHandle_t xTaskCreateStatic(void (*fn)(void *), const char *name, uint32_t depth,
                                      void *param, uint32_t prio, StackType_t *stack,
                                      StaticTask_t *tcb);
extern void vCommsTask(void *pvParameters);

/* BAD: xTaskCreate(...) and xQueueCreate(...) allocate from heap ([RTOS-STATIC-01]) */

/* GOOD: Static storage in BSS paired with xQueueCreateStatic / xTaskCreateStatic */
static StackType_t   s_commsStack[COMMS_STACK_WORDS];
static StaticTask_t  s_commsTcb;
static uint8_t       s_commsQueueStorage[COMMS_QUEUE_LEN * sizeof(CommsMsg_t)];
static StaticQueue_t s_commsQueueStruct;

_Static_assert(sizeof(s_commsQueueStorage) == (COMMS_QUEUE_LEN * sizeof(CommsMsg_t)),
               "Queue storage size must match element count * sizeof(CommsMsg_t)");

QueueHandle_t commsTask_InitStatic(TaskHandle_t * const outTask);
QueueHandle_t commsTask_InitStatic(TaskHandle_t * const outTask) {
    QueueHandle_t const q = xQueueCreateStatic(
        COMMS_QUEUE_LEN, (uint32_t)sizeof(CommsMsg_t), s_commsQueueStorage, &s_commsQueueStruct);
    *outTask = xTaskCreateStatic(
        vCommsTask, "Comms", COMMS_STACK_WORDS, (void *)0, 2U, s_commsStack, &s_commsTcb);
    return q;
}
```

## 3. ISR-Safe Primitives & Deferred Interrupt Processing (`[RTOS-ISR-01]`)

- **`[RTOS-ISR-01]` (Never call blocking or non-`FromISR` OS APIs inside an ISR):** Calling
  `xQueueSend()`, `xQueueReceive()`, `xSemaphoreTake()`, or `vTaskDelay()` from an Interrupt
  Service Routine corrupts scheduler ready lists or triggers a hard fault (`configASSERT`).
  Inside any `*_IRQHandler`, use only `FromISR` variants (`xQueueSendFromISR`,
  `vTaskNotifyGiveFromISR`, `xSemaphoreGiveFromISR`) with a `timeout` of zero, and pass
  `&xHigherPriorityTaskWoken` into `portYIELD_FROM_ISR()` at ISR exit:

```c
#include <stdbool.h>
#include <stdint.h>

typedef int32_t BaseType_t;
#define pdFALSE ((BaseType_t)0)
extern BaseType_t xQueueSendFromISR(void *q, const void *item, BaseType_t *pxWoken);
extern void portYIELD_FROM_ISR(BaseType_t xSwitchRequired);
extern volatile uint32_t VENDOR_USART2_SR;
extern volatile uint32_t VENDOR_USART2_DR;
#define USART_SR_RXNE_MASK (1U << 5U)

static void *s_rxByteQueue = (void *)0;

/* Linker-mandated vector name: must NOT be static */
void USART2_IRQHandler(void);
void USART2_IRQHandler(void) {
    BaseType_t higherPrioWoken = pdFALSE;
    if ((VENDOR_USART2_SR & USART_SR_RXNE_MASK) != 0U) {
        uint8_t const rxByte = (uint8_t)(VENDOR_USART2_DR & 0xFFU);
        /* Never call blocking xQueueSend() in an ISR ([RTOS-ISR-01]) */
        (void)xQueueSendFromISR(s_rxByteQueue, &rxByte, &higherPrioWoken);
    }
    portYIELD_FROM_ISR(higherPrioWoken);
}
```

## 4. Priority-Inheriting Mutexes vs. Binary Semaphores (`[RTOS-MUTEX-01]`)

- **`[RTOS-MUTEX-01]` (Protect shared resources with priority-inheriting mutexes, never binary
  semaphores):** When a low-priority task and a high-priority task share a hardware bus (SPI,
  I2C, RS-485) or shared state, locking with a **binary semaphore** (`xSemaphoreCreateBinary`)
  allows a medium-priority task to preempt the low-priority lock holder indefinitely, causing
  **unbounded priority inversion** (the Mars Pathfinder failure mode).
  - **Shared resource locking across tasks:** Always use a **mutex** with priority inheritance
    (`xSemaphoreCreateMutexStatic()` / `k_mutex`) and a finite acquisition timeout.
  - **ISR-to-task event signaling:** Never acquire or release a mutex inside an ISR (mutexes
    have task ownership and cannot be given from an interrupt). Use a direct task notification
    (`vTaskNotifyGiveFromISR`) or binary semaphore for one-way ISR signaling.

## 5. Bounded Blocking and Watchdog Liveness (`[RTOS-WDT-01]`)

- **`[RTOS-WDT-01]` (Never block indefinitely with `portMAX_DELAY` / `K_FOREVER` in
  watchdog-monitored tasks):** If a task waits on a queue or mutex with `portMAX_DELAY` and the
  upstream producer stalls, the task blocks forever and either starves its watchdog check-in or
  silently deadlocks if another task kicks the hardware watchdog blindly.
  1. **Bound every blocking OS call** to a fraction of the watchdog window (e.g.,
     `pdMS_TO_TICKS(50U)` inside a `200 ms` watchdog window). On timeout (`pdFALSE`), record a
     heartbeat or handle the idle window, then loop.
  2. **Rendezvous watchdog pattern:** Individual application tasks must never kick the hardware
     watchdog timer directly. Each monitored task sets its heartbeat bit via a supervisor API;
     a dedicated watchdog supervisor task verifies that **all** registered task bits are set
     within the window before kicking the hardware watchdog and clearing the bitmask.

## 6. OS-Agnostic State Machine Core (`[RTOS-SEAM-01]`)

- **`[RTOS-SEAM-01]` (Humble Task Wrapper — keep RTOS headers out of `src/app/*.h` and state
  machine logic):** Coupling application state transitions directly to `FreeRTOS.h`, `task.h`,
  and `queue.h` makes deterministic host `gcc` testing slow or impossible. Split every RTOS
  application module into two parts:
  1. **Pure OS-agnostic state machine (`app<Name>_Init()`, `app<Name>_Step()`):** Lives in
     `src/app/app<Name>.h/.c` (or calls a vendor-free `src/bsp/bspRtos.h` seam), takes plain C11
     structs and `Milliseconds_t`, and executes one deterministic step with zero OS dependencies.
  2. **Thin RTOS task wrapper (`v<Name>Task()`):** Waits on the bounded queue/notification,
     passes the event or timeout into `app<Name>_Step()`, and checks in with the watchdog.

```c
#include <stdbool.h>
#include <stdint.h>

typedef enum { STATUS_OK = 0, STATUS_ERR_TIMEOUT } Status_e;
typedef struct { uint32_t ms; } Milliseconds_t;
typedef struct { uint16_t cmdId; int32_t value_mv; } AppCommsFrame_t;

/* 1. Pure OS-agnostic step function — 100% host-testable without FreeRTOS */
Status_e appComms_Step(const AppCommsFrame_t * const frameOrNull,
                       Milliseconds_t elapsed_ms);

/* 2. Thin RTOS task wrapper in target glue */
extern bool bspRtos_QueueReceiveComms(AppCommsFrame_t *outFrame, Milliseconds_t timeout_ms);
extern void appWatchdog_ReportHeartbeat(uint8_t taskId);

void vCommsTask(void *pvParameters);
void vCommsTask(void *pvParameters) {
    (void)pvParameters;
    for (;;) {
        AppCommsFrame_t frame = { 0U, 0 };
        bool const hasFrame = bspRtos_QueueReceiveComms(&frame, (Milliseconds_t){ 50U });
        (void)appComms_Step(hasFrame ? &frame : (const AppCommsFrame_t *)0,
                            (Milliseconds_t){ 50U });
        appWatchdog_ReportHeartbeat(0U);
    }
}
```

## 7. Checklist

- [ ] Are all tasks, queues, and mutexes created with `*Static` APIs (`[RTOS-STATIC-01]`)?
- [ ] Do ISRs call only `*FromISR` APIs and yield via `portYIELD_FROM_ISR` (`[RTOS-ISR-01]`)?
- [ ] Are shared buses locked with priority-inheriting mutexes, not binary semaphores (`[RTOS-MUTEX-01]`)?
- [ ] Do all task waits use finite timeouts (`pdMS_TO_TICKS`), never `portMAX_DELAY` (`[RTOS-WDT-01]`)?
- [ ] Are `src/app/*.h` headers and `app*_Step()` functions 100% free of RTOS headers (`[RTOS-SEAM-01]`)?
- [ ] Do hardware vector handlers (`*_IRQHandler`) retain external linkage and exact symbol names?

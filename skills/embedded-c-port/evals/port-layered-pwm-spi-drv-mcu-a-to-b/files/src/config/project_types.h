//-------------------------------------------------------------------------------------------------//
/**
 * @file        project_types.h
 * @brief       Vendor-free shared status codes, compile-time macros, and physical unit types
 */
//-------------------------------------------------------------------------------------------------//
#ifndef PROJECT_TYPES_H_
#define PROJECT_TYPES_H_

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

//-------------------------------------------------------------------------------------------------//
//             Exported Macros
//-------------------------------------------------------------------------------------------------//
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 202311L)
#define MUST_CHECK [[nodiscard]]
#elif defined(__GNUC__) || defined(__clang__)
#define MUST_CHECK __attribute__((warn_unused_result))
#else
#define MUST_CHECK
#endif

#define ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//
typedef enum {
    STATUS_OK = 0,
    STATUS_ERR_NULL_PTR,
    STATUS_ERR_INVALID_CHANNEL,
    STATUS_ERR_INVALID_PARAM,
    STATUS_ERR_TIMEOUT,
    STATUS_ERR_UNINITIALIZED,
    STATUS_ERR_BUFFER_FULL,
    STATUS_ERR_BUFFER_EMPTY,
    STATUS_ERR_HW_FAULT
} Status_e;

/* Zero-cost single-field physical unit wrapper structs ([MISRA-UNIT-WRAP]) */
typedef struct {
    uint32_t hz;
} FreqHz_t;

typedef struct {
    uint16_t permille;
} DutyPermille_t;

typedef struct {
    int32_t mv;
} Millivolts_t;

typedef struct {
    int32_t ma;
} Milliamps_t;

typedef struct {
    uint32_t ms;
} Milliseconds_t;

typedef struct {
    uint32_t us;
} Microseconds_t;

_Static_assert(sizeof(FreqHz_t) == sizeof(uint32_t), "FreqHz_t must be 4 bytes");
_Static_assert(sizeof(DutyPermille_t) == sizeof(uint16_t), "DutyPermille_t must be 2 bytes");
_Static_assert(sizeof(Millivolts_t) == sizeof(int32_t), "Millivolts_t must be 4 bytes");
_Static_assert(sizeof(Milliamps_t) == sizeof(int32_t), "Milliamps_t must be 4 bytes");
_Static_assert(sizeof(Milliseconds_t) == sizeof(uint32_t), "Milliseconds_t must be 4 bytes");
_Static_assert(sizeof(Microseconds_t) == sizeof(uint32_t), "Microseconds_t must be 4 bytes");

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//

#endif /* PROJECT_TYPES_H_ */

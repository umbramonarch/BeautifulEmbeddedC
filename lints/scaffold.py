#!/usr/bin/env python3
"""BeautifulEmbeddedC Multi-Layer Project & Module Scaffolder (scaffold.py).

Scaffolds either a complete 4-layer (`app`, `bsp`, `config`, `drv`) + vertical `libs/`
Embedded C project structure, or individual compliant modules + host unit tests in any layer:

Usage:
  python3 lints/scaffold.py --init-project --root <dir>
  python3 lints/scaffold.py --layer app <name> --root <dir>
  python3 lints/scaffold.py --layer config <name> --root <dir>
  python3 lints/scaffold.py --layer bsp <name> --root <dir>
  python3 lints/scaffold.py --layer drv <name> --root <dir>
  python3 lints/scaffold.py --layer lib <name> --root <dir>
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys
from typing import Sequence

BANNER = (
    "//-------------------------------------------------------------------------------------------------//"
)


def to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_") if part)


def to_camel(name: str) -> str:
    pascal = to_pascal(name)
    return pascal[0].lower() + pascal[1:] if pascal else ""


def to_snake(name: str) -> str:
    return "_".join(part.lower() for part in name.replace("-", "_").split("_") if part)


def write_if_missing(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"[SKIP] {path} already exists")
        return
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[CREATE] {path}")


PROJECT_TYPES_H = f"""{BANNER}
/**
 * @file        project_types.h
 * @brief       Vendor-free shared status codes, compile-time macros, and physical unit types
 */
{BANNER}
#ifndef PROJECT_TYPES_H_
#define PROJECT_TYPES_H_

{BANNER}
//             Includes
{BANNER}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

{BANNER}
//             Exported Macros
{BANNER}
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 202311L)
#define MUST_CHECK [[nodiscard]]
#elif defined(__GNUC__) || defined(__clang__)
#define MUST_CHECK __attribute__((warn_unused_result))
#else
#define MUST_CHECK
#endif

#define ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

{BANNER}
//             Exported Types
{BANNER}
typedef enum {{
    STATUS_OK = 0,
    STATUS_ERR_NULL_PTR,
    STATUS_ERR_INVALID_CHANNEL,
    STATUS_ERR_INVALID_PARAM,
    STATUS_ERR_TIMEOUT,
    STATUS_ERR_UNINITIALIZED,
    STATUS_ERR_BUFFER_FULL,
    STATUS_ERR_BUFFER_EMPTY,
    STATUS_ERR_HW_FAULT
}} Status_e;

/* Zero-cost single-field physical unit wrapper structs ([MISRA-UNIT-WRAP]) */
typedef struct {{
    uint32_t hz;
}} FreqHz_t;

typedef struct {{
    uint16_t permille;
}} DutyPermille_t;

typedef struct {{
    int32_t mv;
}} Millivolts_t;

typedef struct {{
    int32_t ma;
}} Milliamps_t;

typedef struct {{
    uint32_t ms;
}} Milliseconds_t;

typedef struct {{
    uint32_t us;
}} Microseconds_t;

_Static_assert(sizeof(FreqHz_t) == sizeof(uint32_t), "FreqHz_t must be 4 bytes");
_Static_assert(sizeof(DutyPermille_t) == sizeof(uint16_t), "DutyPermille_t must be 2 bytes");
_Static_assert(sizeof(Millivolts_t) == sizeof(int32_t), "Millivolts_t must be 4 bytes");
_Static_assert(sizeof(Milliamps_t) == sizeof(int32_t), "Milliamps_t must be 4 bytes");
_Static_assert(sizeof(Milliseconds_t) == sizeof(uint32_t), "Milliseconds_t must be 4 bytes");
_Static_assert(sizeof(Microseconds_t) == sizeof(uint32_t), "Microseconds_t must be 4 bytes");

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}

#endif /* PROJECT_TYPES_H_ */
"""


def scaffold_init_project(root: pathlib.Path, lints_dir: pathlib.Path) -> None:
    for subdir in (
        "src/app",
        "src/config",
        "src/bsp",
        "src/bsp/config",
        "drvs",
        "libs",
        "tests",
        "lints",
    ):
        (root / subdir).mkdir(parents=True, exist_ok=True)

    write_if_missing(root / "src/config/project_types.h", PROJECT_TYPES_H)

    for cfg_name in (".clang-format", ".clang-tidy", ".clangd", "Makefile"):
        src_file = lints_dir / cfg_name
        dst_file = root / cfg_name
        if src_file.is_file() and not dst_file.exists():
            shutil.copyfile(src_file, dst_file)
            print(f"[CREATE] {dst_file}")

    for tool_name in ("check_arch.py", "scaffold.py"):
        src_tool = lints_dir / tool_name
        dst_tool = root / "lints" / tool_name
        if src_tool.is_file() and not dst_tool.exists():
            shutil.copyfile(src_tool, dst_tool)
            print(f"[CREATE] {dst_tool}")


def scaffold_config(root: pathlib.Path, name: str) -> None:
    snake = to_snake(name)
    pascal = to_pascal(name)
    upper = snake.upper()
    write_if_missing(root / "src/config/project_types.h", PROJECT_TYPES_H)

    hdr = f"""{BANNER}
/**
 * @file        {snake}Cfg.h
 * @brief       Product configuration constants for {pascal}
 */
{BANNER}
#ifndef {upper}_CFG_H_
#define {upper}_CFG_H_

{BANNER}
//             Includes
{BANNER}
#include <stdint.h>
#include "project_types.h"

{BANNER}
//             Exported Macros
{BANNER}
#define {upper}_DEFAULT_TIMEOUT_MS (100U)
#define {upper}_MAX_LIMIT_MV       (3300)

{BANNER}
//             Exported Types
{BANNER}

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}

#endif /* {upper}_CFG_H_ */
"""
    write_if_missing(root / f"src/config/{snake}Cfg.h", hdr)


def scaffold_app(root: pathlib.Path, name: str) -> None:
    pascal = to_pascal(name)
    upper = to_snake(name).upper()
    write_if_missing(root / "src/config/project_types.h", PROJECT_TYPES_H)

    app_h = f"""{BANNER}
/**
 * @file        app{pascal}.h
 * @brief       Application state machine and policy for {pascal}
 */
{BANNER}
#ifndef APP_{upper}_H_
#define APP_{upper}_H_

{BANNER}
//             Includes
{BANNER}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

{BANNER}
//             Exported Macros
{BANNER}

{BANNER}
//             Exported Types
{BANNER}
typedef struct {{
    Millivolts_t threshold_mv;
    DutyPermille_t activeDuty_permille;
}} App{pascal}Config_t;

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}
/**
 * @brief Initialize the {pascal} application module.
 * @param config Pointer to const configuration in .rodata.
 * @return STATUS_OK on success, STATUS_ERR_NULL_PTR or STATUS_ERR_INVALID_PARAM on error.
 */
MUST_CHECK Status_e app{pascal}_Init(const App{pascal}Config_t * const config);

/**
 * @brief Execute one deterministic step of the {pascal} state machine.
 * @param input_mv Measured input in millivolts.
 * @param outDuty_permille Output commanded duty cycle (0..1000 permille).
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e app{pascal}_Step(Millivolts_t input_mv,
                                     DutyPermille_t * const outDuty_permille);

#endif /* APP_{upper}_H_ */
"""

    app_c = f"""{BANNER}
/**
 * @file        app{pascal}.c
 * @brief       Application state machine implementation for {pascal}
 */
{BANNER}

{BANNER}
//             Includes
{BANNER}
#include "app{pascal}.h"

{BANNER}
//             Private Macros
{BANNER}
#define APP_{upper}_MAX_DUTY_PERMILLE (1000U)

{BANNER}
//             Private Types
{BANNER}

{BANNER}
//             Private Variables
{BANNER}
static const App{pascal}Config_t *s_config = NULL;
static bool s_isInitialized = false;

{BANNER}
//             Private Prototypes
{BANNER}

{BANNER}
//             Implementation
{BANNER}
Status_e app{pascal}_Init(const App{pascal}Config_t * const config) {{
    if (config == NULL) {{
        return STATUS_ERR_NULL_PTR;
    }}
    if (config->activeDuty_permille.permille > APP_{upper}_MAX_DUTY_PERMILLE) {{
        return STATUS_ERR_INVALID_PARAM;
    }}
    s_config = config;
    s_isInitialized = true;
    return STATUS_OK;
}}

Status_e app{pascal}_Step(Millivolts_t input_mv,
                          DutyPermille_t * const outDuty_permille) {{
    if (!s_isInitialized || (s_config == NULL)) {{
        return STATUS_ERR_UNINITIALIZED;
    }}
    if (outDuty_permille == NULL) {{
        return STATUS_ERR_NULL_PTR;
    }}
    if (input_mv.mv >= s_config->threshold_mv.mv) {{
        *outDuty_permille = s_config->activeDuty_permille;
    }} else {{
        outDuty_permille->permille = 0U;
    }}
    return STATUS_OK;
}}
"""

    test_c = f"""#include <assert.h>
#include "app{pascal}.h"

static const App{pascal}Config_t kTestConfig = {{
    .threshold_mv        = {{ .mv = 2500 }},
    .activeDuty_permille = {{ .permille = 800U }}
}};

int main(void) {{
    DutyPermille_t duty = {{ .permille = 0U }};

    assert(app{pascal}_Init(NULL) == STATUS_ERR_NULL_PTR);
    assert(app{pascal}_Step((Millivolts_t){{ .mv = 1000 }}, &duty) == STATUS_ERR_UNINITIALIZED);
    assert(app{pascal}_Init(&kTestConfig) == STATUS_OK);
    assert(app{pascal}_Step((Millivolts_t){{ .mv = 1000 }}, NULL) == STATUS_ERR_NULL_PTR);

    assert(app{pascal}_Step((Millivolts_t){{ .mv = 2000 }}, &duty) == STATUS_OK);
    assert(duty.permille == 0U);

    assert(app{pascal}_Step((Millivolts_t){{ .mv = 2600 }}, &duty) == STATUS_OK);
    assert(duty.permille == 800U);
    return 0;
}}
"""
    write_if_missing(root / f"src/app/app{pascal}.h", app_h)
    write_if_missing(root / f"src/app/app{pascal}.c", app_c)
    write_if_missing(root / f"tests/test_app{pascal}.c", test_c)


def scaffold_drv(root: pathlib.Path, name: str) -> None:
    snake = to_snake(name)
    pascal = to_pascal(name)
    upper = snake.upper()
    write_if_missing(root / "src/config/project_types.h", PROJECT_TYPES_H)

    drv_h = f"""{BANNER}
/**
 * @file        drv{pascal}.h
 * @brief       Vendor-free peripheral driver interface for {pascal}
 */
{BANNER}
#ifndef DRV_{upper}_H_
#define DRV_{upper}_H_

{BANNER}
//             Includes
{BANNER}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

{BANNER}
//             Exported Macros
{BANNER}

{BANNER}
//             Exported Types
{BANNER}
typedef struct {{
    uint32_t hwInstanceId;
    FreqHz_t frequency_hz;
    DutyPermille_t initialDuty_permille;
}} Drv{pascal}Config_t;

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}
/**
 * @brief Initialize {pascal} channels from a const configuration table in .rodata.
 * @param configTable Pointer to const Drv{pascal}Config_t array.
 * @param numChannels Number of entries in configTable.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e drv{pascal}_Init(const Drv{pascal}Config_t * const configTable,
                                     size_t numChannels);

/**
 * @brief Set output duty cycle in permille (0..1000) for a {pascal} channel.
 * @param channel Logical channel index (< numChannels).
 * @param duty_permille Desired duty cycle in permille.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e drv{pascal}_SetDuty(size_t channel, DutyPermille_t duty_permille);

#endif /* DRV_{upper}_H_ */
"""

    drv_c = f"""{BANNER}
/**
 * @file        drv{pascal}.c
 * @brief       Hardware peripheral driver implementation for {pascal}
 */
{BANNER}

{BANNER}
//             Includes
{BANNER}
#include "drv{pascal}.h"

{BANNER}
//             Private Macros
{BANNER}
#define DRV_{upper}_MAX_DUTY_PERMILLE (1000U)

{BANNER}
//             Private Types
{BANNER}

{BANNER}
//             Private Variables
{BANNER}
static const Drv{pascal}Config_t *s_configTable = NULL;
static size_t s_numChannels = 0U;

{BANNER}
//             Private Prototypes
{BANNER}

{BANNER}
//             Implementation
{BANNER}
Status_e drv{pascal}_Init(const Drv{pascal}Config_t * const configTable,
                          size_t numChannels) {{
    if ((configTable == NULL) || (numChannels == 0U)) {{
        return STATUS_ERR_NULL_PTR;
    }}
    for (size_t i = 0U; i < numChannels; ++i) {{
        if (configTable[i].initialDuty_permille.permille > DRV_{upper}_MAX_DUTY_PERMILLE) {{
            return STATUS_ERR_INVALID_PARAM;
        }}
    }}
    s_configTable = configTable;
    s_numChannels = numChannels;
    return STATUS_OK;
}}

Status_e drv{pascal}_SetDuty(size_t channel, DutyPermille_t duty_permille) {{
    if (s_configTable == NULL) {{
        return STATUS_ERR_UNINITIALIZED;
    }}
    if (channel >= s_numChannels) {{
        return STATUS_ERR_INVALID_CHANNEL;
    }}
    if (duty_permille.permille > DRV_{upper}_MAX_DUTY_PERMILLE) {{
        return STATUS_ERR_INVALID_PARAM;
    }}
    (void)s_configTable[channel].hwInstanceId;
    return STATUS_OK;
}}
"""

    fake_h = f"""#ifndef FAKE_DRV_{upper}_H_
#define FAKE_DRV_{upper}_H_

#include "drv{pascal}.h"

void fakeDrv{pascal}_Reset(void);
void fakeDrv{pascal}_InjectStatus(Status_e status);
DutyPermille_t fakeDrv{pascal}_GetLastDuty(size_t channel);
uint32_t fakeDrv{pascal}_GetSetDutyCallCount(void);

#endif /* FAKE_DRV_{upper}_H_ */
"""

    fake_c = f"""#include "fake_drv{pascal}.h"

#define FAKE_DRV_{upper}_MAX_CHANNELS (16U)

static const Drv{pascal}Config_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static DutyPermille_t s_lastDuty[FAKE_DRV_{upper}_MAX_CHANNELS];
static uint32_t s_setDutyCalls = 0U;
static Status_e s_injectedStatus = STATUS_OK;

void fakeDrv{pascal}_Reset(void) {{
    s_configTable = NULL;
    s_numChannels = 0U;
    s_setDutyCalls = 0U;
    s_injectedStatus = STATUS_OK;
    for (size_t i = 0U; i < FAKE_DRV_{upper}_MAX_CHANNELS; ++i) {{
        s_lastDuty[i].permille = 0U;
    }}
}}

void fakeDrv{pascal}_InjectStatus(Status_e status) {{
    s_injectedStatus = status;
}}

DutyPermille_t fakeDrv{pascal}_GetLastDuty(size_t channel) {{
    if (channel < FAKE_DRV_{upper}_MAX_CHANNELS) {{
        return s_lastDuty[channel];
    }}
    DutyPermille_t const zero = {{ .permille = 0U }};
    return zero;
}}

uint32_t fakeDrv{pascal}_GetSetDutyCallCount(void) {{
    return s_setDutyCalls;
}}

Status_e drv{pascal}_Init(const Drv{pascal}Config_t * const configTable,
                          size_t numChannels) {{
    if (s_injectedStatus != STATUS_OK) {{
        return s_injectedStatus;
    }}
    if ((configTable == NULL) || (numChannels == 0U) ||
        (numChannels > FAKE_DRV_{upper}_MAX_CHANNELS)) {{
        return STATUS_ERR_NULL_PTR;
    }}
    for (size_t i = 0U; i < numChannels; ++i) {{
        if (configTable[i].initialDuty_permille.permille > 1000U) {{
            return STATUS_ERR_INVALID_PARAM;
        }}
        s_lastDuty[i] = configTable[i].initialDuty_permille;
    }}
    s_configTable = configTable;
    s_numChannels = numChannels;
    return STATUS_OK;
}}

Status_e drv{pascal}_SetDuty(size_t channel, DutyPermille_t duty_permille) {{
    if (s_injectedStatus != STATUS_OK) {{
        return s_injectedStatus;
    }}
    if (s_configTable == NULL) {{
        return STATUS_ERR_UNINITIALIZED;
    }}
    if (channel >= s_numChannels) {{
        return STATUS_ERR_INVALID_CHANNEL;
    }}
    if (duty_permille.permille > 1000U) {{
        return STATUS_ERR_INVALID_PARAM;
    }}
    s_lastDuty[channel] = duty_permille;
    s_setDutyCalls++;
    return STATUS_OK;
}}
"""

    test_c = f"""#include <assert.h>
#include "fake_drv{pascal}.h"

static const Drv{pascal}Config_t kTestTable[1] = {{
    [0] = {{
        .hwInstanceId         = 0U,
        .frequency_hz         = {{ .hz = 25000U }},
        .initialDuty_permille = {{ .permille = 100U }}
    }}
}};

int main(void) {{
    fakeDrv{pascal}_Reset();
    assert(drv{pascal}_Init(NULL, 0U) == STATUS_ERR_NULL_PTR);
    assert(drv{pascal}_SetDuty(0U, (DutyPermille_t){{ .permille = 500U }}) ==
           STATUS_ERR_UNINITIALIZED);

    assert(drv{pascal}_Init(kTestTable, ARRAY_LEN(kTestTable)) == STATUS_OK);
    assert(drv{pascal}_SetDuty(5U, (DutyPermille_t){{ .permille = 500U }}) ==
           STATUS_ERR_INVALID_CHANNEL);
    assert(drv{pascal}_SetDuty(0U, (DutyPermille_t){{ .permille = 1001U }}) ==
           STATUS_ERR_INVALID_PARAM);

    assert(drv{pascal}_SetDuty(0U, (DutyPermille_t){{ .permille = 650U }}) == STATUS_OK);
    assert(fakeDrv{pascal}_GetLastDuty(0U).permille == 650U);
    assert(fakeDrv{pascal}_GetSetDutyCallCount() == 1U);
    return 0;
}}
"""

    write_if_missing(root / f"drvs/{snake}/drv{pascal}.h", drv_h)
    write_if_missing(root / f"drvs/{snake}/drv{pascal}.c", drv_c)
    write_if_missing(root / f"drvs/{snake}/test/fake_drv{pascal}.h", fake_h)
    write_if_missing(root / f"drvs/{snake}/test/fake_drv{pascal}.c", fake_c)
    write_if_missing(root / f"drvs/{snake}/test/test_drv{pascal}.c", test_c)


def scaffold_bsp(root: pathlib.Path, name: str) -> None:
    snake = to_snake(name)
    pascal = to_pascal(name)
    upper = snake.upper()
    scaffold_drv(root, name)

    bsp_cfg_h = f"""{BANNER}
/**
 * @file        bsp{pascal}Cfg.h
 * @brief       Board channel enum and const configuration table declaration for {pascal}
 */
{BANNER}
#ifndef BSP_{upper}_CFG_H_
#define BSP_{upper}_CFG_H_

{BANNER}
//             Includes
{BANNER}
#include "drv{pascal}.h"

{BANNER}
//             Exported Macros
{BANNER}

{BANNER}
//             Exported Types
{BANNER}
typedef enum {{
    BSP_{upper}_CH_PRIMARY = 0,
    BSP_{upper}_CH_COUNT
}} Bsp{pascal}Channel_e;

{BANNER}
//             Exported Variables
{BANNER}
extern const Drv{pascal}Config_t kBsp{pascal}ConfigTable[BSP_{upper}_CH_COUNT];

{BANNER}
//             Exported Prototypes
{BANNER}

#endif /* BSP_{upper}_CFG_H_ */
"""

    bsp_cfg_c = f"""{BANNER}
/**
 * @file        bsp{pascal}Cfg.c
 * @brief       Board const configuration table in .rodata Flash for {pascal}
 */
{BANNER}

{BANNER}
//             Includes
{BANNER}
#include "bsp{pascal}Cfg.h"

{BANNER}
//             Private Macros
{BANNER}

{BANNER}
//             Private Types
{BANNER}

{BANNER}
//             Private Variables
{BANNER}
const Drv{pascal}Config_t kBsp{pascal}ConfigTable[BSP_{upper}_CH_COUNT] = {{
    [BSP_{upper}_CH_PRIMARY] = {{
        .hwInstanceId         = 0U,
        .frequency_hz         = {{ .hz = 25000U }},
        .initialDuty_permille = {{ .permille = 0U }}
    }}
}};

_Static_assert(ARRAY_LEN(kBsp{pascal}ConfigTable) == (size_t)BSP_{upper}_CH_COUNT,
               "kBsp{pascal}ConfigTable size must match Bsp{pascal}Channel_e count");

{BANNER}
//             Private Prototypes
{BANNER}

{BANNER}
//             Implementation
{BANNER}
"""

    bsp_h = f"""{BANNER}
/**
 * @file        bsp{pascal}.h
 * @brief       Board-meaningful hardware abstraction for {pascal}
 */
{BANNER}
#ifndef BSP_{upper}_H_
#define BSP_{upper}_H_

{BANNER}
//             Includes
{BANNER}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

{BANNER}
//             Exported Macros
{BANNER}

{BANNER}
//             Exported Types
{BANNER}

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}
/**
 * @brief Initialize board {pascal} channels using kBsp{pascal}ConfigTable.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e bsp{pascal}_Init(void);

/**
 * @brief Set primary board actuator duty cycle in permille (0..1000).
 * @param duty_permille Desired duty cycle in permille.
 * @return STATUS_OK on success, error status otherwise.
 */
MUST_CHECK Status_e bsp{pascal}_PrimarySetDuty(DutyPermille_t duty_permille);

#endif /* BSP_{upper}_H_ */
"""

    bsp_c = f"""{BANNER}
/**
 * @file        bsp{pascal}.c
 * @brief       Board Support Package implementation for {pascal}
 */
{BANNER}

{BANNER}
//             Includes
{BANNER}
#include "bsp{pascal}.h"
#include "bsp{pascal}Cfg.h"
#include "drv{pascal}.h"

{BANNER}
//             Private Macros
{BANNER}

{BANNER}
//             Private Types
{BANNER}

{BANNER}
//             Private Variables
{BANNER}

{BANNER}
//             Private Prototypes
{BANNER}

{BANNER}
//             Implementation
{BANNER}
Status_e bsp{pascal}_Init(void) {{
    return drv{pascal}_Init(kBsp{pascal}ConfigTable, (size_t)BSP_{upper}_CH_COUNT);
}}

Status_e bsp{pascal}_PrimarySetDuty(DutyPermille_t duty_permille) {{
    return drv{pascal}_SetDuty((size_t)BSP_{upper}_CH_PRIMARY, duty_permille);
}}
"""

    write_if_missing(root / f"src/bsp/config/bsp{pascal}Cfg.h", bsp_cfg_h)
    write_if_missing(root / f"src/bsp/config/bsp{pascal}Cfg.c", bsp_cfg_c)
    write_if_missing(root / f"src/bsp/bsp{pascal}.h", bsp_h)
    write_if_missing(root / f"src/bsp/bsp{pascal}.c", bsp_c)


def scaffold_lib(root: pathlib.Path, name: str) -> None:
    snake = to_snake(name)
    camel = to_camel(name)
    pascal = to_pascal(name)
    upper = snake.upper()
    write_if_missing(root / "src/config/project_types.h", PROJECT_TYPES_H)

    lib_h = f"""{BANNER}
/**
 * @file        {camel}.h
 * @brief       Pure vertical utility library for {pascal} (zero hardware dependencies)
 */
{BANNER}
#ifndef LIB_{upper}_H_
#define LIB_{upper}_H_

{BANNER}
//             Includes
{BANNER}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

{BANNER}
//             Exported Macros
{BANNER}

{BANNER}
//             Exported Types
{BANNER}
typedef struct {{
    uint8_t *storage;
    size_t capacity;
    size_t head;
    size_t tail;
    size_t count;
}} {pascal}_t;

{BANNER}
//             Exported Variables
{BANNER}

{BANNER}
//             Exported Prototypes
{BANNER}
/**
 * @brief Initialize a {pascal} instance backed by caller-supplied static storage.
 * @param inst Pointer to instance state.
 * @param storageBuf Pointer to static byte array.
 * @param capacity Size of storageBuf in bytes (> 0).
 * @return STATUS_OK on success, STATUS_ERR_NULL_PTR or STATUS_ERR_INVALID_PARAM on error.
 */
MUST_CHECK Status_e {camel}_Init({pascal}_t * const inst,
                                 uint8_t * const storageBuf,
                                 size_t capacity);

/**
 * @brief Push one byte into the {pascal} instance.
 * @param inst Pointer to initialized instance.
 * @param byte Value to push.
 * @return STATUS_OK on success, STATUS_ERR_BUFFER_FULL or STATUS_ERR_NULL_PTR on error.
 */
MUST_CHECK Status_e {camel}_Push({pascal}_t * const inst, uint8_t byte);

/**
 * @brief Pop one byte from the {pascal} instance.
 * @param inst Pointer to initialized instance.
 * @param outByte Pointer to receive popped byte.
 * @return STATUS_OK on success, STATUS_ERR_BUFFER_EMPTY or STATUS_ERR_NULL_PTR on error.
 */
MUST_CHECK Status_e {camel}_Pop({pascal}_t * const inst, uint8_t * const outByte);

#endif /* LIB_{upper}_H_ */
"""

    lib_c = f"""{BANNER}
/**
 * @file        {camel}.c
 * @brief       Pure vertical implementation for {pascal}
 */
{BANNER}

{BANNER}
//             Includes
{BANNER}
#include "{camel}.h"

{BANNER}
//             Private Macros
{BANNER}

{BANNER}
//             Private Types
{BANNER}

{BANNER}
//             Private Variables
{BANNER}

{BANNER}
//             Private Prototypes
{BANNER}

{BANNER}
//             Implementation
{BANNER}
Status_e {camel}_Init({pascal}_t * const inst,
                      uint8_t * const storageBuf,
                      size_t capacity) {{
    if ((inst == NULL) || (storageBuf == NULL)) {{
        return STATUS_ERR_NULL_PTR;
    }}
    if (capacity == 0U) {{
        return STATUS_ERR_INVALID_PARAM;
    }}
    inst->storage = storageBuf;
    inst->capacity = capacity;
    inst->head = 0U;
    inst->tail = 0U;
    inst->count = 0U;
    return STATUS_OK;
}}

Status_e {camel}_Push({pascal}_t * const inst, uint8_t byte) {{
    if ((inst == NULL) || (inst->storage == NULL)) {{
        return STATUS_ERR_NULL_PTR;
    }}
    if (inst->count >= inst->capacity) {{
        return STATUS_ERR_BUFFER_FULL;
    }}
    inst->storage[inst->head] = byte;
    inst->head = (inst->head + 1U) % inst->capacity;
    inst->count++;
    return STATUS_OK;
}}

Status_e {camel}_Pop({pascal}_t * const inst, uint8_t * const outByte) {{
    if ((inst == NULL) || (inst->storage == NULL) || (outByte == NULL)) {{
        return STATUS_ERR_NULL_PTR;
    }}
    if (inst->count == 0U) {{
        return STATUS_ERR_BUFFER_EMPTY;
    }}
    *outByte = inst->storage[inst->tail];
    inst->tail = (inst->tail + 1U) % inst->capacity;
    inst->count--;
    return STATUS_OK;
}}
"""

    test_c = f"""#include <assert.h>
#include "{camel}.h"

int main(void) {{
    uint8_t backing[4] = {{ 0U }};
    {pascal}_t buf;
    uint8_t out = 0U;

    assert({camel}_Init(NULL, backing, sizeof(backing)) == STATUS_ERR_NULL_PTR);
    assert({camel}_Init(&buf, backing, 0U) == STATUS_ERR_INVALID_PARAM);
    assert({camel}_Init(&buf, backing, sizeof(backing)) == STATUS_OK);

    assert({camel}_Pop(&buf, &out) == STATUS_ERR_BUFFER_EMPTY);
    assert({camel}_Push(&buf, 0x11U) == STATUS_OK);
    assert({camel}_Push(&buf, 0x22U) == STATUS_OK);
    assert({camel}_Pop(&buf, &out) == STATUS_OK);
    assert(out == 0x11U);
    assert({camel}_Pop(&buf, &out) == STATUS_OK);
    assert(out == 0x22U);
    return 0;
}}
"""
    write_if_missing(root / f"libs/{snake}/{camel}.h", lib_h)
    write_if_missing(root / f"libs/{snake}/{camel}.c", lib_c)
    write_if_missing(root / f"libs/{snake}/test/test_{snake}.c", test_c)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a complete Embedded C project structure or individual layer module."
    )
    parser.add_argument(
        "--init-project",
        action="store_true",
        help="Initialize the full 4-layer (app, bsp, config, drv) + vertical libs/ directory tree.",
    )
    parser.add_argument(
        "--layer",
        choices=("app", "bsp", "config", "drv", "lib"),
        help="Target firmware layer to scaffold.",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Module or peripheral name (e.g., thermal, pwm, adc, ring_buf).",
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path("."),
        help="Target project root directory (default: current directory).",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    lints_dir = pathlib.Path(__file__).resolve().parent

    if not args.init_project and not args.layer:
        parser.error("Specify --init-project and/or --layer {app,bsp,config,drv,lib} <name>.")

    if args.init_project:
        scaffold_init_project(root, lints_dir)

    if args.layer:
        if not args.name:
            parser.error(f"--layer {args.layer} requires a module <name>.")
        if args.layer == "app":
            scaffold_app(root, args.name)
        elif args.layer == "config":
            scaffold_config(root, args.name)
        elif args.layer == "bsp":
            scaffold_bsp(root, args.name)
        elif args.layer == "drv":
            scaffold_drv(root, args.name)
        elif args.layer == "lib":
            scaffold_lib(root, args.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())

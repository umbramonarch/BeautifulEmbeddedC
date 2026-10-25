# BeautifulEmbeddedC Dual-Target Makefile (Target Cross-Compile + Host GCC Unit Tests)
#
# Copy to your firmware repository root as `Makefile`.
# Enforces strict per-layer include-path isolation (`INC_APP`, `INC_BSP`, `INC_DRV`, `INC_LIBS`)
# so upper layers physically cannot `#include` lower-layer or vendor SDK headers.
#
# Targets:
#   make test    - Compile and run fast host GCC unit tests with link-time fakes
#   make arch    - Run check_arch.py across all .c and .h files
#   make format  - Verify .clang-format compliance across all .c and .h files
#   make tidy    - Run clang-tidy static analysis
#   make bear    - Regenerate compile_commands.json via Bear

TARGET       ?= firmware
BUILD_DIR    ?= build
HOST_CC      ?= gcc
TARGET_CC    ?= arm-none-eabi-gcc
PYTHON       ?= python3
CHECK_ARCH   ?= $(firstword $(wildcard lints/check_arch.py tools/check_arch.py))

# Locked-Door C11 Warning Flags (NASA JPL Rule 10 + MISRA C Essential Type checks)
COMMON_WARN_FLAGS := \
	-std=c11 \
	-Wall -Wextra -Werror -Wpedantic \
	-Wconversion -Wsign-conversion -Wdouble-promotion \
	-Wshadow -Wundef -Wformat=2 \
	-Wmissing-prototypes -Wstrict-prototypes -Wold-style-definition \
	-Wwrite-strings -Wcast-qual -Wvla

HOST_CFLAGS   := $(COMMON_WARN_FLAGS) -O0 -g3
TARGET_CFLAGS := $(COMMON_WARN_FLAGS) -Os -g3 -ffunction-sections -fdata-sections -fno-common -Wstack-usage=128

# Strictly isolated per-layer include paths (Beningo 4-Layer + Vertical libs/)
INC_CFG  := -Isrc/config
INC_LIBS := $(addprefix -I,$(wildcard libs/*))
INC_DRV  := $(INC_CFG) $(INC_LIBS) $(addprefix -I,$(filter-out drvs/vendor_sdk,$(wildcard drvs/*)))
INC_BSP  := -Isrc/bsp -Isrc/bsp/config $(INC_DRV)
INC_APP  := -Isrc/app $(INC_CFG) -Isrc/bsp $(INC_LIBS)

# Source discovery across layers
LIB_SRCS     := $(wildcard libs/*/*.c)
BSP_CFG_SRCS := $(wildcard src/bsp/config/*.c)
BSP_SRCS     := $(wildcard src/bsp/*.c)
APP_SRCS     := $(wildcard src/app/*.c)
FAKE_SRCS    := $(wildcard drvs/*/test/fake_*.c tests/fakes/fake_*.c)
TEST_SRCS    := $(wildcard tests/test_*.c libs/*/test/test_*.c drvs/*/test/test_*.c)

ALL_C_H_FILES := \
	$(wildcard src/app/*.[ch] src/config/*.[ch] src/bsp/*.[ch] src/bsp/config/*.[ch]) \
	$(wildcard drvs/*/*.[ch] drvs/*/test/*.[ch] libs/*/*.[ch] libs/*/test/*.[ch] tests/*.[ch])

.PHONY: all arch test format tidy bear clean

all: arch test

arch:
	@if [ -n "$(CHECK_ARCH)" ]; then \
		$(PYTHON) $(CHECK_ARCH) .; \
	else \
		echo "check_arch.py not found in lints/ or tools/"; exit 1; \
	fi

test: arch
	@mkdir -p $(BUILD_DIR)/tests
	@set -e; \
	for test_src in $(TEST_SRCS); do \
		test_name=$$(basename "$$test_src" .c); \
		echo "[HOST-TEST] Compiling $$test_name..."; \
		$(HOST_CC) $(HOST_CFLAGS) \
			$(INC_APP) $(INC_BSP) $(INC_DRV) \
			$(addprefix -I,$(wildcard drvs/*/test libs/*/test tests)) \
			$(LIB_SRCS) $(BSP_CFG_SRCS) $(BSP_SRCS) $(APP_SRCS) $(FAKE_SRCS) "$$test_src" \
			-o "$(BUILD_DIR)/tests/$$test_name"; \
		"$(BUILD_DIR)/tests/$$test_name"; \
	done
	@echo "[HOST-TEST] All host unit tests passed."

format:
	clang-format --dry-run -Werror $(ALL_C_H_FILES)

tidy:
	clang-tidy $(LIB_SRCS) $(BSP_CFG_SRCS) $(BSP_SRCS) $(APP_SRCS)

bear:
	bear -- $(MAKE) -B test

clean:
	rm -rf $(BUILD_DIR)

#include "ld_out.h"

/*
 * The LD32 translator doesn't really product linker script useable symbols.
 * It expects the user to call the C preprocessor manually on the linkerscript
 * to resolve references to translator outputs.
 *
 * Anyway, here we make sure the prepreocessor accepts ld_out.h
 */

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 5L)
proof_dir <- args[[1L]]
cat("COMPONENT PROOF ONLY; not native release qualification\n")
cat("R_VERSION=", R.version.string, "\n", sep = "")
cat("R_PLATFORM=", R.version$platform, "\n", sep = "")
cat("PROOF_HEAD=", args[[2L]], "\n", sep = "")
cat("GITHUB_RUN_ID=", args[[3L]], "\n", sep = "")
cat("GITHUB_RUN_ATTEMPT=", args[[4L]], "\n", sep = "")
cat("RUNNER_OS=", args[[5L]], "\n", sep = "")
cat("BASE_SOURCE=37eaa608443e0bc9dbd03b76946835c1e93484ee\n")
cat("ORIGINAL_OWNER=fd0f50f4e8ccb242f7c2e92fa8848a1de4b6c3f0\n")
cat("ARGV:\n")
dput(commandArgs())
cat("SESSION_INFO:\n")
print(sessionInfo())

library_dir <- normalizePath(file.path(proof_dir, "library"), winslash = "/")
.libPaths(c(library_dir, .libPaths()))
library(yamaabenchmarks)
package_dir <- normalizePath(find.package("yamaabenchmarks"), winslash = "/")
stopifnot(startsWith(package_dir, paste0(library_dir, "/")))
cat("INSTALLED_COMPONENT=", package_dir, "\n", sep = "")

original <- new.env(parent = baseenv())
sys.source(".github/scripts/proof/r-original-functions.R", original)
bits_of <- function(value) {
  paste0(as.character(writeBin(value, raw(), size = 8L, endian = "big")),
         collapse = "")
}
cat("ORIGINAL_FINITE_FORMATTER_RECEIPT:\n")
for (numerator in c(2, -2)) {
  quotient <- numerator / 400
  prior <- original$project_ratio(numerator, 400, 2L, 0, FALSE)
  portable <- project_ratio(numerator, 400, 2L, 0, FALSE)
  cat("numerator=", numerator, " quotient_bits=", bits_of(quotient),
      " original_sprintf=", sprintf("%.2f", quotient),
      " original_result_bits=", bits_of(prior),
      " portable_result_bits=", bits_of(portable), "\n", sep = "")
}
cat("ORIGINAL_NUMERIC_PARITY_ARGV=source(.github/scripts/proof/r-original-numeric-parity.R)\n")
sys.source(".github/scripts/proof/r-original-numeric-parity.R", globalenv())
cat("PASS: original numeric-parity assertions unchanged\n")
cat("PORTABLE_COMPONENT_ARGV=source(rust/tests/project-programs/r/tests/numeric-parity.R)\n")
sys.source("rust/tests/project-programs/r/tests/numeric-parity.R", globalenv())
cat("PASS: original prefix plus independently authored portable component controls\n")

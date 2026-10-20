# =============================================================================
# update_data.R - refresh the NAEP Explorer's data from the repo
#
# Purpose
#   app.R reads NAEP_Compiled_Wide.xlsx from its own folder so it can be
#   deployed to shinyapps.io as one folder. This writes that file from the
#   scraped repo output, in the same layout as the hand-built workbook.
#   Only run it after naep/scripts/03_validate.py passes -- until then, keep
#   using the hand-built workbook from the shared drive.
#
# Inputs (repo path, relative to the repo root)
#   naep/data/clean/naep_scores_wide.csv
#
# Outputs
#   naep/apps/explorer/NAEP_Compiled_Wide.xlsx   (git-ignored copy)
#
# Run (from the repo root)
#   Rscript naep/apps/explorer/update_data.R
# =============================================================================

# ---- Config -------------------------------------------------------------------

APP_DIR  <- "naep/apps/explorer"
SRC_FILE <- "naep/data/clean/naep_scores_wide.csv"
OUT_FILE <- file.path(APP_DIR, "NAEP_Compiled_Wide.xlsx")

# ---- Copy ---------------------------------------------------------------------

if (!requireNamespace("writexl", quietly = TRUE)) {
  stop("needs the writexl package: install.packages('writexl')")
}
if (!file.exists(SRC_FILE)) {
  stop("missing ", SRC_FILE, " -- run naep/scripts/01_scrape.py and 02_compile.py first")
}

# check.names = FALSE keeps headers like "Asian/Pacific Islander" as-is -- app.R
# selects columns by those exact names
wide <- read.csv(SRC_FILE, check.names = FALSE, stringsAsFactors = FALSE)

# app reads sheet "Sheet1", same as the hand-built workbook
writexl::write_xlsx(list(Sheet1 = wide), OUT_FILE)
cat("wrote", OUT_FILE, "-", nrow(wide), "rows\n")

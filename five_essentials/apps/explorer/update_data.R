# =============================================================================
# update_data.R - refresh the 5Essentials Explorer's data from the repo
#
# Purpose
#   The Shiny app reads only from its own data/ and www/geo/ folders so it can
#   be deployed to shinyapps.io as one folder. This script copies the current
#   repo outputs into those folders. Run it after the 5Essentials scraper or
#   the shared reference files change, then redeploy.
#
# Inputs (repo paths, relative to the repo root)
#   five_essentials/data/clean/5essentials_scores_wide.csv
#   five_essentials/data/clean/5essentials_schools.csv
#   five_essentials/data/clean/5essentials_measures_dictionary.csv
#   reference/schools/school_groups.json, school_esb.json, school_locations.json
#   reference/geo/networks.geojson, community_areas.geojson, esb_districts.geojson
#
# Outputs
#   five_essentials/apps/explorer/data/   and   five_essentials/apps/explorer/www/geo/
#
# Run (from the repo root)
#   Rscript five_essentials/apps/explorer/update_data.R
# =============================================================================

# ---- Config -------------------------------------------------------------------

APP_DIR <- "five_essentials/apps/explorer"

SCORE_FILES <- c(
  "five_essentials/data/clean/5essentials_scores_wide.csv",
  "five_essentials/data/clean/5essentials_schools.csv",
  "five_essentials/data/clean/5essentials_measures_dictionary.csv"
)

CROSSWALK_FILES <- c(
  "reference/schools/school_groups.json",
  "reference/schools/school_esb.json",
  "reference/schools/school_locations.json"
)

BOUNDARY_FILES <- c(
  "reference/geo/networks.geojson",
  "reference/geo/community_areas.geojson",
  "reference/geo/esb_districts.geojson"
)


# ---- Steps --------------------------------------------------------------------

#' Stop early with a clear message if run from the wrong folder.
check_repo_root <- function() {
  if (!dir.exists(APP_DIR)) {
    stop("Run this from the chicago-education-data repo root (couldn't find ",
         APP_DIR, ").", call. = FALSE)
  }
}

#' Copy files into a folder, reporting what was copied and what was missing.
copy_into <- function(files, dest_dir) {
  dir.create(dest_dir, recursive = TRUE, showWarnings = FALSE)
  missing <- files[!file.exists(files)]
  if (length(missing) > 0) {
    stop("Missing input file(s):\n  ", paste(missing, collapse = "\n  "),
         "\nRun the matching pipeline first (see the repo README).", call. = FALSE)
  }
  ok <- file.copy(files, dest_dir, overwrite = TRUE)
  message(sprintf("Copied %d file(s) to %s", sum(ok), dest_dir))
}

copy_scores     <- function() copy_into(SCORE_FILES, file.path(APP_DIR, "data"))
copy_crosswalks <- function() copy_into(CROSSWALK_FILES, file.path(APP_DIR, "data"))
copy_boundaries <- function() copy_into(BOUNDARY_FILES, file.path(APP_DIR, "www", "geo"))


# ---- Main ---------------------------------------------------------------------

main <- function() {
  check_repo_root()
  copy_scores()
  copy_crosswalks()
  copy_boundaries()
  message("Done. Run the app with: shiny::runApp(\"", APP_DIR, "\")")
}

main()

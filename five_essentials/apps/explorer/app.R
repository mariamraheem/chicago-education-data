# =============================================================================
# 5Essentials Explorer (Shiny)
#
# Purpose
#   Let anyone pick an essential, a survey respondent group and a set of
#   measures, then see the 2022-2026 trend at five levels: CPS district,
#   network, community area, Elected School Board (ESB) sub-district and
#   individual school, plus a map of any one measure by area or school.
#   Uses the same look as the "Chicago's NAEP Story"
#   dashboard (kidsfirstchicago.shinyapps.io/naep).
#
# Rules built into the app
#   - Measures are always shown within ONE respondent group: Teacher survey,
#     Student survey, or the composite Essential scores. A teacher measure and
#     a student measure can never be drawn in the same chart.
#   - Definitions come from the measures dictionary (latest year available).
#   - District / network / community / ESB views show the median (or mean) of
#     school scores, with the number of schools behind each point.
#
# Inputs
#   This app lives in chicago-education-data/five_essentials/apps/explorer/.
#   Its data/ and www/geo/ folders are filled by update_data.R (run from the
#   repo root) from the repo's own outputs, so nothing here is edited by hand:
#     data/5essentials_scores_wide.csv        <- five_essentials/data/clean/
#     data/5essentials_schools.csv            <- five_essentials/data/clean/
#     data/5essentials_measures_dictionary.csv <- five_essentials/data/clean/
#     data/school_groups.json, school_esb.json, school_locations.json
#                                             <- reference/schools/
#     www/geo/*.geojson                       <- reference/geo/
#   Optional: www/k1c_logo.png (same logo file as the NAEP app) for the header.
#
# Run (from the repo root)
#   Rscript five_essentials/apps/explorer/update_data.R
#   R -e 'shiny::runApp("five_essentials/apps/explorer")'
#   See five_essentials/apps/explorer/README.md for deploying to shinyapps.io.
# =============================================================================

library(shiny)
library(dplyr)
library(tidyr)
library(plotly)
library(ggplot2)
library(ggrepel)
library(stringr)

# ---- Config -----------------------------------------------------------------

SCORES_FILE   <- "data/5essentials_scores_wide.csv"
SCHOOLS_FILE  <- "data/5essentials_schools.csv"
DICT_FILE     <- "data/5essentials_measures_dictionary.csv"
GROUPS_FILE   <- "data/school_groups.json"
ESB_FILE      <- "data/school_esb.json"
LOCATIONS_FILE <- "data/school_locations.json"
LOGO_FILE     <- "www/k1c_logo.png"


APP_TITLE     <- "Chicago's 5Essentials Story"
DATA_BADGE    <- "Survey years 2022-2026"

# Grouping levels shown as tabs between District and School.
# Name = column in the school crosswalk, value = tab label.
GROUP_LEVELS <- c(
  network        = "Network",
  community_area = "Community Area",
  esb_district   = "ESB Sub-district"
)

# Map layers: boundary file (served from www/ so the browser loads it
# directly, which keeps the map fast), the GeoJSON property that names each
# area, and how to turn the app's group value into that property's spelling.
MAP_LAYERS <- list(
  network        = list(url = "geo/networks.geojson",
                        key = "network", to_key = identity),
  community_area = list(url = "geo/community_areas.geojson",
                        key = "community_area", to_key = toupper),
  esb_district   = list(url = "geo/esb_districts.geojson",
                        key = "sub", to_key = tolower)
)
SCHOOLS_LAYER <- "school"
MAP_CENTER    <- list(lat = 41.835, lon = -87.69)
MAP_ZOOM      <- 9.3
MAP_STYLE     <- "carto-positron"     # free basemap, no token needed

# UChicago Impact performance bands for 5Essentials scores
SCORE_BANDS   <- c("Very Weak", "Weak", "Neutral", "Strong", "Very Strong")
BAND_BREAKS   <- c(0, 20, 40, 60, 80, 100)
BAND_COLORS   <- c("#C05621", "#EDB98A", "#CBD5E0", "#8CC9A1", "#1B4D25")

# Indicators to leave out of the app (none right now). Add a name here to
# hide a measure, e.g. c("Grit").
EXCLUDE_INDICATORS <- character(0)

OVERVIEW_CHOICE <- "Essential scores (overview)"
ALL_CHOICE      <- "All measures"
COMPOSITE_LABEL <- "Composite"        # respondent label for essential scores
OVERALL_DEF     <- "Overall 5Essentials rating, combining all five essentials."
DEFAULT_ESSENTIAL <- "Involved Families"

MAX_SERIES      <- 6                  # most lines allowed in one chart
DEFAULT_SERIES  <- 3                  # pre-selected when a list is long

# NAEP dashboard colors
K1C_DARK   <- "#1B4D25"
K1C_GREEN  <- "#2C8C4C"
TEXT_DARK  <- "#2D3748"
TEXT_MUTED <- "#4A5568"
GRID_COLOR <- "#E2E8F0"
PAGE_BG    <- "#F7F9F7"
PALETTE    <- c(K1C_GREEN, "#2B6CB0", TEXT_DARK, "#718096", "#C05621", "#6B46C1")
Y_MAX      <- 100

# "Relative" color mode: light-to-dark green stretched over the scores shown
RELATIVE_SCALE <- list(c(0, 1), c("#E8F5EE", K1C_DARK))

# ---- Helpers ----------------------------------------------------------------

`%||%` <- function(x, y) if (is.null(x)) y else x

# ---- Data prep --------------------------------------------------------------

#' Read a CSV as a tibble, keeping column names exactly as written
#' (score columns have spaces and symbols, e.g. "Human & Social Resources").
read_csv_plain <- function(path) {
  as_tibble(utils::read.csv(path, check.names = FALSE, stringsAsFactors = FALSE,
                            na.strings = c("", "NA")))
}

#' Read the dictionary and keep one row per indicator (its latest year).
load_dictionary <- function(path) {
  read_csv_plain(path) |>
    mutate(
      essential  = if_else(tolower(essential) == "supplemental measures",
                           "Supplemental Measures", essential),
      respondent = if_else(level == "essential", COMPOSITE_LABEL, asked_of),
      description = case_when(
        indicator == "5Essentials" ~ OVERALL_DEF,
        TRUE ~ coalesce(description, "")
      )
    ) |>
    filter(indicator != "Supplemental Measures",        # no score column
           !indicator %in% EXCLUDE_INDICATORS) |>
    group_by(indicator) |>
    slice_max(survey_year, n = 1, with_ties = FALSE) |>
    ungroup() |>
    mutate(short_def = first_sentence(description)) |>
    select(indicator, essential, level, respondent, description, short_def)
}

#' First sentence of a definition, used in the chart footer.
first_sentence <- function(x) {
  sub("^(.*?[.!?])\\s.*$", "\\1", x)
}

#' Read the wide scores and reshape to one row per school-year-indicator.
load_scores <- function(path) {
  read_csv_plain(path) |>
    pivot_longer(-c(survey_year, school_id, school_name),
                 names_to = "indicator", values_to = "score",
                 values_drop_na = TRUE) |>
    filter(!indicator %in% EXCLUDE_INDICATORS) |>
    mutate(school_id = as.character(school_id))
}

#' School type and response rates by school-year.
load_schools <- function(path) {
  read_csv_plain(path) |>
    transmute(survey_year, school_id = as.character(school_id), school_type,
              student_response_rate, teacher_response_rate)
}

#' Network, community area and ESB sub-district for each school, taken from
#' the enrollment dashboard so groupings stay consistent across K1C tools.
load_crosswalk <- function(groups_path, esb_path) {
  groups <- jsonlite::fromJSON(groups_path)
  esb    <- jsonlite::fromJSON(esb_path)
  tibble(
    school_id      = names(groups),
    network        = vapply(groups, \(g) null_to_na(g$network), ""),
    community_area = tools::toTitleCase(tolower(
      vapply(groups, \(g) null_to_na(g$community_area), ""))),
    esb_district   = toupper(unlist(esb)[names(groups)])
  )
}

null_to_na <- function(x) if (is.null(x)) NA_character_ else x

#' Names of the areas drawn on each map layer (read once from www/geo/).
load_geo_keys <- function() {
  lapply(MAP_LAYERS, \(l) {
    geo <- jsonlite::read_json(file.path("www", l$url), simplifyVector = FALSE)
    vapply(geo$features, \(f) as.character(f$properties[[l$key]]), "")
  })
}

#' School points for the map.
load_school_locations <- function(path) {
  locs <- jsonlite::fromJSON(path)
  tibble(school_id = names(locs),
         lat = vapply(locs, \(x) x[1], 0),
         lon = vapply(locs, \(x) x[2], 0))
}

#' Join everything into one long table the app filters on.
build_school_scores <- function(scores, schools, crosswalk) {
  scores |>
    left_join(schools, by = c("survey_year", "school_id")) |>
    left_join(crosswalk, by = "school_id") |>
    mutate(school_type = coalesce(school_type, "Unknown"))
}

#' Latest name for each school, for the school dropdown.
school_choices <- function(scores) {
  latest <- scores |>
    distinct(school_id, school_name, survey_year) |>
    group_by(school_id) |>
    slice_max(survey_year, n = 1, with_ties = FALSE) |>
    ungroup() |>
    arrange(school_name)
  setNames(latest$school_id, latest$school_name)
}

#' Choices for a grouping level, sorted naturally ("Network 2" before 10).
group_choices <- function(school_scores, level) {
  vals <- unique(na.omit(school_scores[[level]]))
  num  <- suppressWarnings(as.numeric(gsub("\\D", "", vals)))
  vals[order(is.na(num), num, vals)]
}

#' Load and assemble all data once at startup.
load_all_data <- function() {
  dict      <- load_dictionary(DICT_FILE)
  scores    <- load_scores(SCORES_FILE)
  schools   <- load_schools(SCHOOLS_FILE)
  crosswalk <- load_crosswalk(GROUPS_FILE, ESB_FILE)
  list(
    dict          = dict,
    school_scores = build_school_scores(scores, schools, crosswalk),
    schools       = schools,
    school_list   = school_choices(scores),
    school_types  = sort(unique(schools$school_type)),
    geo_keys      = load_geo_keys(),
    locations     = load_school_locations(LOCATIONS_FILE)
  )
}


# ---- Measure selection ------------------------------------------------------

#' Respondent groups available for an essential (never mixed in one chart).
respondents_for <- function(dict, essential) {
  if (essential == OVERVIEW_CHOICE) return(COMPOSITE_LABEL)
  d <- filter(dict, level == "measure")
  if (essential != ALL_CHOICE) d <- filter(d, essential == !!essential)
  sort(unique(d$respondent))
}

#' Measures for an essential + respondent combination.
measures_for <- function(dict, essential, respondent) {
  if (essential == OVERVIEW_CHOICE) {
    comp <- filter(dict, respondent == COMPOSITE_LABEL)$indicator
    return(c("5Essentials", sort(setdiff(comp, "5Essentials"))))
  }
  d <- filter(dict, level == "measure", respondent == !!respondent)
  if (essential != ALL_CHOICE) d <- filter(d, essential == !!essential)
  sort(d$indicator)
}

default_selection <- function(choices) {
  if (length(choices) <= MAX_SERIES) choices else head(choices, DEFAULT_SERIES)
}


# ---- Aggregation ------------------------------------------------------------

#' Median or mean of school scores per year and indicator.
stat_fn <- function(stat) if (stat == "Mean") mean else median

aggregate_scores <- function(df, stat) {
  fn <- stat_fn(stat)
  df |>
    group_by(survey_year, indicator) |>
    summarise(score = round(fn(score)), n_schools = n(), .groups = "drop")
}

#' Add empty rows for years a measure wasn't reported, so the line breaks
#' instead of drawing straight across the missing year.
fill_year_gaps <- function(df, years) {
  complete(df, survey_year = years, indicator)
}

#' Filter school scores down to what one view should plot.
view_scores <- function(school_scores, level, unit, ctl) {
  df <- filter(school_scores, indicator %in% ctl$indicators)
  if (level == "school") {
    out <- df |>
      filter(school_id == unit) |>
      transmute(survey_year, indicator, score, n_schools = 1L)
  } else {
    df <- filter(df, school_type %in% ctl$school_types)
    if (level != "district") df <- df[df[[level]] %in% unit, ]
    out <- aggregate_scores(df, ctl$stat)
  }
  if (nrow(out) == 0) return(out)
  fill_year_gaps(out, sort(unique(school_scores$survey_year)))
}


# ---- Titles -------------------------------------------------------------------

chart_title <- function(ctl) {
  if (ctl$essential == OVERVIEW_CHOICE) return("Essential Scores")
  topic <- if (ctl$essential == ALL_CHOICE) "All Measures" else ctl$essential
  paste0(topic, " | ", ctl$respondent, " Survey")
}

chart_subtitle <- function(unit_label, df, level, ctl) {
  if (level == "school") return(unit_label)
  n_range <- range(df$n_schools, na.rm = TRUE)
  n_txt <- if (n_range[1] == n_range[2]) n_range[1] else paste(n_range, collapse = "-")
  types <- if (length(ctl$school_types) < length(ctl$all_types)) {
    paste0(" | ", paste(ctl$school_types, collapse = ", "))
  } else ""
  paste0(unit_label, " | ", ctl$stat, " of school scores (", n_txt,
         " schools per point)", types)
}


# ---- Interactive chart (plotly, NAEP dashboard style) -------------------------

plot_trend <- function(df, level, show_values) {
  series <- unique(df$indicator)
  colors <- setNames(PALETTE[seq_along(series)], series)
  years  <- sort(unique(df$survey_year))

  p <- plot_ly()
  for (s in series) {
    d <- filter(df, indicator == s)
    n_txt <- if (level == "school") "" else " (%{customdata} schools)"
    p <- add_trace(
      p, data = d, x = ~survey_year, y = ~score, name = s,
      type = "scatter",
      mode = "lines+markers",
      line = list(color = colors[[s]], width = 2.5),
      marker = list(color = colors[[s]], size = 7),
      connectgaps = FALSE, customdata = ~n_schools,
      hovertemplate = paste0(s, ": <b>%{y:.0f}</b>", n_txt, "<extra></extra>")
    )
    if (show_values) {
      p <- add_text(
        p, data = filter(d, !is.na(score)), x = ~survey_year, y = ~score,
        text = ~score, textposition = "top center", showlegend = FALSE,
        textfont = list(color = colors[[s]], size = 11), hoverinfo = "skip"
      )
    }
  }

  p |>
    layout(
      font = list(family = "Montserrat, sans-serif", color = TEXT_DARK),
      paper_bgcolor = "white", plot_bgcolor = "white",
      legend = list(orientation = "h", yanchor = "bottom", y = 1.04, x = 0,
                    font = list(size = 12, color = TEXT_MUTED),
                    bgcolor = PAGE_BG, bordercolor = GRID_COLOR, borderwidth = 1),
      xaxis = list(title = "", showgrid = FALSE, tickvals = years,
                   fixedrange = TRUE),
      yaxis = list(title = "Score (1-99)", range = c(0, Y_MAX + 5), dtick = 20,
                   gridcolor = GRID_COLOR, zeroline = FALSE, fixedrange = TRUE),
      hovermode = "x unified",
      margin = list(b = 40, l = 60, t = 75, r = 20)
    ) |>
    config(displayModeBar = FALSE)
}


# ---- Static chart for download (PNG with definitions footer) -----------------

chart_caption <- function(dict, indicators) {
  d <- filter(dict, indicator %in% indicators)
  d <- d[match(indicators, d$indicator), ]
  lines <- paste0(d$indicator, ": ", d$short_def)
  defs <- paste(vapply(lines, \(l) paste(strwrap(l, 150), collapse = "\n   "), ""),
                collapse = "\n")
  paste0(defs, "\nGaps in a line = measure not reported that year. ",
         "Source: UChicago Impact 5Essentials Survey. Kids First Chicago.")
}

plot_trend_png <- function(df, dict, title, subtitle, show_values) {
  series <- unique(df$indicator)
  colors <- setNames(PALETTE[seq_along(series)], series)
  years  <- sort(unique(df$survey_year))
  span   <- max(diff(range(years)), 1)
  pts    <- filter(df, !is.na(score))
  ends   <- pts |> group_by(indicator) |> slice_max(survey_year, n = 1) |> ungroup()

  p <- ggplot(df, aes(survey_year, score, colour = indicator, group = indicator)) +
    geom_line(linewidth = 1.2, na.rm = TRUE) +
    geom_point(data = pts, size = 2.6)

  if (show_values) {
    p <- p + geom_text(data = pts, aes(label = score), vjust = -1.1, size = 3.8,
                       fontface = "bold", show.legend = FALSE)
  }

  p +
    geom_text_repel(
      data = ends, aes(label = str_wrap(indicator, 22)),
      xlim = c(max(years) + span * 0.05, NA), hjust = 0, direction = "y",
      size = 4, fontface = "bold", lineheight = 0.9, segment.color = NA,
      show.legend = FALSE
    ) +
    scale_x_continuous(breaks = years,
                       limits = c(min(years), max(years) + span * 0.4),
                       expand = expansion(mult = c(0.02, 0))) +
    scale_y_continuous(limits = c(0, Y_MAX), breaks = seq(0, Y_MAX, 20)) +
    scale_colour_manual(values = colors) +
    coord_cartesian(clip = "off") +
    labs(title = title, subtitle = subtitle, x = NULL, y = NULL,
         caption = chart_caption(dict, series)) +
    theme_minimal(base_size = 15) +
    theme(
      plot.background      = element_rect(fill = "white", colour = NA),
      text                 = element_text(colour = TEXT_DARK),
      panel.grid.minor     = element_blank(),
      panel.grid.major.x   = element_blank(),
      panel.grid.major.y   = element_line(colour = GRID_COLOR),
      axis.text            = element_text(colour = TEXT_MUTED),
      legend.position      = "none",
      plot.title           = element_text(face = "bold", size = 22, colour = K1C_DARK),
      plot.subtitle        = element_text(colour = TEXT_MUTED, margin = margin(b = 10)),
      plot.caption         = element_text(hjust = 0, size = 10.5, colour = TEXT_MUTED,
                                          lineheight = 1.15),
      plot.title.position  = "plot",
      plot.caption.position = "plot",
      plot.margin          = margin(16, 20, 12, 16)
    )
}


# ---- Tables and definitions -------------------------------------------------

#' Wide table: one row per measure, one column per year (plus school counts
#' or response rates).
view_table <- function(df, level, unit, schools, respondent) {
  tbl <- df |>
    select(indicator, survey_year, score) |>
    filter(!is.na(score)) |>
    pivot_wider(names_from = survey_year, values_from = score) |>
    rename(Measure = indicator)

  if (level == "school") {
    if (respondent != COMPOSITE_LABEL) {
      rate_col <- if (respondent == "Student") "student_response_rate" else "teacher_response_rate"
      rates <- schools |>
        filter(school_id == unit) |>
        select(survey_year, rate = all_of(rate_col)) |>
        pivot_wider(names_from = survey_year, values_from = rate) |>
        mutate(Measure = paste(respondent, "response rate (%)"))
      tbl <- bind_rows(tbl, mutate(rates, across(-Measure, as.numeric)))
    }
  } else {
    n_row <- df |>
      group_by(survey_year) |>
      summarise(n = suppressWarnings(max(n_schools, na.rm = TRUE)), .groups = "drop") |>
      mutate(n = if_else(is.finite(n), n, NA_real_)) |>
      pivot_wider(names_from = survey_year, values_from = n) |>
      mutate(Measure = "Schools (max per year)")
    tbl <- bind_rows(tbl, n_row)
  }
  tbl[, c("Measure", sort(setdiff(names(tbl), "Measure")))]
}

definitions_ui <- function(dict, indicators) {
  d <- filter(dict, indicator %in% indicators)
  d <- d[match(indicators, d$indicator), ]
  tags$dl(class = "defs",
    lapply(seq_len(nrow(d)), \(i) tagList(
      tags$dt(d$indicator[i],
              span(class = "chip", d$respondent[i]),
              span(class = "chip chip-muted", d$essential[i])),
      tags$dd(d$description[i])
    ))
  )
}


# ---- Page pieces ------------------------------------------------------------

app_css <- function() {
  tags$style(HTML(sprintf("
    *{font-family:'Montserrat',sans-serif;}
    body{background:%1$s;}
    .title-header{background:%2$s;color:white;padding:16px 24px;margin:12px 0 20px;border-radius:4px;
                  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
    .title-header .brand{display:flex;align-items:center;gap:14px;}
    .title-header img{height:44px;}
    .title-header h2{margin:0;font-size:18px;font-weight:700;}
    .data-badge{font-size:10px;background:rgba(255,255,255,.15);padding:3px 8px;border-radius:10px;}
    .sidebar-panel{background:white;border:1px solid %3$s;border-radius:4px;padding:16px 14px;margin-top:20px;}
    .card-panel{background:white;border:1px solid %3$s;border-radius:4px;padding:16px;margin:20px 0 14px;}
    .card-panel + .card-panel{margin-top:0;}
    .card-title{font-size:13px;font-weight:600;color:%4$s;margin-bottom:12px;padding-bottom:8px;
                border-bottom:1px solid %3$s;}
    .view-title{font-size:15px;font-weight:700;color:%4$s;}
    .view-sub{font-size:13px;color:%5$s;margin-top:4px;}
    .section-label{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:%5$s;
                   font-weight:700;margin:6px 0 6px;}
    .side-note{font-size:11px;color:#a0aec0;line-height:1.5;}
    .nav-tabs .nav-link.active{background-color:%6$s!important;color:white!important;
                               border-color:%6$s!important;font-weight:600;}
    .nav-tabs .nav-link{color:%2$s;font-size:13px;font-weight:600;}
    label{font-size:12px;color:%5$s;font-weight:600;}
    .checkbox label, .radio label{font-weight:500;}
    hr{border-color:%3$s;margin:10px 0;}
    .chip{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;
          margin-left:6px;background:%6$s;color:white;vertical-align:middle;}
    .chip-muted{background:#E8F5EE;color:%2$s;}
    .defs dt{font-size:13px;color:%4$s;margin-top:10px;}
    .defs dd{font-size:13px;color:%5$s;line-height:1.6;margin:2px 0 0;}
    .dl-row{display:flex;gap:8px;margin-top:8px;}
    .btn-k1c{background:transparent;color:%2$s!important;border:1.5px solid %2$s;font-size:12px;
             font-weight:700;border-radius:4px;padding:6px 14px;}
    .btn-k1c:hover{background:#E8F5EE;}
    .table{font-size:12.5px;}
    .overview-hero{background:white;border:1px solid %3$s;border-left:4px solid %2$s;border-radius:4px;
                   padding:28px 32px;margin-top:20px;box-shadow:0 2px 10px rgba(27,77,37,.06);}
    .overview-hero p{font-size:14px;line-height:1.75;color:%5$s;}
    .overview-hero .tab-label{font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;
                              color:%2$s;margin:14px 0 2px;}
    .overview-hero .tab-desc{font-size:13px;line-height:1.65;color:%5$s;margin:0;}
    .band-legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:12px;color:%5$s;}
    .band-legend .swatch{display:inline-block;width:14px;height:14px;border-radius:3px;
                         margin-right:6px;vertical-align:-2px;}
    .band-legend .swatch-empty{background:white;border:1px solid #A0AEC0;}
    .unmapped{margin-top:10px;font-size:12px;color:%5$s;}
    .footer-note{text-align:center;font-size:11px;color:#a0aec0;margin:24px 0;}
  ", PAGE_BG, K1C_DARK, GRID_COLOR, TEXT_DARK, TEXT_MUTED, K1C_GREEN)))
}

title_header <- function() {
  logo <- if (file.exists(LOGO_FILE)) tags$img(src = basename(LOGO_FILE), alt = "Kids First Chicago")
  div(class = "title-header",
      div(class = "brand", logo, h2(APP_TITLE)),
      span(class = "data-badge", DATA_BADGE))
}

section_label <- function(text) div(class = "section-label", text)

overview_tab <- function() {
  div(class = "overview-hero",
    p("The 5Essentials Survey asks CPS students and teachers about the five",
      "conditions research links to school improvement: Ambitious Instruction,",
      "Collaborative Teachers, Effective Leaders, Involved Families and a",
      "Supportive Environment. This explorer shows how those scores have moved",
      "since 2022 for the whole district, for groups of schools, and for any",
      "single school."),
    div(class = "tab-label", "District, Network, Community Area, ESB Sub-district"),
    p(class = "tab-desc", "The median (or mean) of school scores in the group.",
      "Network, community area and ESB assignments match the K1C enrollment dashboard."),
    div(class = "tab-label", "Map"),
    p(class = "tab-desc", "One measure for one year, colored by the 5Essentials",
      "performance bands. Click an area or school to see its trend."),
    div(class = "tab-label", "School"),
    p(class = "tab-desc", "One school's scores, with its survey response rate."),
    div(class = "tab-label", "How to read the scores"),
    p(class = "tab-desc",
      "Scores run from 1 to 99. Teacher and student measures come from different",
      "surveys, so each chart shows one respondent group at a time. A gap in a",
      "line means the measure wasn't reported that year (for example, several",
      "student measures and the overall rating are missing for 2025).")
  )
}


# ---- View module (one per tab) ----------------------------------------------

trend_view_ui <- function(id, data, aggregate = TRUE, selector_label = NULL,
                          selector_note = NULL) {
  ns <- NS(id)
  essentials <- sort(unique(filter(data$dict, level == "measure")$essential))

  fluidRow(
    column(3, div(class = "sidebar-panel",
      if (!is.null(selector_label)) tagList(
        section_label(selector_label),
        selectizeInput(ns("unit"), NULL, choices = NULL, width = "100%"),
        if (!is.null(selector_note)) div(class = "side-note", selector_note),
        hr()
      ),
      section_label("Essential"),
      selectInput(ns("essential"), NULL,
                  choices = c(OVERVIEW_CHOICE, essentials, ALL_CHOICE),
                  selected = DEFAULT_ESSENTIAL, width = "100%"),
      conditionalPanel(
        sprintf("input.essential != '%s'", OVERVIEW_CHOICE), ns = ns,
        section_label("Survey respondent"),
        radioButtons(ns("respondent"), NULL, choices = "Teacher", inline = TRUE),
        div(class = "side-note",
            "Teacher and student measures come from different surveys, so they",
            "are never shown in the same chart.")
      ),
      hr(),
      section_label("Measures"),
      checkboxGroupInput(ns("indicators"), NULL, choices = NULL),
      if (aggregate) tagList(
        hr(),
        section_label("Combine school scores"),
        radioButtons(ns("stat"), NULL, choices = c("Median", "Mean"), inline = TRUE),
        section_label("School types"),
        checkboxGroupInput(ns("school_types"), NULL, choices = data$school_types,
                           selected = data$school_types)
      ),
      hr(),
      checkboxInput(ns("show_values"), "Show values on chart", FALSE)
    )),
    column(9,
      div(class = "card-panel",
          div(class = "view-title", textOutput(ns("title"), inline = TRUE)),
          div(class = "view-sub", textOutput(ns("subtitle"), inline = TRUE))),
      div(class = "card-panel",
          div(class = "card-title", "Trend, 2022-2026"),
          plotlyOutput(ns("plot"), height = "470px"),
          div(class = "dl-row",
              downloadButton(ns("dl_png"), "Chart (PNG)", class = "btn-k1c"),
              downloadButton(ns("dl_csv"), "Data (CSV)", class = "btn-k1c"))),
      div(class = "card-panel",
          div(class = "card-title", "Scores by year"),
          tableOutput(ns("table"))),
      div(class = "card-panel",
          div(class = "card-title", "What these measures mean"),
          uiOutput(ns("defs")))
    )
  )
}

trend_view_server <- function(id, data, level, choices = NULL,
                              unit_label = "All CPS schools") {
  moduleServer(id, function(input, output, session) {

    if (!is.null(choices)) {
      updateSelectizeInput(session, "unit", choices = choices, server = TRUE)
    }

    # Respondent options follow the essential; measures follow both.
    update_measures <- function(respondent) {
      ch <- measures_for(data$dict, input$essential, respondent)
      updateCheckboxGroupInput(session, "indicators", choices = ch,
                               selected = default_selection(ch))
    }
    observeEvent(input$essential, {
      resp <- respondents_for(data$dict, input$essential)
      keep <- if (isTRUE(input$respondent %in% resp)) input$respondent else resp[1]
      updateRadioButtons(session, "respondent", choices = resp, selected = keep,
                         inline = TRUE)
      update_measures(keep)
    })
    observeEvent(input$respondent, update_measures(input$respondent),
                 ignoreInit = TRUE)

    # Measures are re-checked against the current respondent so a mixed
    # teacher/student chart can't slip through while inputs are updating.
    controls <- reactive({
      req(input$essential)
      resp  <- if (input$essential == OVERVIEW_CHOICE) COMPOSITE_LABEL else input$respondent
      valid <- measures_for(data$dict, input$essential, resp)
      inds  <- intersect(input$indicators, valid)
      validate(
        need(length(inds) > 0, "Pick at least one measure."),
        need(length(inds) <= MAX_SERIES,
             paste("Pick", MAX_SERIES, "or fewer measures so the chart stays readable."))
      )
      list(essential = input$essential, respondent = resp, indicators = inds,
           stat = input$stat %||% "Median",
           school_types = input$school_types %||% data$school_types,
           all_types = data$school_types, show_values = isTRUE(input$show_values))
    })

    unit <- reactive({
      if (is.null(choices)) return(NA)
      req(input$unit)
      input$unit
    })

    label <- reactive({
      if (is.null(choices)) return(unit_label)
      if (level == "school") names(choices)[choices == unit()] else unit()
    })

    plot_data <- reactive({
      df <- view_scores(data$school_scores, level, unit(), controls())
      validate(need(nrow(df) > 0, "No scores for this selection."))
      df
    })

    title    <- reactive(chart_title(controls()))
    subtitle <- reactive(chart_subtitle(label(), plot_data(), level, controls()))

    output$title    <- renderText(title())
    output$subtitle <- renderText(subtitle())
    output$plot     <- renderPlotly(plot_trend(plot_data(), level, controls()$show_values))
    output$table    <- renderTable(
      view_table(plot_data(), level, unit(), data$schools, controls()$respondent),
      digits = 0, na = "-", striped = TRUE, width = "100%"
    )
    output$defs <- renderUI(definitions_ui(data$dict, unique(plot_data()$indicator)))

    file_stub <- reactive(gsub("[^A-Za-z0-9]+", "_", paste("5E", level, label())))
    output$dl_png <- downloadHandler(
      filename = \() paste0(file_stub(), ".png"),
      content  = \(file) ggsave(
        file,
        plot_trend_png(plot_data(), data$dict, title(), subtitle(), controls()$show_values),
        width = 13, height = 8.5, dpi = 150, bg = "white")
    )
    output$dl_csv <- downloadHandler(
      filename = \() paste0(file_stub(), ".csv"),
      content  = \(file) write.csv(mutate(plot_data(), unit = label()), file,
                                   row.names = FALSE)
    )
  })
}


# ---- Map ----------------------------------------------------------------------

score_band <- function(score) {
  cut(score, BAND_BREAKS, labels = SCORE_BANDS, right = FALSE, include.lowest = TRUE)
}

#' One score per area (or per school) for a single measure and year.
map_scores <- function(data, geography, ctl, year) {
  df <- filter(data$school_scores, indicator == ctl$indicators[1], survey_year == year)

  if (geography == SCHOOLS_LAYER) {
    out <- df |>
      inner_join(data$locations, by = "school_id") |>
      transmute(unit = school_id, name = school_name, score, n_schools = 1L, lat, lon)
  } else {
    out <- df |>
      filter(school_type %in% ctl$school_types, !is.na(.data[[geography]])) |>
      group_by(unit = .data[[geography]]) |>
      summarise(score = round(stat_fn(ctl$stat)(score)), n_schools = n(),
                .groups = "drop") |>
      mutate(name = unit)
  }
  mutate(out, band = score_band(score))
}

map_hover <- function(df, geography, measure, stat) {
  n_txt <- if (geography == SCHOOLS_LAYER) "" else
    paste0("<br>", stat, " of ", df$n_schools, " schools")
  paste0("<b>", df$name, "</b><br>", measure, ": <b>", df$score, "</b> (",
         df$band, ")", n_txt)
}

#' Areas in the data that have no boundary to draw (e.g. Charter, ISP and
#' Options networks are citywide, not geographic).
unmapped_units <- function(df, geo_keys, geography) {
  if (geography == SCHOOLS_LAYER) return(df[0, ])
  keys <- MAP_LAYERS[[geography]]$to_key(df$unit)
  df[!keys %in% geo_keys[[geography]], ]
}

#' Choropleth (areas) or point map (schools), colored by 5Essentials band.
plot_map <- function(df, geo_keys, geography, measure, stat, source, color_mode = "bands") {
  df$hover <- map_hover(df, geography, measure, stat)
  p <- plot_ly(source = source)
  relative <- color_mode == "relative"
  colorbar <- list(title = list(text = "Score", font = list(size = 11)),
                   thickness = 12, len = 0.5, x = 0.98)

  if (geography == SCHOOLS_LAYER && relative) {
    p <- add_trace(
      p, data = df, type = "scattermapbox", mode = "markers",
      lat = ~lat, lon = ~lon, customdata = ~unit,
      marker = list(size = 9, opacity = 0.9, color = ~score,
                    colorscale = RELATIVE_SCALE, showscale = TRUE, colorbar = colorbar),
      text = ~hover, hovertemplate = "%{text}<extra></extra>"
    )
  } else if (geography == SCHOOLS_LAYER) {
    for (i in seq_along(SCORE_BANDS)) {
      d <- filter(df, band == SCORE_BANDS[i])
      if (nrow(d) == 0) next
      p <- add_trace(
        p, data = d, type = "scattermapbox", mode = "markers",
        lat = ~lat, lon = ~lon, name = SCORE_BANDS[i], customdata = ~unit,
        marker = list(size = 9, color = BAND_COLORS[i], opacity = 0.9),
        text = ~hover, hovertemplate = "%{text}<extra></extra>"
      )
    }
  } else {
    layer <- MAP_LAYERS[[geography]]
    fid   <- paste0("properties.", layer$key)
    df    <- mutate(df, key = layer$to_key(unit))
    no_data <- setdiff(geo_keys[[geography]], df$key)

    if (length(no_data) > 0) {
      p <- add_trace(
        p, type = "choroplethmapbox", geojson = layer$url,
        featureidkey = fid, locations = no_data, z = rep(1, length(no_data)),
        colorscale = list(c(0, 1), c("#FFFFFF", "#FFFFFF")), showscale = FALSE,
        marker = list(opacity = 0.5, line = list(color = "#A0AEC0", width = 1)),
        hovertemplate = "%{location}<br>No data<extra></extra>"
      )
    }

    if (relative) {
      fill <- list(z = df$score, colorscale = RELATIVE_SCALE, showscale = TRUE,
                   colorbar = colorbar)
    } else {
      # z is the band number (1-5) so each band gets exactly one flat color
      n     <- length(SCORE_BANDS)
      stops <- sort(c(seq(0, 1, length.out = n + 1), seq(0, 1, length.out = n + 1)[2:n]))
      fill  <- list(z = as.integer(df$band), zmin = 0.5, zmax = n + 0.5,
                    colorscale = list(stops, rep(BAND_COLORS, each = 2)),
                    showscale = FALSE)
    }
    p <- add_trace(
      p, type = "choroplethmapbox", geojson = layer$url,
      featureidkey = fid, locations = df$key,
      z = fill$z, zmin = fill$zmin, zmax = fill$zmax, colorscale = fill$colorscale,
      showscale = fill$showscale, colorbar = fill$colorbar, customdata = df$unit,
      marker = list(opacity = 0.85, line = list(color = "white", width = 1.2)),
      text = df$hover, hovertemplate = "%{text}<extra></extra>"
    )
  }

  p |>
    layout(
      mapbox = list(style = MAP_STYLE, center = MAP_CENTER, zoom = MAP_ZOOM),
      font = list(family = "Montserrat, sans-serif", color = TEXT_DARK),
      margin = list(l = 0, r = 0, t = 0, b = 0), showlegend = FALSE
    ) |>
    config(displayModeBar = FALSE, scrollZoom = TRUE) |>
    event_register("plotly_click")
}

band_legend <- function() {
  div(class = "band-legend",
      lapply(seq_along(SCORE_BANDS), \(i) span(
        span(class = "swatch", style = paste0("background:", BAND_COLORS[i])),
        paste0(SCORE_BANDS[i], " (", max(BAND_BREAKS[i], 1), "-",
               BAND_BREAKS[i + 1] - 1, ")"))),
      span(span(class = "swatch swatch-empty"), "No data"))
}


# ---- Map module ---------------------------------------------------------------

map_view_ui <- function(id, data) {
  ns <- NS(id)
  essentials <- sort(unique(filter(data$dict, level == "measure")$essential))
  geographies <- c(setNames(names(GROUP_LEVELS), GROUP_LEVELS),
                   setNames(SCHOOLS_LAYER, "Schools"))

  fluidRow(
    column(3, div(class = "sidebar-panel",
      section_label("Show"),
      radioButtons(ns("geography"), NULL, choices = geographies),
      section_label("Color by"),
      radioButtons(ns("color_mode"), NULL,
                   choices = c("5Essentials bands" = "bands", "Relative (spread)" = "relative")),
      div(class = "side-note",
          "Bands use UChicago's fixed cut points. Relative stretches the colors",
          "across the scores shown, to make small differences visible."),
      hr(),
      section_label("Essential"),
      selectInput(ns("essential"), NULL,
                  choices = c(OVERVIEW_CHOICE, essentials, ALL_CHOICE),
                  selected = DEFAULT_ESSENTIAL, width = "100%"),
      conditionalPanel(
        sprintf("input.essential != '%s'", OVERVIEW_CHOICE), ns = ns,
        section_label("Survey respondent"),
        radioButtons(ns("respondent"), NULL, choices = "Teacher", inline = TRUE)
      ),
      section_label("Measure"),
      selectInput(ns("measure"), NULL, choices = NULL, width = "100%"),
      section_label("Year"),
      selectInput(ns("year"), NULL, choices = NULL, width = "100%"),
      conditionalPanel(
        sprintf("input.geography != '%s'", SCHOOLS_LAYER), ns = ns,
        hr(),
        section_label("Combine school scores"),
        radioButtons(ns("stat"), NULL, choices = c("Median", "Mean"), inline = TRUE),
        section_label("School types"),
        checkboxGroupInput(ns("school_types"), NULL, choices = data$school_types,
                           selected = data$school_types)
      )
    )),
    column(9,
      div(class = "card-panel",
          div(class = "view-title", textOutput(ns("title"), inline = TRUE)),
          div(class = "view-sub", textOutput(ns("subtitle"), inline = TRUE))),
      div(class = "card-panel",
          div(class = "card-title", "Map"),
          plotlyOutput(ns("map"), height = "620px"),
          uiOutput(ns("legend")),
          uiOutput(ns("unmapped"))),
      div(class = "card-panel",
          div(class = "card-title", textOutput(ns("trend_title"), inline = TRUE)),
          plotlyOutput(ns("trend"), height = "360px")),
      div(class = "card-panel",
          div(class = "card-title", "What this measure means"),
          uiOutput(ns("defs")))
    )
  )
}

map_view_server <- function(id, data) {
  moduleServer(id, function(input, output, session) {
    map_source <- session$ns("map")

    # Respondent follows essential; measure list follows both; years follow measure.
    observeEvent(input$essential, {
      resp <- respondents_for(data$dict, input$essential)
      keep <- if (isTRUE(input$respondent %in% resp)) input$respondent else resp[1]
      updateRadioButtons(session, "respondent", choices = resp, selected = keep,
                         inline = TRUE)
      updateSelectInput(session, "measure",
                        choices = measures_for(data$dict, input$essential, keep))
    })
    observeEvent(input$respondent, {
      updateSelectInput(session, "measure",
                        choices = measures_for(data$dict, input$essential, input$respondent))
    }, ignoreInit = TRUE)
    observeEvent(input$measure, {
      req(input$measure)
      yrs <- sort(unique(filter(data$school_scores, indicator == input$measure)$survey_year),
                  decreasing = TRUE)
      keep <- if (isTRUE(input$year %in% yrs)) input$year else yrs[1]
      updateSelectInput(session, "year", choices = yrs, selected = keep)
    })

    controls <- reactive({
      req(input$essential, input$measure, input$year)
      resp <- if (input$essential == OVERVIEW_CHOICE) COMPOSITE_LABEL else input$respondent
      req(input$measure %in% measures_for(data$dict, input$essential, resp))
      list(essential = input$essential, respondent = resp,
           indicators = input$measure, year = as.integer(input$year),
           stat = input$stat %||% "Median",
           school_types = input$school_types %||% data$school_types,
           all_types = data$school_types, show_values = TRUE)
    })

    map_data <- reactive({
      ctl <- controls()
      df  <- map_scores(data, input$geography, ctl, ctl$year)
      validate(need(nrow(df) > 0, "No scores for this measure and year."))
      df
    })

    geo_label <- reactive({
      if (input$geography == SCHOOLS_LAYER) "school" else
        tolower(GROUP_LEVELS[[input$geography]])
    })

    output$title <- renderText({
      ctl <- controls()
      paste0(ctl$indicators, " | ", ctl$respondent, " Survey | ", ctl$year)
    })
    output$subtitle <- renderText({
      how <- if (input$geography == SCHOOLS_LAYER) "Each school's score" else
        paste(controls()$stat, "of school scores in each", geo_label())
      paste0(how, ". Click the map to see that ", geo_label(), "'s trend.")
    })

    output$map <- renderPlotly({
      ctl <- controls()
      plot_map(map_data(), data$geo_keys, input$geography, ctl$indicators,
               ctl$stat, map_source, input$color_mode)
    })
    output$legend <- renderUI(if (input$color_mode == "bands") band_legend())

    output$unmapped <- renderUI({
      um <- unmapped_units(map_data(), data$geo_keys, input$geography)
      if (nrow(um) == 0) return(NULL)
      div(class = "side-note unmapped",
          strong("Not on the map (citywide, no boundary): "),
          paste0(um$name, " ", um$score, " (", um$n_schools, " schools)",
                 collapse = " | "))
    })

    # Clicked area or school; resets when the layer changes.
    selected <- reactiveVal(NULL)
    observeEvent(input$geography, selected(NULL))
    observeEvent(event_data("plotly_click", source = map_source), {
      click <- event_data("plotly_click", source = map_source)
      if (!is.null(click$customdata)) selected(as.character(click$customdata[[1]]))
    })

    selected_label <- reactive({
      req(selected())
      if (input$geography == SCHOOLS_LAYER) {
        names(data$school_list)[data$school_list == selected()]
      } else selected()
    })

    output$trend_title <- renderText({
      if (is.null(selected())) return("Click an area or school on the map to see its trend")
      paste0(selected_label(), " compared with all CPS schools")
    })

    output$trend <- renderPlotly({
      req(selected())
      ctl   <- controls()
      level <- input$geography
      area  <- view_scores(data$school_scores, level, selected(), ctl) |>
        mutate(indicator = selected_label())
      cps   <- view_scores(data$school_scores, "district", NA, ctl) |>
        mutate(indicator = paste("All CPS schools (", ctl$stat, ")", sep = ""))
      plot_trend(bind_rows(area, cps), level, show_values = TRUE)
    })

    output$defs <- renderUI(definitions_ui(data$dict, controls()$indicators))
  })
}


# ---- UI -----------------------------------------------------------------------

build_ui <- function(data) {
  group_tabs <- lapply(names(GROUP_LEVELS), \(lvl)
    tabPanel(GROUP_LEVELS[[lvl]],
             trend_view_ui(lvl, data, selector_label = GROUP_LEVELS[[lvl]])))

  fluidPage(
    theme = bslib::bs_theme(version = 5),
    title = APP_TITLE,
    tags$head(
      tags$link(rel = "stylesheet",
                href = "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap"),
      app_css()
    ),
    title_header(),
    do.call(tabsetPanel, c(
      list(id = "tabs",
           tabPanel("Overview", overview_tab()),
           tabPanel("Map", map_view_ui("map", data)),
           tabPanel("District", trend_view_ui("district", data))),
      group_tabs,
      list(tabPanel("School",
                    trend_view_ui("school", data, aggregate = FALSE,
                                  selector_label = "School",
                                  selector_note = "Type to search by school name.")))
    )),
    div(class = "footer-note",
        HTML("&copy; 2026 Kids First Chicago. Source: UChicago Impact 5Essentials Survey."))
  )
}


# ---- Server -------------------------------------------------------------------

build_server <- function(data) {
  function(input, output, session) {
    map_view_server("map", data)
    trend_view_server("district", data, "district")
    for (lvl in names(GROUP_LEVELS)) {
      local({
        l <- lvl
        trend_view_server(l, data, l, choices = group_choices(data$school_scores, l))
      })
    }
    trend_view_server("school", data, "school", choices = data$school_list)
  }
}


# ---- Main -------------------------------------------------------------------

main <- function() {
  data <- load_all_data()
  shinyApp(build_ui(data), build_server(data))
}

main()
